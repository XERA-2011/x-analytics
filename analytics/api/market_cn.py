"""
中国市场API路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..core.cache import wrap_response
from ..modules.market_cn import (
    CNFearGreedIndex,
    CNMarketLeaders,

    CNBonds,
    LPRAnalysis,
    CNIndices,
)

router = APIRouter(tags=["中国市场"])


@router.get("/fear-greed", summary="获取恐慌贪婪指数")
def get_fear_greed_index(symbol: str = "sh000001", days: int = 14) -> Dict[str, Any]:
    """获取中国市场恐慌贪婪指数"""
    try:
        result = CNFearGreedIndex.calculate(symbol=symbol, days=days)
        # @cached 装饰器已返回 wrap_response 格式，直接透传
        return result
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/fear-greed/history", summary="获取恐慌贪婪指数历史")
async def get_fear_greed_history(days: int = 30) -> Dict[str, Any]:
    """获取恐慌贪婪指数历史趋势 (最近30天)"""
    try:
        from analytics.core.db import DB_AVAILABLE
        if not DB_AVAILABLE:
            return wrap_response(status="ok", data=[], message="Database not configured")

        from analytics.models.sentiment import SentimentHistory
        from datetime import date, timedelta
        
        start_date = date.today() - timedelta(days=days)
        history = await SentimentHistory.filter(
            market="CN", 
            date__gte=start_date
        ).order_by("date").all()
        
        return wrap_response(
            status="ok",
            data=[
                {
                    "date": h.date.isoformat(),
                    "score": h.score,
                    "level": h.level
                }
                for h in history
            ]
        )
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/sectors/all", summary="获取所有行业板块")
def get_all_sectors() -> Dict[str, Any]:
    """获取所有行业板块数据 (用于热力图)"""
    try:
        result = CNMarketLeaders.get_all_sectors()
        return result
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/bonds/treasury", summary="获取国债收益率")
def get_treasury_yields() -> Dict[str, Any]:
    """获取国债收益率曲线"""
    try:
        result = CNBonds.get_bond_market_analysis()
        return result
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/bonds/analysis", summary="获取债券市场分析")
def get_bond_analysis() -> Dict[str, Any]:
    """获取债券市场分析"""
    try:
        result = CNBonds.get_bond_market_analysis()
        return result
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/lpr", summary="获取 LPR 利率")
def get_lpr_rates() -> Dict[str, Any]:
    """获取贷款市场报价利率 (LPR)"""
    try:
        return LPRAnalysis.get_lpr_rates()
    except Exception as e:
        return wrap_response(status="error", message=str(e))

@router.get("/indices", summary="获取主要指数")
def get_indices() -> Dict[str, Any]:
    """获取上证、深证、创业板、科创50等指数"""
    try:
        result = CNIndices.get_indices()
        return result
    except Exception as e:
        return wrap_response(status="error", message=str(e))


@router.get("/signals/overbought-oversold", summary="获取超买超卖信号")
def get_cn_obo_signal(period: str = "daily") -> Dict[str, Any]:
    """
    获取A股超买超卖综合信号
    
    Args:
        period: "daily" (日线) 或 "60min" (60分钟)
    
    Returns:
        综合信号 (overbought/oversold/neutral) 及各指标详情
    """
    try:
        from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
        return OverboughtOversoldSignal.get_cn_signal(period=period)
    except Exception as e:
        return wrap_response(status="error", message=str(e))
