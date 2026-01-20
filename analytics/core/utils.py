"""
工具函数模块
"""

import pytz
from datetime import datetime
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

    config = settings.TRADING_HOURS[market]
    now = get_beijing_time()

    # 检查是否为工作日
    if config.get("weekdays_only", True) and now.weekday() >= 5:  # 周六日
        return False

    current_time = now.time()

    # 处理中国市场 (上午 + 下午两个时段)
    if market == "market_cn":
        morning_start, morning_end = config["morning"]
        afternoon_start, afternoon_end = config["afternoon"]
        return (
            morning_start <= current_time <= morning_end
            or afternoon_start <= current_time <= afternoon_end
        )

    # 处理跨午夜的市场 (如美股)
    elif config.get("cross_midnight", False):
        session_start, session_end = config["session"]
        return current_time >= session_start or current_time <= session_end

    # 处理普通时段
    else:
        session_start, session_end = config["session"]
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


def safe_float(value, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def generate_cache_key(*args) -> str:
    """生成缓存键"""
    key_parts = [settings.CACHE_PREFIX] + [str(arg) for arg in args]
    return ":".join(key_parts)
