"""
基金 API 路由
"""

from fastapi import APIRouter
from typing import Dict, Any
from ..modules.funds import FundRanking
from ..core.logger import logger

router = APIRouter(tags=["基金"])


@router.get("/ranking", summary="获取基金涨跌幅排行")
def get_fund_ranking(
    fund_type: str = "全部",
    limit: int = 50
) -> Dict[str, Any]:
    """
    获取基金涨跌幅排行榜

    Args:
        fund_type: 基金类型 (全部/股票型/混合型/债券型/指数型/FOF/QDII)
        limit: 返回数量限制 (最大100)

    Returns:
        基金排行数据，包含代码、名称、净值、涨跌幅等
    """
    # 限制最大返回数量
    limit = min(limit, 100)
    
    try:
        return FundRanking.get_ranking(fund_type=fund_type, limit=limit)
    except Exception as e:
        logger.error(f"❌ 基金 API 请求失败: {e}")
        # 返回错误响应（不会被缓存，因为异常已在模块层抛出）
        return {"status": "error", "message": str(e), "data": []}
