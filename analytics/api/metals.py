#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 有色金属API路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..core.cache import wrap_response
from ..modules.metals import GoldSilverAnalysis, MetalSpotPrice, GoldFearGreedIndex

router = APIRouter(tags=["有色金属"])


@router.get("/fear-greed", summary="获取黄金恐慌贪婪指数")
def get_gold_fear_greed() -> Dict[str, Any]:
    """获取黄金恐慌贪婪指数 (Custom)"""
    try:
        return GoldFearGreedIndex.calculate()
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/silver-fear-greed", summary="获取白银恐慌贪婪指数")
def get_silver_fear_greed() -> Dict[str, Any]:
    """获取白银恐慌贪婪指数 (Custom)"""
    try:
        from ..modules.metals.fear_greed import SilverFearGreedIndex
        return SilverFearGreedIndex.calculate()
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/gold-silver-ratio", summary="获取金银比")
def get_gold_silver_ratio() -> Dict[str, Any]:
    """获取金银比及投资分析"""
    try:
        return GoldSilverAnalysis.get_gold_silver_ratio()
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/spot-prices", summary="获取金属现货价格")
def get_spot_prices() -> Any:
    """获取金属现货价格 (SGE)"""
    try:
        return MetalSpotPrice.get_spot_prices()
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/gold/signals/overbought-oversold", summary="获取黄金超买超卖信号")
def get_gold_obo_signal(period: str = "daily") -> Dict[str, Any]:
    """
    获取黄金超买超卖综合信号
    
    Args:
        period: "daily" (日线) 或 "60min" (60分钟)
    """
    try:
        from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
        return OverboughtOversoldSignal.get_gold_signal(period=period)
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/silver/signals/overbought-oversold", summary="获取白银超买超卖信号")
def get_silver_obo_signal(period: str = "daily") -> Dict[str, Any]:
    """
    获取白银超买超卖综合信号
    
    Args:
        period: "daily" (日线) 或 "60min" (60分钟)
    """
    try:
        from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
        return OverboughtOversoldSignal.get_silver_signal(period=period)
    except Exception as e:
        return wrap_response(status="error", message=str(e))
