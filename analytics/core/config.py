"""
配置管理模块
"""

import os
from datetime import time
from typing import Dict, Tuple, Any


class Settings:
    """应用配置"""

    # Redis 配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_PREFIX = "xanalytics"

    # 交易时间配置 (北京时间)
    TRADING_HOURS: Dict[str, Dict[str, Any]] = {
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
            "market_cn": 1800,  # 30分钟 (原30秒)
            "market_us": 3600,  # 1小时 (原1分钟)
            "metals": 3600,     # 1小时 (原5分钟)
        },
        "non_trading_hours": {
            "market_cn": 7200,  # 2小时
            "market_us": 7200,  # 2小时
            "metals": 7200,     # 2小时
        },
    }

    # 缓存过期时间 (秒) - 统一配置
    CACHE_TTL = {
        # === 高频数据 (改为低频) ===
        "market_overview": 7200,     # 2小时
        "sector_rank": 7200,         # 2小时
        "sector_top": 7200,          # 2小时
        "sector_bottom": 7200,       # 2小时
        "board_cons": 7200,          # 2小时
        "fear_greed": 7200,          # 2小时
        "leaders": 3600,             # 1小时 (原1分钟)
        
        # === 金属市场 (全天) ===
        "metals": 7200,              # 2小时 (原5分钟)
        "gold_silver": 7200,         # 2小时
        
        # === 衍生数据 ===
        "qvix": 3600,                # 1小时
        "dividend": 7200,            # 2小时
        "bonds": 3600,               # 1小时
        "market_heat": 3600,         # 1小时
        "north_funds": 3600,         # 1小时
        
        # === 股票数据 ===
        "stock_spot": 3600,          # 1小时
    }

    # Stale TTL 倍率 (stale_ttl = ttl * ratio)
    STALE_TTL_RATIO = 2

    # API 限流配置
    RATE_LIMIT = {"requests_per_minute": 60, "burst_size": 10}


settings = Settings()

