"""
中国市场领涨领跌股票
获取实时涨跌幅排行榜
"""

from typing import Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.data_provider import data_provider
from ...core.logger import logger


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
                # 添加分析标签
                sector["analysis"] = CNMarketLeaders._analyze_sector(sector, is_gainer=True)
                sectors.append(sector)

            return {
                "sectors": sectors,
                "count": len(sectors),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": CNMarketLeaders._get_market_status(),
                "explanation": CNMarketLeaders._get_sector_explanation(is_gainer=True),
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
                # 添加分析标签 (领跌板块)
                sector["analysis"] = CNMarketLeaders._analyze_sector(sector, is_gainer=False)
                sectors.append(sector)

            return {
                "sectors": sectors,
                "count": len(sectors),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": CNMarketLeaders._get_market_status(),
                "explanation": CNMarketLeaders._get_sector_explanation(is_gainer=False),
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

    @staticmethod
    def _get_heat_label(turnover: float, is_gainer: bool = True) -> Dict[str, str]:
        """根据换手率获取热度标签，领涨和领跌使用不同用词"""
        if is_gainer:
            # 领涨板块用词
            if turnover >= 5:
                return {"level": "极热", "color": "red"}
            elif turnover >= 3:
                return {"level": "较热", "color": "orange"}
            elif turnover >= 1:
                return {"level": "适中", "color": "gray"}
            else:
                return {"level": "冷门", "color": "blue"}
        else:
            # 领跌板块用词
            if turnover >= 5:
                return {"level": "恐慌", "color": "red"}
            elif turnover >= 3:
                return {"level": "剧烈", "color": "orange"}
            elif turnover >= 1:
                return {"level": "温和", "color": "gray"}
            else:
                return {"level": "低迷", "color": "blue"}

    @staticmethod
    def _generate_tip(is_gainer: bool, heat_level: str, strength_ratio: float, change_pct: float) -> str:
        """
        生成综合分析提示
        
        Args:
            is_gainer: 是否为领涨板块
            heat_level: 热度等级
            strength_ratio: 上涨家数占比 (0-1)
            change_pct: 涨跌幅
        """
        if is_gainer:
            # 领涨板块提示
            if heat_level == "极热":
                if strength_ratio >= 0.8:
                    return "走势强劲，注意追高风险"
                else:
                    return "热度极高，内部分化明显"
            elif heat_level == "较热":
                if strength_ratio >= 0.6:
                    return "资金关注，可跟踪龙头"
                else:
                    return "热度较高，部分个股滞涨"
            elif heat_level == "适中":
                if change_pct >= 3:
                    return "启动迹象，关注持续性"
                else:
                    return "温和上涨，走势健康"
            else:
                return "关注度低，启动初期"
        else:
            # 领跌板块提示
            if heat_level == "恐慌":
                return "恐慌抛售，观望为宜"
            elif heat_level == "剧烈":
                if strength_ratio <= 0.2:
                    return "全面下跌，避开为主"
                else:
                    return "跌幅较大，等待企稳"
            elif heat_level == "温和":
                if abs(change_pct) <= 1.5:
                    return "跌势趋缓，关注止跌信号"
                else:
                    return "正常调整，观察支撑"
            else:
                return "无量下跌，关注度低"

    @staticmethod
    def _analyze_sector(sector: Dict[str, Any], is_gainer: bool = True) -> Dict[str, Any]:
        """
        为单个板块生成分析数据
        
        Args:
            sector: 板块数据字典
            is_gainer: 是否为领涨板块
            
        Returns:
            包含 heat, strength_ratio, tip 的分析字典
        """
        turnover = sector.get("turnover", 0)
        up_count = sector.get("up_count", 0)
        down_count = sector.get("down_count", 0)
        change_pct = sector.get("change_pct", 0)
        
        # 热度标签 (根据领涨/领跌使用不同用词)
        heat = CNMarketLeaders._get_heat_label(turnover, is_gainer)
        
        # 强弱比 (上涨家数占比)
        total = up_count + down_count
        strength_ratio = up_count / total if total > 0 else 0.5
        
        # 综合提示
        tip = CNMarketLeaders._generate_tip(is_gainer, heat["level"], strength_ratio, change_pct)
        
        return {
            "heat": heat,
            "turnover": round(turnover, 2),  # 换手率数值
            "strength_ratio": round(strength_ratio * 100),
            "tip": tip,
        }

    @staticmethod
    def _get_sector_explanation(is_gainer: bool = True) -> str:
        """获取板块分析说明"""
        if is_gainer:
            return """
板块分析标签说明（领涨）：

🔥 热度标签（基于换手率）：
• 极热 (≥5%): 交易拥挤，短期可能回调
• 较热 (3-5%): 资金关注度高
• 适中 (1-3%): 正常交易状态
• 冷门 (<1%): 关注度低

📊 强弱比（涨家数占比）：
• ≥80%: 全面上涨，趋势强劲
• 60-80%: 多数上涨，结构良好
• <60%: 内部分化，需精选个股

💡 综合提示：
• 高热度 + 高强弱比 = 注意追高风险
• 适中热度 + 高强弱比 = 走势健康
• 低热度 + 启动迹象 = 可关注
            """.strip()
        else:
            return """
板块分析标签说明（领跌）：

🔥 恐慌标签（基于换手率）：
• 恐慌 (≥5%): 抛压极大，非理性杀跌
• 剧烈 (3-5%): 资金大幅流出
• 温和 (1-3%): 正常调整
• 低迷 (<1%): 无量阴跌

📊 弱势比（跌家数占比）：
• ≥80%: 泥沙俱下，全面杀跌
• 60-80%: 多数下跌，空头占优
• <60%: 抵抗式下跌，部分抗跌

💡 综合提示：
• 高换手 + 全面杀跌 = 恐慌抛售，观望
• 无量 + 全面下跌 = 阴跌不止，慎抄底
• 缩量 + 抵抗下跌 = 关注止跌信号
            """.strip()
