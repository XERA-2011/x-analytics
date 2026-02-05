"""
配置管理模块
"""

import os
from datetime import time
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量 (优先加载 .env.local, 然后 .env)
# 这样在本地开发时可以自动读取配置，无需在命令行 export
load_dotenv(".env.local")
load_dotenv(".env")


class Settings:
    """应用配置"""
    
    # Base Directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Redis 配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Database 配置
    # 强制要求通过环境变量配置数据库连接 (e.g. postgres://user:pass@host:5432/db)
    if not os.getenv("DATABASE_URL"):
        raise ValueError("Critical: DATABASE_URL environment variable is not set. Please configure a valid database connection.")
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    CACHE_PREFIX = "xanalytics"

    # 交易时间配置 (北京时间)
    TRADING_HOURS: Dict[str, Dict[str, Any]] = {
        "market_cn": {
            "morning": (time(9, 30), time(11, 30)),
            "afternoon": (time(13, 0), time(15, 0)),
            "weekdays_only": True,
        },
        "market_us": {
            # 美国市场交易时间 (北京时间 21:30-04:00)
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
            "market_cn": 86400 * 365,   # A股非交易时间停止更新 (设为一年)
            "market_us": 86400 * 365,   # 美股非交易时间停止更新 (设为一年)
            "metals": 3600,             # 金属仍每小时更新
        },
    }

    # 缓存过期时间 (秒) - 逻辑 TTL
    # 物理 TTL = TTL × STALE_TTL_RATIO，在此期间数据仍可返回
    CACHE_TTL = {
        # === 所有数据统一 2 小时逻辑 TTL ===
        # 物理 TTL = 2h × 4 = 8小时，预热间隔最长1小时，绝对安全
        "market_overview": 7200,     # 2小时
        "market": 7200,              # 2小时
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
        
        # === 宏观数据 ===
        "lpr": 86400,                # 24小时 (每月更新)
        "etf_flow": 7200,            # 2小时
        "calendar": 3600,            # 1小时
        
        # === 基金数据 ===
        "funds": 86400,              # 24小时 (基金净值每日更新)
    }

    # Stale TTL 倍率：物理 TTL = TTL × STALE_TTL_RATIO
    # 设为 24 表示：逻辑过期后，数据仍在 Redis 中保留 23 倍 TTL 时间
    # 例：TTL=2h, 物理TTL=48h, 覆盖整个周末 + 节假日无成功预热场景
    STALE_TTL_RATIO = 24

    # API 限流配置
    RATE_LIMIT = {"requests_per_minute": 60, "burst_size": 10}

    # 恐慌贪婪配置（权重、等级）
    FEAR_GREED_CONFIG: Dict[str, Dict[str, Any]] = {
        "cn": {
            "weights": {
                "price_momentum": 0.20,
                "volatility": 0.15,
                "volume": 0.15,
                "rsi": 0.20,
                "price_position": 0.10,
                "daily_change": 0.20,
            },
            "levels": [
                (80, "极度贪婪", "市场情绪极度乐观，注意风险"),
                (65, "贪婪", "市场情绪偏向乐观，注意风险控制"),
                (55, "轻微贪婪", "市场情绪略显乐观"),
                (45, "中性", "市场情绪相对平衡"),
                (35, "轻微恐慌", "市场情绪略显悲观"),
                (20, "恐慌", "市场情绪偏向悲观"),
                (0, "极度恐慌", "市场情绪极度悲观"),
            ],
        },
        "us": {
            "weights": {
                "vix": 0.30,
                "sp500_momentum": 0.25,
                "daily_change": 0.25,
                "market_breadth": 0.20,
            },
            "levels": [
                (80, "极度贪婪", "市场情绪极度乐观"),
                (65, "贪婪", "市场情绪乐观"),
                (55, "轻微贪婪", "市场情绪略显乐观"),
                (45, "中性", "市场情绪平衡"),
                (35, "轻微恐慌", "市场情绪略显悲观"),
                (20, "恐慌", "市场情绪悲观"),
                (0, "极度恐慌", "市场情绪极度悲观"),
            ],
        },
        "hk": {
            "weights": {
                "rsi": 0.35,
                "bias": 0.35,
                "daily_change": 0.30,
            },
            "levels": [
                (75, "极度贪婪", "市场情绪极度乐观"),
                (55, "贪婪", "市场情绪偏向乐观"),
                (45, "中性", "市场情绪平衡"),
                (25, "恐慌", "市场情绪偏悲观"),
                (0, "极度恐慌", "市场情绪极度悲观"),
            ],
        },
        "metals": {
            "weights": {
                # 技术面因子 (70% 总计)
                "rsi": 0.20,
                "volatility": 0.15,
                "momentum": 0.20,
                "daily_change": 0.15,
                # 基本面因子 (30% 总计)
                "etf_holdings": 0.15,
                "comex_inventory": 0.15,
            },
            "levels": [
                (75, "极度贪婪", "市场情绪极度乐观"),
                (55, "贪婪", "市场情绪偏向乐观"),
                (45, "中性", "多空平衡，方向不明"),
                (25, "恐慌", "市场情绪偏悲观"),
                (0, "极度恐慌", "市场情绪极度悲观"),
            ],
        },
    }

    # 超买超卖信号配置
    OVERBOUGHT_OVERSOLD_CONFIG: Dict[str, Any] = {
        "weights": {
            "rsi": 0.30,
            "macd": 0.25,
            "bollinger": 0.20,
            "kdj": 0.15,
            "volume": 0.10,
        },
        "levels": [
            {"min": 75, "signal": "overbought", "level": "强烈超买", "description": "多项指标共振，市场处于强烈超买状态"},
            {"min": 60, "signal": "overbought", "level": "超买", "description": "技术指标偏向超买"},
            {"min": 40, "signal": "neutral", "level": "中性", "description": "技术指标未出现明显超买超卖信号"},
            {"min": 25, "signal": "oversold", "level": "强烈超卖", "description": "多项指标共振，市场处于强烈超卖状态"},
            {"min": 0, "signal": "oversold", "level": "超卖", "description": "技术指标偏向超卖"},
        ],
    }


settings = Settings()
