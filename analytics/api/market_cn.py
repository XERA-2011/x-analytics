"""
中国市场API路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..core.cache import wrap_response
from ..core.decorators import safe_endpoint, safe_async_endpoint
from ..modules.market_cn import (
    CNFearGreedIndex,
    CNMarketLeaders,

    CNBonds,
    LPRAnalysis,
    CNIndices,
)

router = APIRouter(tags=["中国市场"])


@router.get("/fear-greed", summary="获取恐慌贪婪指数")
@safe_endpoint
def get_fear_greed_index(symbol: str = "sh000001", days: int = 14) -> Dict[str, Any]:
    """获取中国市场恐慌贪婪指数"""
    return CNFearGreedIndex.calculate(symbol=symbol, days=days)


@router.get("/fear-greed/history", summary="获取恐慌贪婪指数历史")
@safe_async_endpoint
async def get_fear_greed_history(days: int = 30) -> Dict[str, Any]:
    """获取恐慌贪婪指数历史趋势 (最近30天)"""
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


@router.get("/sectors/all", summary="获取所有行业板块")
@safe_endpoint
def get_all_sectors() -> Dict[str, Any]:
    """获取所有行业板块数据 (用于热力图)"""
    return CNMarketLeaders.get_all_sectors()


@router.get("/bonds/treasury", summary="获取国债收益率")
@safe_endpoint
def get_treasury_yields() -> Dict[str, Any]:
    """获取国债收益率曲线"""
    return CNBonds.get_bond_market_analysis()


@router.get("/bonds/analysis", summary="获取债券市场分析")
@safe_endpoint
def get_bond_analysis() -> Dict[str, Any]:
    """获取债券市场分析"""
    return CNBonds.get_bond_market_analysis()


@router.get("/lpr", summary="获取 LPR 利率")
@safe_endpoint
def get_lpr_rates() -> Dict[str, Any]:
    """获取贷款市场报价利率 (LPR)"""
    return LPRAnalysis.get_lpr_rates()


@router.get("/indices", summary="获取主要指数")
@safe_endpoint
def get_indices() -> Dict[str, Any]:
    """获取上证、深证、创业板、科创50等指数"""
    return CNIndices.get_indices()


@router.get("/signals/overbought-oversold", summary="获取超买超卖信号")
@safe_endpoint
def get_cn_obo_signal(period: str = "daily") -> Dict[str, Any]:
    """
    获取A股超买超卖综合信号

    Args:
        period: "daily" (日线) 或 "60min" (60分钟)

    Returns:
        综合信号 (overbought/oversold/neutral) 及各指标详情
    """
    from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
    return OverboughtOversoldSignal.get_cn_signal(period=period)
