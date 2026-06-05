"""
ETF 市场 API 路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..core.decorators import safe_endpoint
from ..modules.etf import ETFHeatmap

router = APIRouter(tags=["ETF市场"])


@router.get("/heatmap", summary="获取 ETF 热力图数据")
@safe_endpoint
def get_etf_heatmap() -> Dict[str, Any]:
    """获取精选 ETF 热力图数据（按宽基/行业/跨境/商品债券分类）"""
    return ETFHeatmap.get_heatmap_data()
