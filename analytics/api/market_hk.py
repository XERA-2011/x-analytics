from fastapi import APIRouter
from ..modules.market_hk import HKIndices
from analytics.modules.market_hk.fear_greed import HKFearGreed
from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
from ..core.cache import wrap_response

router = APIRouter()

@router.get("/fear-greed")
async def get_hk_fear_greed():
    """获取港股恐慌贪婪指数"""
    result = HKFearGreed.get_data()
    if result.get("status") == "error":
         return wrap_response(status="error", message=result.get("error"))
    return wrap_response(status="ok", data=result)

@router.get("/indices")
async def get_hk_indices():
    """获取港股指数和板块概览"""
    result = HKIndices.get_market_data()
    if result.get("status") == "error":
         return wrap_response(status="error", message=result.get("error"))
    return wrap_response(status="ok", data=result)

@router.get("/signals/overbought-oversold")
async def get_hk_overbought_oversold(period: str = "daily"):
    """获取港股超买超卖信号"""
    result = OverboughtOversoldSignal.get_hk_signal(period=period)
    if result.get("error"):
        return wrap_response(status="error", message=result.get("error"))
    return wrap_response(status="ok", data=result)
