#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 美国市场 API 路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..core.decorators import safe_endpoint
from ..modules.market_us import USFearGreedIndex, USMarketHeat, USTreasury, USMarketLeaders

router = APIRouter(tags=["美国市场"])


@router.get("/fear-greed", summary="获取美国恐慌贪婪指数(替代CNN)")
@safe_endpoint
def get_fear_greed() -> Dict[str, Any]:
    """
    获取美国市场恐慌贪婪指数 (自定义替代CNN)
    """
    return USFearGreedIndex.get_cnn_fear_greed()


@router.get("/fear-greed/custom", summary="获取自定义美国市场恐慌贪婪指数")
@safe_endpoint
def get_custom_fear_greed() -> Dict[str, Any]:
    """
    获取自定义美国市场恐慌贪婪指数 (基于VIX等)
    """
    return USFearGreedIndex.calculate_custom_index()


@router.get("/market-heat", summary="获取美国市场板块热度")
@safe_endpoint
def get_market_heat() -> Any:
    """
    获取美国市场各板块涨跌幅 (基于 SPDR Sector ETFs)
    """
    return USMarketHeat.get_sector_performance()


@router.get("/bond-yields", summary="获取美债收益率")
@safe_endpoint
def get_bond_yields() -> Any:
    """
    获取主要期限美债收益率及倒挂情况
    """
    return USTreasury.get_us_bond_yields()


@router.get("/leaders", summary="获取美国市场领涨板块")
@safe_endpoint
def get_market_leaders() -> Dict[str, Any]:
    """
    获取美国市场领涨股票 (知名美国市场)
    """
    return USMarketLeaders.get_leaders()


@router.get("/signals/overbought-oversold", summary="获取超买超卖信号")
@safe_endpoint
def get_us_obo_signal(period: str = "daily") -> Dict[str, Any]:
    """
    获取美股超买超卖综合信号 (基于标普500)

    Args:
        period: "daily" (日线)
    """
    from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
    return OverboughtOversoldSignal.get_us_signal(period=period)
