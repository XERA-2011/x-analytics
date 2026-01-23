"""
配置管理模块
"""

import os
from datetime import time
from typing import Dict, Any


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
    # 核心原则：预热间隔 < 物理 TTL，确保缓存永不为空
    REFRESH_INTERVALS = {
        "trading_hours": {
            "market_cn": 1800,   # 30分钟
            "market_us": 1800,   # 30分钟 (改小，确保覆盖)
            "metals": 1800,      # 30分钟 (改小，确保覆盖)
        },
        "non_trading_hours": {
            "market_cn": 3600,   # 1小时 (改小，原2小时)
            "market_us": 3600,   # 1小时 (改小，原2小时)
            "metals": 3600,      # 1小时 (改小，原2小时)
        },
    }

    # 缓存过期时间 (秒) - 逻辑 TTL
    # 物理 TTL = TTL × STALE_TTL_RATIO，在此期间数据仍可返回
    CACHE_TTL = {
        # === 所有数据统一 2 小时逻辑 TTL ===
        # 物理 TTL = 2h × 4 = 8小时，预热间隔最长1小时，绝对安全
        "market_overview": 7200,     # 2小时
        "sector_rank": 7200,         # 2小时
        "sector_top": 7200,          # 2小时
        "sector_bottom": 7200,       # 2小时
        "board_cons": 7200,          # 2小时
        "fear_greed": 7200,          # 2小时
        "leaders": 7200,             # 2小时 (原1小时)
        
        # === 金属市场 ===
        "metals": 7200,              # 2小时
        "gold_silver": 7200,         # 2小时
        
        # === 衍生数据 ===
        "qvix": 7200,                # 2小时 (原1小时)
        "dividend": 7200,            # 2小时
        "bonds": 7200,               # 2小时 (原1小时)
        "market_heat": 7200,         # 2小时 (原1小时)
        "north_funds": 7200,         # 2小时 (原1小时)
        
        # === 股票数据 ===
        "stock_spot": 7200,          # 2小时 (原1小时)
    }

    # Stale TTL 倍率：物理 TTL = TTL × STALE_TTL_RATIO
    # 设为 8 表示：逻辑过期后，数据仍在 Redis 中保留 7 倍 TTL 时间
    # 例：TTL=2h, 物理TTL=16h, 覆盖 12+ 小时无访问场景
    STALE_TTL_RATIO = 8

    # API 限流配置
    RATE_LIMIT = {"requests_per_minute": 60, "burst_size": 10}


settings = Settings()

