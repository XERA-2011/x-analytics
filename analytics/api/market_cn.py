"""
中国市场API路由
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
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
        return CNFearGreedIndex.calculate(symbol=symbol, days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaders/gainers", summary="获取领涨板块")
def get_top_gainers(limit: int = 10) -> Dict[str, Any]:
    """获取领涨板块排行"""
    try:
        return CNMarketLeaders.get_top_gainers(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaders/losers", summary="获取领跌板块")
def get_top_losers(limit: int = 10) -> Dict[str, Any]:
    """获取领跌板块排行"""
    try:
        return CNMarketLeaders.get_top_losers(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaders/sectors", summary="获取行业板块排行")
def get_sector_leaders() -> Dict[str, Any]:
    """获取行业板块涨跌排行"""
    try:
        return CNMarketLeaders.get_sector_leaders()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))








@router.get("/bonds/treasury", summary="获取国债收益率")
def get_treasury_yields() -> Dict[str, Any]:
    """获取国债收益率曲线"""
    try:
        return CNBonds.get_bond_market_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bonds/analysis", summary="获取债券市场分析")
def get_bond_analysis() -> Dict[str, Any]:
    """获取债券市场分析"""
    try:
        return CNBonds.get_bond_market_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lpr", summary="获取 LPR 利率")
def get_lpr_rates() -> Dict[str, Any]:
    """获取贷款市场报价利率 (LPR)"""
    return LPRAnalysis.get_lpr_rates()

@router.get("/indices", summary="获取主要指数")
def get_indices() -> Dict[str, Any]:
    """获取上证、深证、创业板、科创50等指数"""
    try:
        return CNIndices.get_indices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

