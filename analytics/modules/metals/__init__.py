"""
有色金属模块
包含：金银比、各类金属现货价格
"""

from .gold_silver import GoldSilverAnalysis
from .spot_price import MetalSpotPrice

__all__ = ["GoldSilverAnalysis", "MetalSpotPrice"]
