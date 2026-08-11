#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 有色金属API路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..core.decorators import safe_endpoint
from ..modules.metals import GoldSilverAnalysis, MetalSpotPrice, GoldFearGreedIndex

router = APIRouter(tags=["有色金属"])


@router.get("/fear-greed", summary="获取黄金技术热度指数")
@safe_endpoint
def get_gold_fear_greed() -> Dict[str, Any]:
    """获取黄金技术热度指数 (Custom)"""
    return GoldFearGreedIndex.calculate()


@router.get("/silver-fear-greed", summary="获取白银技术热度指数")
@safe_endpoint
def get_silver_fear_greed() -> Dict[str, Any]:
    """获取白银技术热度指数 (Custom)"""
    from ..modules.metals.fear_greed import SilverFearGreedIndex
    return SilverFearGreedIndex.calculate()


@router.get("/gold-silver-ratio", summary="获取金银比")
@safe_endpoint
def get_gold_silver_ratio() -> Dict[str, Any]:
    """获取金银比及投资分析"""
    return GoldSilverAnalysis.get_gold_silver_ratio()


@router.get("/spot-prices", summary="获取金属现货价格")
@safe_endpoint
def get_spot_prices() -> Any:
    """获取金属现货价格 (SGE)"""
    return MetalSpotPrice.get_spot_prices()


@router.get("/central-bank-reserves", summary="获取中国央行黄金储备")
@safe_endpoint
def get_china_gold_reserves() -> Dict[str, Any]:
    """获取中国央行黄金和外汇储备月度数据"""
    from ..modules.metals.reserves import GoldFundFlows
    return GoldFundFlows.get_china_gold_reserves()


@router.get("/etf-holdings", summary="获取全球黄金ETF持仓")
@safe_endpoint
def get_spdr_etf_holdings() -> Dict[str, Any]:
    """获取全球最大黄金ETF持仓日度数据"""
    from ..modules.metals.reserves import GoldFundFlows
    return GoldFundFlows.get_spdr_etf_holdings()


@router.get("/gold/signals/overbought-oversold", summary="获取黄金超买超卖信号")
@safe_endpoint
def get_gold_obo_signal(period: str = "daily") -> Dict[str, Any]:
    """
    获取黄金超买超卖综合信号

    Args:
        period: "daily" (日线) 或 "60min" (60分钟)
    """
    from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
    return OverboughtOversoldSignal.get_gold_signal(period=period)


@router.get("/silver/signals/overbought-oversold", summary="获取白银超买超卖信号")
@safe_endpoint
def get_silver_obo_signal(period: str = "daily") -> Dict[str, Any]:
    """
    获取白银超买超卖综合信号

    Args:
        period: "daily" (日线) 或 "60min" (60分钟)
    """
    from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
    return OverboughtOversoldSignal.get_silver_signal(period=period)
