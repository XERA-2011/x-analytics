#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
x-analytics 核心分析模块 v2.0
重构为三大板块：沪港深市场、美股市场、有色金属
"""

# 核心模块
from .core import cache, scheduler, settings
from .core.cache import cached, warmup_cache

# 业务模块
from .modules.market_cn import (
    CNFearGreedIndex,
    CNMarketLeaders,
    CNMarketHeat,
    CNDividendStrategy,
    CNBonds,
)
from .modules.metals import GoldSilverAnalysis

# 兼容性导入 (保持向后兼容)
try:
    from .sentiment import SentimentAnalysis
    from .market import MarketAnalysis
    from .stock import StockAnalysis
except ImportError:
    # 如果旧模块不存在，创建兼容性类
    class SentimentAnalysis:
        @staticmethod
        def calculate_fear_greed_custom(*args, **kwargs):
            return CNFearGreedIndex.calculate(*args, **kwargs)

    class MarketAnalysis:
        @staticmethod
        def get_market_overview_v2():
            return {"error": "旧版本接口已废弃，请使用新版本API"}

        @staticmethod
        def get_sector_top(*args, **kwargs):
            return CNMarketLeaders.get_sector_leaders()

        @staticmethod
        def get_sector_bottom(*args, **kwargs):
            return CNMarketLeaders.get_sector_leaders()

    class StockAnalysis:
        @staticmethod
        def search(*args, **kwargs):
            return {"error": "股票搜索功能已迁移到新版本API"}


__all__ = [
    # 核心模块
    "cache",
    "scheduler",
    "settings",
    "cached",
    "warmup_cache",
    # 新版本业务模块
    "CNFearGreedIndex",
    "CNMarketLeaders",
    "CNMarketHeat",
    "CNDividendStrategy",
    "CNBonds",
    "GoldSilverAnalysis",
    # 兼容性模块
    "SentimentAnalysis",
    "MarketAnalysis",
    "StockAnalysis",
]
