"""
中国市场领涨领跌股票
获取实时涨跌幅排行榜
"""

import logging
import akshare as ak
from typing import Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.data_provider import data_provider

logger = logging.getLogger(__name__)


class CNMarketLeaders:
    """中国市场领涨领跌股票"""

    @staticmethod
    @cached("market_cn:leaders_top", ttl=settings.CACHE_TTL["leaders"], stale_ttl=settings.CACHE_TTL["leaders"] * settings.STALE_TTL_RATIO)
    def get_top_gainers(limit: int = 10) -> Dict[str, Any]:
        """
        获取领涨板块

        Args:
            limit: 返回数量

        Returns:
            领涨板块列表
        """
        try:
            # 使用共享数据提供层获取板块数据
            df = data_provider.get_board_industry_name()

            if df.empty:
                raise ValueError("无法获取行业板块数据")

            # DataFrame schema 校验
            required_columns = {"板块名称", "涨跌幅"}
            missing_columns = required_columns - set(df.columns)
            if missing_columns:
                raise ValueError(f"数据缺少必要列: {missing_columns}")

            # 检查可选字段（警告但不报错）
            optional_columns = {"上涨家数", "下跌家数", "总市值", "领涨股票", "领涨股票-涨跌幅", "换手率"}
            missing_optional = optional_columns - set(df.columns)
            if missing_optional:
                logger.warning(f"板块数据缺少可选列 (AKShare 接口可能已更新): {missing_optional}")

            # 按涨跌幅排序，取前N个
            top_sectors = df.nlargest(limit, "涨跌幅")

            # 格式化数据
            sectors = []
            for _, row in top_sectors.iterrows():
                total_companies = safe_float(row.get("上涨家数", 0)) + safe_float(
                    row.get("下跌家数", 0)
                )
                sector = {
                    "name": str(row["板块名称"]),
                    "change_pct": safe_float(row["涨跌幅"]),
                    "total_market_cap": safe_float(row.get("总市值", 0)),
                    "stock_count": int(total_companies),
                    "leading_stock": str(row.get("领涨股票", "")),
                    "leading_stock_pct": safe_float(row.get("领涨股票-涨跌幅", 0)),
                    "turnover": safe_float(row.get("换手率", 0)),
                    "up_count": int(safe_float(row.get("上涨家数", 0))),
                    "down_count": int(safe_float(row.get("下跌家数", 0))),
                }
                sectors.append(sector)

            return {
                "sectors": sectors,
                "count": len(sectors),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": CNMarketLeaders._get_market_status(),
            }

        except Exception as e:
            logger.error(f"获取领涨板块失败: {e}")
            return {
                "error": str(e),
                "sectors": [],
                "count": 0,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    @cached(
        "market_cn:leaders_bottom", ttl=settings.CACHE_TTL["leaders"], stale_ttl=settings.CACHE_TTL["leaders"] * settings.STALE_TTL_RATIO
    )
    def get_top_losers(limit: int = 10) -> Dict[str, Any]:
        """
        获取领跌板块

        Args:
            limit: 返回数量

        Returns:
            领跌板块列表
        """
        try:
            # 使用共享数据提供层获取板块数据
            df = data_provider.get_board_industry_name()

            if df.empty:
                raise ValueError("无法获取行业板块数据")

            # 按涨跌幅排序，取后N个（最小的）
            bottom_sectors = df.nsmallest(limit, "涨跌幅")

            # 格式化数据
            sectors = []
            for _, row in bottom_sectors.iterrows():
                total_companies = safe_float(row.get("上涨家数", 0)) + safe_float(
                    row.get("下跌家数", 0)
                )
                sector = {
                    "name": str(row["板块名称"]),
                    "change_pct": safe_float(row["涨跌幅"]),
                    "total_market_cap": safe_float(row.get("总市值", 0)),
                    "stock_count": int(total_companies),
                    "leading_stock": str(row.get("领涨股票", "")),
                    "leading_stock_pct": safe_float(row.get("领涨股票-涨跌幅", 0)),
                    "turnover": safe_float(row.get("换手率", 0)),
                    "up_count": int(safe_float(row.get("上涨家数", 0))),
                    "down_count": int(safe_float(row.get("下跌家数", 0))),
                }
                sectors.append(sector)

            return {
                "sectors": sectors,
                "count": len(sectors),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": CNMarketLeaders._get_market_status(),
            }

        except Exception as e:
            logger.error(f"获取领跌板块失败: {e}")
            return {
                "error": str(e),
                "sectors": [],
                "count": 0,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    @cached(
        "market_cn:sector_leaders", ttl=settings.CACHE_TTL["leaders"], stale_ttl=settings.CACHE_TTL["leaders"] * settings.STALE_TTL_RATIO
    )
    def get_sector_leaders() -> Dict[str, Any]:
        """
        获取行业板块涨跌排行

        Returns:
            行业板块排行数据
        """
        try:
            # 使用共享数据提供层获取板块数据
            df = data_provider.get_board_industry_name()

            if df.empty:
                raise ValueError("无法获取行业板块数据")

            # 按涨跌幅排序
            df_sorted = df.sort_values("涨跌幅", ascending=False)

            # 取前10和后10
            top_sectors = df_sorted.head(10)
            bottom_sectors = df_sorted.tail(10)

            # 格式化数据
            def format_sectors(sectors_df):
                sectors = []
                for _, row in sectors_df.iterrows():
                    total_companies = safe_float(row.get("上涨家数", 0)) + safe_float(
                        row.get("下跌家数", 0)
                    )
                    sector = {
                        "name": str(row["板块名称"]),
                        "change_pct": safe_float(row["涨跌幅"]),
                        "total_market_cap": safe_float(row.get("总市值", 0)),
                        "stock_count": int(total_companies),
                        "leading_stock": str(row.get("领涨股票", "")),
                        "leading_stock_pct": safe_float(row.get("领涨股票-涨跌幅", 0)),
                        "up_count": int(safe_float(row.get("上涨家数", 0))),
                        "down_count": int(safe_float(row.get("下跌家数", 0))),
                    }
                    sectors.append(sector)
                return sectors

            return {
                "top_sectors": format_sectors(top_sectors),
                "bottom_sectors": format_sectors(bottom_sectors),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": CNMarketLeaders._get_market_status(),
            }

        except Exception as e:
            logger.error(f"获取行业板块数据失败: {e}")
            return {
                "error": str(e),
                "top_sectors": [],
                "bottom_sectors": [],
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def _get_market_status() -> str:
        """获取市场状态"""
        from ...core.utils import is_trading_hours

        if is_trading_hours("market_cn"):
            return "交易中"
        else:
            return "休市"
