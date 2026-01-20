#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 美股市场 API 路由
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from ..modules.market_us import USFearGreedIndex, USMarketHeat, USTreasury, USMarketLeaders

router = APIRouter(prefix="/market-us", tags=["美股市场"])


@router.get("/fear-greed", summary="获取CNN恐慌贪婪指数")
def get_fear_greed() -> Dict[str, Any]:
    """
    获取美股恐慌贪婪指数 (CNN Fear & Greed Index)
    """
    try:
        # 优先使用实时抓取的 CNN 数据
        data = USFearGreedIndex.get_cnn_fear_greed()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fear-greed/custom", summary="获取自定义美股恐慌贪婪指数")
def get_custom_fear_greed() -> Dict[str, Any]:
    """
    获取自定义美股恐慌贪婪指数 (基于VIX等)
    """
    try:
        return USFearGreedIndex.calculate_custom_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-heat", summary="获取美股板块热度")
def get_market_heat() -> List[Dict[str, Any]]:
    """
    获取美股各板块涨跌幅 (基于 SPDR Sector ETFs)
    """
    try:
        return USMarketHeat.get_sector_performance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bond-yields", summary="获取美债收益率")
def get_bond_yields() -> List[Dict[str, Any]]:
    """
    获取主要期限美债收益率及倒挂情况
    """
    try:
        return USTreasury.get_us_bond_yields()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaders", summary="获取美股领涨板块")
def get_market_leaders() -> Dict[str, Any]:
    """
    获取美股领涨股票 (知名美股)
    """
    try:
        return USMarketLeaders.get_leaders()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
