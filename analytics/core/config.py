"""
配置管理模块
"""

import os
from datetime import time


class Settings:
    """应用配置"""

    # Redis 配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_PREFIX = "xanalytics"

    # 交易时间配置 (北京时间)
    # 交易时间配置 (北京时间)
    TRADING_HOURS = {
        "market_cn": {
            "morning": (time(9, 30), time(11, 30)),
            "afternoon": (time(13, 0), time(15, 0)),
            "weekdays_only": True,
        },
        "market_us": {
            # 美股交易时间 (北京时间 21:30-04:00)
            "session": (time(21, 30), time(4, 0)),
            "weekdays_only": True,
            "cross_midnight": True,
        },
        "metals": {
            # 金属市场 24小时交易
            "session": (time(0, 0), time(23, 59)),
            "weekdays_only": False,
        },
    }

    # 刷新间隔配置 (秒)
    REFRESH_INTERVALS = {
        "trading_hours": {
            "market_cn": 30,  # 30秒
            "market_us": 60,  # 1分钟
            "metals": 300,  # 5分钟
        },
        "non_trading_hours": {
            "market_cn": 1800,  # 30分钟
            "market_us": 3600,  # 1小时
            "metals": 1800,  # 30分钟
        },
    }

    # 缓存过期时间 (秒)
    CACHE_TTL = {
        "fear_greed": 300,  # 5分钟
        "leaders": 60,  # 1分钟
        "market_heat": 180,  # 3分钟
        "dividend": 3600,  # 1小时
        "bonds": 600,  # 10分钟
        "metals": 300,  # 5分钟
    }

    # API 限流配置
    RATE_LIMIT = {"requests_per_minute": 60, "burst_size": 10}


settings = Settings()
