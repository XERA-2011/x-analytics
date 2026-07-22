"""
AI 产业链 API 路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..modules.ai import AIOverview

router = APIRouter(tags=["AI 产业链"])

@router.get("/overview", summary="获取 AI 产业链火热度、周期评估与 6 层明细")
async def get_ai_overview() -> Dict[str, Any]:
    """
    获取 AI 产业链 6 层明细、综合火热度得分及周期阶段判断
    """
    return AIOverview.get_overview()
