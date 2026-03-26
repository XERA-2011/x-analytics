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

    # 申万一级行业白名单。
    # 东方财富行业接口会混入一级/二级/三级行业，热力图只保留一级行业。
    PRIMARY_SECTOR_NAMES = {
        "农林牧渔",
        "基础化工",
        "钢铁",
        "有色金属",
        "电子",
        "家用电器",
        "食品饮料",
        "纺织服饰",
        "轻工制造",
        "医药生物",
        "公用事业",
        "交通运输",
        "房地产",
        "商贸零售",
        "社会服务",
        "综合",
        "建筑材料",
        "建筑装饰",
        "电力设备",
        "国防军工",
        "计算机",
        "通信",
        "银行",
        "非银金融",
        "传媒",
        "机械设备",
        "汽车",
        "美容护理",
        "环保",
        "石油石化",
        "煤炭",
    }

    @staticmethod
    def _filter_primary_sectors(df):
        """仅保留一级行业。"""
        if "板块名称" not in df.columns:
            return df

        filtered_df = df[df["板块名称"].astype(str).isin(CNMarketLeaders.PRIMARY_SECTOR_NAMES)]

        # 上游名称口径变化时，退回原始数据，避免页面整体空白。
        return filtered_df if not filtered_df.empty else df







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
            df = CNMarketLeaders._filter_primary_sectors(df)

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

