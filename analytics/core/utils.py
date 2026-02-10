"""
工具函数模块
"""

import pytz  # type: ignore[import-untyped]
from datetime import datetime, time as dt_time
from typing import Any, Dict, Tuple, cast, overload, Optional
from .config import settings


def get_beijing_time() -> datetime:
    """获取北京时间"""
    beijing_tz = pytz.timezone("Asia/Shanghai")
    return datetime.now(beijing_tz)


def is_trading_hours(market: str) -> bool:
    """
    判断指定市场是否在交易时间内

    Args:
        market: 市场类型 ('market_cn', 'market_us', 'metals')

    Returns:
        bool: 是否在交易时间内
    """
    if market not in settings.TRADING_HOURS:
        return False

    config: Dict[str, Any] = settings.TRADING_HOURS[market]
    now = get_beijing_time()

    # 检查是否为工作日
    if config.get("weekdays_only", True) and now.weekday() >= 5:  # 周六日
        return False

    current_time = now.time()

    # 处理中国市场 (上午 + 下午两个时段)
    if market == "market_cn":
        morning_start, morning_end = cast(Tuple[dt_time, dt_time], config["morning"])
        afternoon_start, afternoon_end = cast(Tuple[dt_time, dt_time], config["afternoon"])
        return (
            morning_start <= current_time <= morning_end
            or afternoon_start <= current_time <= afternoon_end
        )

    # 处理跨午夜的市场 (如美国市场)
    elif config.get("cross_midnight", False):
        session_start, session_end = cast(Tuple[dt_time, dt_time], config["session"])
        return current_time >= session_start or current_time <= session_end

    # 处理普通时段
    else:
        session_start, session_end = cast(Tuple[dt_time, dt_time], config["session"])
        return session_start <= current_time <= session_end


def get_refresh_interval(market: str) -> int:
    """
    获取指定市场的刷新间隔

    Args:
        market: 市场类型

    Returns:
        int: 刷新间隔(秒)
    """
    if is_trading_hours(market):
        return settings.REFRESH_INTERVALS["trading_hours"].get(market, 300)
    else:
        return settings.REFRESH_INTERVALS["non_trading_hours"].get(market, 1800)


TOLERANCE_MINUTES = 15  # Buffer window around trading hours


def is_trading_time(market: str, tolerance_minutes: int = TOLERANCE_MINUTES) -> bool:
    """Check if a market is within its trading time window (with tolerance).
    
    Extends the trading window by ±tolerance_minutes to avoid edge-case misses
    where a warmup task fires slightly before open or after close.

    Args:
        market: Market type ('market_cn', 'market_us', 'metals').
        tolerance_minutes: Minutes to extend each end of the window.

    Returns:
        True if the current time falls within the expanded trading window.
    """
    if market not in settings.TRADING_HOURS:
        return False

    # Metals trade 24h — always return True
    config: Dict[str, Any] = settings.TRADING_HOURS[market]
    if not config.get("weekdays_only", True):
        return True

    from .scheduler import is_trading_day
    now = get_beijing_time()

    # Weekend / holiday check (no tolerance can save a non-trading day)
    if config.get("weekdays_only", True):
        if now.weekday() >= 5:
            return False
        if not is_trading_day(now.date()):
            return False

    from datetime import timedelta

    current_dt = now
    tolerance = timedelta(minutes=tolerance_minutes)

    if market == "market_cn":
        morning_start, morning_end = config["morning"]
        afternoon_start, afternoon_end = config["afternoon"]
        # Build datetime versions for tolerance math
        day = now.date()
        m_start = datetime.combine(day, morning_start) - tolerance
        a_end = datetime.combine(day, afternoon_end) + tolerance
        # Simplified: if within expanded morning-open to afternoon-close, allow
        return m_start <= current_dt.replace(tzinfo=None) <= a_end

    elif config.get("cross_midnight", False):
        # US market: 21:30 - 04:00 Beijing time
        session_start, session_end = config["session"]
        day = now.date()
        start_dt = datetime.combine(day, session_start) - tolerance
        # End is next day
        end_dt = datetime.combine(day + timedelta(days=1), session_end) + tolerance
        current_naive = current_dt.replace(tzinfo=None)
        return current_naive >= start_dt or current_naive <= (datetime.combine(day, session_end) + tolerance)

    else:
        session_start, session_end = config["session"]
        day = now.date()
        start_dt = datetime.combine(day, session_start) - tolerance
        end_dt = datetime.combine(day, session_end) + tolerance
        return start_dt <= current_dt.replace(tzinfo=None) <= end_dt


def format_number(value: float, precision: int = 2) -> str:
    """格式化数字显示"""
    if abs(value) >= 1e8:
        return f"{value / 1e8:.{precision}f}亿"
    elif abs(value) >= 1e4:
        return f"{value / 1e4:.{precision}f}万"
    else:
        return f"{value:.{precision}f}"


def format_percentage(value: float, precision: int = 2) -> str:
    """格式化百分比显示"""
    return f"{value:.{precision}f}%"


@overload
def safe_float(value: Any, default: float = 0.0) -> float: ...

@overload
def safe_float(value: Any, default: None) -> Optional[float]: ...

def safe_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    """安全转换为浮点数，支持 None 默认值"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def generate_cache_key(*args) -> str:
    """生成缓存键"""
    key_parts = [settings.CACHE_PREFIX] + [str(arg) for arg in args]
    return ":".join(key_parts)


def akshare_call_with_retry(
    func,
    *args,
    max_retries: int = 5,
    base_delay: float = 2.0,
    use_throttle: bool = True,
    **kwargs
):
    """
    带重试机制的 AkShare API 调用

    Args:
        func: AkShare 函数
        *args: 函数参数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间(秒)
        use_throttle: 是否使用全局节流器
        **kwargs: 函数关键字参数

    Returns:
        API 调用结果

    Raises:
        Exception: 所有重试失败后抛出最后一个异常
    """
    import time
    import random
    from .throttler import throttler

    last_exception = None

    for attempt in range(max_retries):
        try:
            # 使用节流器控制请求频率
            if use_throttle:
                throttler.wait_if_needed()

            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()

            # 检查是否是可重试的错误（网络问题或 JSON 解析失败）
            retryable_error_keywords = [
                # 网络/连接相关
                "connection",
                "timeout",
                "disconnected",
                "reset",
                "refused",
                "aborted",
                "remotedisconnected",
                "closed",
                "eof",
                "broken pipe",
                "network",
                "temporary failure",
                # JSON 解析错误（响应被截断）
                "object literal",      # 东财 API 返回不完整 JSON
                "not terminated",      # JSON 字符串未正常结束
                "json",                # 通用 JSON 错误
                "decode",              # JSON decode 失败
                "expecting",           # JSON 格式期望错误
                "unterminated",        # 未结束的字符串
            ]
            
            is_retryable_error = any(
                keyword in error_msg
                for keyword in retryable_error_keywords
            )

            if not is_retryable_error:
                # 非可重试错误，直接抛出
                raise

            if attempt < max_retries - 1:
                # 指数退避 + 随机抖动，避免同时重试造成更大压力
                jitter = random.uniform(0.5, 1.5)
                delay = base_delay * (2 ** attempt) * jitter
                func_name = getattr(func, '__name__', str(func))
                print(
                    f"⚠️ API调用失败 [{func_name}] (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}"
                )
                print(f"   {delay:.1f}秒后重试...")
                time.sleep(delay)
            else:
                func_name = getattr(func, '__name__', str(func))
                print(f"❌ API调用失败 [{func_name}] (已重试{max_retries}次): {str(e)[:150]}")

    raise last_exception  # type: ignore

