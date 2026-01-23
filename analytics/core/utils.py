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

            # 检查是否是连接类错误（需要重试）
            connection_error_keywords = [
                "connection",
                "timeout",
                "disconnected",
                "reset",
                "refused",
                "aborted",
                "remotedisconnected",  # 新增：针对您遇到的错误
                "closed",              # 新增：连接关闭
                "eof",                 # 新增：意外结束
                "broken pipe",         # 新增：管道断开
                "network",             # 新增：网络相关
                "temporary failure",   # 新增：临时故障
            ]
            
            is_connection_error = any(
                keyword in error_msg
                for keyword in connection_error_keywords
            )

            if not is_connection_error:
                # 非连接错误，直接抛出
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

