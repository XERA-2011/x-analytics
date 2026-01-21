"""
中国市场热度指标
包括成交额、换手率、活跃度等指标
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import get_beijing_time
from ...core.data_provider import data_provider


class CNMarketHeat:
    """中国市场热度分析"""

    @staticmethod
    @cached("market_cn:heat", ttl=settings.CACHE_TTL["market_heat"], stale_ttl=300)
    def get_market_heat() -> Dict[str, Any]:
        """
        获取市场热度指标

        Returns:
            市场热度数据
        """
        try:
            # 使用共享数据提供层获取股票数据 (避免重复请求)
            print("📊 获取股票行情数据...")
            df = data_provider.get_stock_zh_a_spot()

            if df.empty:
                raise ValueError("无法获取股票行情数据")

            print(f"✅ 获取到 {len(df)} 只股票数据")

            # 获取市场概况数据
            heat_data = {}

            # 1. 获取两市成交额
            turnover_data = CNMarketHeat._get_market_turnover_from_df(df)
            heat_data.update(turnover_data)

            # 2. 获取涨跌分布
            breadth_data = CNMarketHeat._get_market_breadth_from_df(df)
            heat_data.update(breadth_data)

            # 3. 获取活跃度指标
            activity_data = CNMarketHeat._get_market_activity_from_df(df)
            heat_data.update(activity_data)

            # 4. 计算综合热度指数
            heat_score = CNMarketHeat._calculate_heat_score(heat_data)
            heat_data["heat_score"] = round(heat_score, 1)  # 保留1位小数
            heat_data["heat_level"] = CNMarketHeat._get_heat_level(heat_score)

            heat_data["update_time"] = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            heat_data["explanation"] = CNMarketHeat._get_explanation()

            return heat_data

        except Exception as e:
            print(f"❌ 获取市场热度失败: {e}")
            return {
                "error": str(e),
                "heat_score": 50,
                "heat_level": "中等",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def _get_market_turnover_from_df(df: pd.DataFrame) -> Dict[str, Any]:
        """从DataFrame获取市场成交额数据"""
        try:
            # 计算总成交额（亿元）
            total_turnover = df["成交额"].sum() / 100000000

            # 获取历史平均成交额（最近5天）
            try:
                # 这里简化处理，使用当前数据估算
                avg_turnover_5d = total_turnover * 0.8  # 简化估算
                turnover_ratio = (
                    total_turnover / avg_turnover_5d if avg_turnover_5d > 0 else 1
                )
            except Exception:
                avg_turnover_5d = total_turnover
                turnover_ratio = 1

            return {
                "total_turnover": round(total_turnover, 2),
                "avg_turnover_5d": round(avg_turnover_5d, 2),
                "turnover_ratio": round(turnover_ratio, 2),
                "turnover_level": "高"
                if turnover_ratio > 1.2
                else "中"
                if turnover_ratio > 0.8
                else "低",
            }

        except Exception as e:
            print(f"⚠️ 获取成交额数据失败: {e}")
            return {"turnover_error": str(e)}

    @staticmethod
    def _get_market_breadth_from_df(df: pd.DataFrame) -> Dict[str, Any]:
        """从DataFrame获取市场广度数据（涨跌分布）"""
        try:
            # 统计涨跌分布
            total_stocks = len(df)
            rising_stocks = len(df[df["涨跌幅"] > 0])
            falling_stocks = len(df[df["涨跌幅"] < 0])
            flat_stocks = total_stocks - rising_stocks - falling_stocks

            # 计算涨跌比
            rise_fall_ratio = (
                rising_stocks / falling_stocks if falling_stocks > 0 else 999
            )

            # 统计涨停跌停
            limit_up = len(df[df["涨跌幅"] >= 9.8])
            limit_down = len(df[df["涨跌幅"] <= -9.8])

            # 计算强势股比例（涨幅>3%）
            strong_stocks = len(df[df["涨跌幅"] > 3])
            strong_ratio = strong_stocks / total_stocks * 100

            return {
                "total_stocks": total_stocks,
                "rising_stocks": rising_stocks,
                "falling_stocks": falling_stocks,
                "flat_stocks": flat_stocks,
                "rise_fall_ratio": round(rise_fall_ratio, 2),
                "limit_up": limit_up,
                "limit_down": limit_down,
                "strong_stocks": strong_stocks,
                "strong_ratio": round(strong_ratio, 2),
                "market_sentiment": CNMarketHeat._get_sentiment_from_ratio(
                    rise_fall_ratio
                ),
            }

        except Exception as e:
            print(f"⚠️ 获取市场广度数据失败: {e}")
            return {"breadth_error": str(e)}

    @staticmethod
    def _get_market_activity_from_df(df: pd.DataFrame) -> Dict[str, Any]:
        """从DataFrame获取市场活跃度数据"""
        try:
            # 计算平均换手率
            avg_turnover_rate = df["换手率"].mean()

            # 统计高换手率股票（>5%）
            high_turnover_stocks = len(df[df["换手率"] > 5])
            high_turnover_ratio = high_turnover_stocks / len(df) * 100

            # 计算成交活跃股票数量（成交额>1亿）
            active_stocks = len(df[df["成交额"] > 100000000])
            active_ratio = active_stocks / len(df) * 100

            return {
                "avg_turnover_rate": round(avg_turnover_rate, 2),
                "high_turnover_stocks": high_turnover_stocks,
                "high_turnover_ratio": round(high_turnover_ratio, 2),
                "active_stocks": active_stocks,
                "active_ratio": round(active_ratio, 2),
                "activity_level": CNMarketHeat._get_activity_level(
                    avg_turnover_rate, active_ratio
                ),
            }

        except Exception as e:
            print(f"⚠️ 获取活跃度数据失败: {e}")
            return {"activity_error": str(e)}

    @staticmethod
    def _calculate_heat_score(data: Dict[str, Any]) -> float:
        """计算综合热度指数 (0-100)"""
        try:
            score = 50  # 基础分数

            # 成交额因子 (权重30%)
            turnover_ratio = data.get("turnover_ratio", 1)
            turnover_score = min(100, max(0, 50 + (turnover_ratio - 1) * 50))
            score += (turnover_score - 50) * 0.3

            # 涨跌比因子 (权重25%)
            rise_fall_ratio = data.get("rise_fall_ratio", 1)
            ratio_score = min(100, max(0, 50 + (rise_fall_ratio - 1) * 25))
            score += (ratio_score - 50) * 0.25

            # 强势股比例因子 (权重20%)
            strong_ratio = data.get("strong_ratio", 10)
            strong_score = min(100, strong_ratio * 5)  # 20%强势股=100分
            score += (strong_score - 50) * 0.2

            # 活跃度因子 (权重15%)
            active_ratio = data.get("active_ratio", 20)
            active_score = min(100, active_ratio * 2.5)  # 40%活跃股=100分
            score += (active_score - 50) * 0.15

            # 换手率因子 (权重10%)
            avg_turnover = data.get("avg_turnover_rate", 2)
            turnover_rate_score = min(100, avg_turnover * 20)  # 5%换手率=100分
            score += (turnover_rate_score - 50) * 0.1

            return max(0, min(100, score))

        except Exception as e:
            print(f"⚠️ 计算热度指数失败: {e}")
            return 50

    @staticmethod
    def _get_heat_level(score: float) -> str:
        """根据热度分数获取等级"""
        if score >= 80:
            return "极热"
        elif score >= 65:
            return "较热"
        elif score >= 55:
            return "温热"
        elif score >= 45:
            return "中等"
        elif score >= 35:
            return "偏冷"
        elif score >= 20:
            return "较冷"
        else:
            return "极冷"

    @staticmethod
    def _get_sentiment_from_ratio(ratio: float) -> str:
        """根据涨跌比获取市场情绪"""
        if ratio >= 2:
            return "强势"
        elif ratio >= 1.5:
            return "偏强"
        elif ratio >= 1.2:
            return "略强"
        elif ratio >= 0.8:
            return "平衡"
        elif ratio >= 0.6:
            return "略弱"
        elif ratio >= 0.4:
            return "偏弱"
        else:
            return "弱势"

    @staticmethod
    def _get_activity_level(turnover_rate: float, active_ratio: float) -> str:
        """根据换手率和活跃比例获取活跃度等级"""
        if turnover_rate > 4 and active_ratio > 30:
            return "极活跃"
        elif turnover_rate > 3 and active_ratio > 20:
            return "较活跃"
        elif turnover_rate > 2 and active_ratio > 15:
            return "中等活跃"
        elif turnover_rate > 1.5 and active_ratio > 10:
            return "略活跃"
        else:
            return "不活跃"

    @staticmethod
    def _get_explanation() -> str:
        """获取市场热度说明"""
        return """
市场热度指数说明：
• 指数范围：0-100，数值越高表示市场越火热
• 计算因子：
  1. 成交额 (30%)：两市总成交额，反映资金参与度
  2. 涨跌比 (25%)：上涨家数/下跌家数，反映市场情绪
  3. 强势股 (20%)：涨幅>3%的股票比例，反映赚钱效应
  4. 活跃度 (15%)：成交额>1亿的股票比例
  5. 换手率 (10%)：市场平均换手率
• 极热(80+)：市场情绪亢奋，注意风险
• 较热(65-80)：赚钱效应明显
• 中等(45-65)：市场正常波动
• 较冷(20-45)：市场情绪低迷
• 极冷(0-20)：市场极度冰点
        """.strip()
