#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
x-analytics 核心分析模块
重构为三大板块：中国市场、美国市场、有色金属
"""

# 核心模块
from .core import cache, scheduler, settings
from .core.cache import cached, warmup_cache

# 业务模块
from .modules.market_cn import (
    CNFearGreedIndex,
    CNMarketLeaders,
    CNBonds,
)
from .modules.metals import GoldSilverAnalysis

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
    "CNBonds",
    "GoldSilverAnalysis",
]
