"""
黄金市场模块
包含：金银比、各类金属现货价格、黄金/白银技术热度、央行储备及ETF持仓
"""

from .gold_silver import GoldSilverAnalysis
from .spot_price import MetalSpotPrice
from .fear_greed import GoldFearGreedIndex, SilverFearGreedIndex

__all__ = [
    "GoldSilverAnalysis",
    "MetalSpotPrice",
    "GoldFearGreedIndex",
    "SilverFearGreedIndex",
]
