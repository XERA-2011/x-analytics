"""
指数估值 API 路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..modules.index_valuation import get_index_valuation
from ..core.decorators import safe_endpoint

router = APIRouter(tags=["指数估值"])


@router.get("/valuation/{index_code}", summary="获取指数估值详情")
@safe_endpoint
def get_valuation(index_code: str) -> Dict[str, Any]:
    """
    获取指定指数的估值及价格历史数据。
    
    支持的指数代码包括：
    - **SH000300**: 沪深300
    - **HSI**: 恒生指数
    - **NDX**: 纳斯达克100
    - **SP500**: 标普500
    """
    return get_index_valuation(index_code)
