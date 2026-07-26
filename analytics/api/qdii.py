"""
QDII 基金 API 路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..core.decorators import safe_endpoint
from ..modules.qdii import get_qdii_passive_funds

router = APIRouter(tags=["QDII基金"])


@router.get("/funds", summary="获取纳斯达克100 & 标普500 场外 QDII A类基金列表")
@safe_endpoint
def get_qdii_funds() -> Dict[str, Any]:
    """获取场外被动 QDII A类基金数据列表（支持排名、费率、近一年收益、跟踪偏离度等）"""
    return get_qdii_passive_funds()
