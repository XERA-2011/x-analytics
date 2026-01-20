"""
沪港深市场API路由
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..modules.market_cn import (
    CNFearGreedIndex,
    CNMarketLeaders,
    CNMarketHeat,
    CNDividendStrategy,
    CNBonds,
)

router = APIRouter(prefix="/market-cn", tags=["沪港深市场"])


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


@router.get("/heat", summary="获取市场热度")
def get_market_heat() -> Dict[str, Any]:
    """获取市场热度指标"""
    try:
        return CNMarketHeat.get_market_heat()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dividend/stocks", summary="获取红利低波股票")
def get_dividend_stocks(limit: int = 20) -> Dict[str, Any]:
    """获取红利低波策略股票池"""
    try:
        return CNDividendStrategy.get_dividend_stocks(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dividend/etfs", summary="获取红利ETF")
def get_dividend_etfs() -> Dict[str, Any]:
    """获取红利相关ETF"""
    try:
        return CNDividendStrategy.get_dividend_etfs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bonds/treasury", summary="获取国债收益率")
def get_treasury_yields() -> Dict[str, Any]:
    """获取国债收益率曲线"""
    try:
        return CNBonds.get_treasury_yields()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bonds/analysis", summary="获取债券市场分析")
def get_bond_analysis() -> Dict[str, Any]:
    """获取债券市场分析"""
    try:
        return CNBonds.get_bond_market_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
