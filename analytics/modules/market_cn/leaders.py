"""
中国市场领涨领跌股票
获取实时涨跌幅排行榜
"""

from typing import Dict, Any
import time
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.data_provider import data_provider
from ...core.logger import logger


class CNMarketLeaders:
    """中国市场领涨领跌股票"""







    @staticmethod
    @cached(
        "market_cn:sectors:all", ttl=settings.CACHE_TTL["leaders"], stale_ttl=settings.CACHE_TTL["leaders"] * settings.STALE_TTL_RATIO
    )
    def get_all_sectors() -> Dict[str, Any]:
        """
        获取所有行业板块数据 (用于热力图)
        """
        try:
            df = data_provider.get_board_industry_name()
            if df.empty:
                raise ValueError("无法获取行业板块数据")

            # 格式化所有数据
            sectors = []
            for _, row in df.iterrows():
                total_companies = safe_float(row.get("上涨家数", 0)) + safe_float(
                    row.get("下跌家数", 0)
                )
                sectors.append({
                    "name": str(row["板块名称"]),
                    "value": safe_float(row.get("总市值", 0)), # 用于 Treemap 面积
                    "change_pct": safe_float(row["涨跌幅"]),   # 用于颜色
                    "stock_count": int(total_companies),
                    "turnover": safe_float(row.get("换手率", 0)),
                    "leading_stock": str(row.get("领涨股票", "")),
                })

            return {
                "sectors": sectors,
                "count": len(sectors),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": CNMarketLeaders._get_market_status(),
            }

        except Exception as e:
            logger.error(f"获取所有板块数据失败: {e}")
            return {"error": str(e), "sectors": []}

    @staticmethod
    def _get_market_status() -> str:
        """获取市场状态"""
        from ...core.utils import is_trading_hours

        if is_trading_hours("market_cn"):
            return "交易中"
        else:
            return "休市"


