"""
有色金属模块
包含：金银比、各类金属现货价格、恐慌贪婪指数、基本面数据
"""

from .gold_silver import GoldSilverAnalysis
from .spot_price import MetalSpotPrice
from .fear_greed import GoldFearGreedIndex, SilverFearGreedIndex
from .fundamentals import MetalFundamentals

__all__ = [
    "GoldSilverAnalysis",
    "MetalSpotPrice",
    "GoldFearGreedIndex",
    "SilverFearGreedIndex",
    "MetalFundamentals",
]
