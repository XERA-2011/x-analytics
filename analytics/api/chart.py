"""
全球图表中心 API 路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..modules.chart import get_indices_comparison
from ..core.decorators import safe_endpoint

router = APIRouter(tags=["全球图表中心"])


@router.get("/indices-comparison", summary="获取全球主要指数对比数据")
@router.get("/indices/comparison", summary="获取全球主要指数对比数据 (别名)")
@safe_endpoint
def get_global_indices_comparison() -> Dict[str, Any]:
    """
    获取全球主要国家与地区核心指数历史收盘价序列与多周期收益率指标。
    """
    return get_indices_comparison()
