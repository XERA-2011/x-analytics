"""
港股市场 API 路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..modules.market_hk import HKIndices
from ..modules.market_hk.fear_greed import HKFearGreed
from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
from ..core.decorators import safe_endpoint

router = APIRouter(tags=["港股市场"])


@router.get("/fear-greed", summary="获取港股恐慌贪婪指数")
@safe_endpoint
def get_hk_fear_greed() -> Dict[str, Any]:
    """获取港股恐慌贪婪指数"""
    return HKFearGreed.get_data()


@router.get("/indices", summary="获取港股指数")
@safe_endpoint
def get_hk_indices() -> Dict[str, Any]:
    """获取港股指数和板块概览"""
    return HKIndices.get_market_data()


@router.get("/signals/overbought-oversold", summary="获取港股超买超卖信号")
@safe_endpoint
def get_hk_overbought_oversold(period: str = "daily") -> Dict[str, Any]:
    """获取港股超买超卖信号"""
    return OverboughtOversoldSignal.get_hk_signal(period=period)
