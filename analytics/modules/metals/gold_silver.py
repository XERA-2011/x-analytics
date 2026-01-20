"""
金银比分析
计算金银比及相关投资分析
"""

import akshare as ak
from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time


class GoldSilverAnalysis:
    """金银比分析"""

    @staticmethod
    @cached("metals:gold_silver_ratio", ttl=settings.CACHE_TTL["metals"], stale_ttl=600)
    def get_gold_silver_ratio() -> Dict[str, Any]:
        """
        获取金银比数据和分析
        """
        try:
            gold_price = 0
            silver_price = 0
            gold_change = 0
            silver_change = 0

            try:
                # 获取黄金 Au99.99
                df_gold = ak.spot_quotations_sge(symbol="Au99.99")
                if not df_gold.empty:
                    latest_gold = df_gold.iloc[-1]
                    gold_price = safe_float(latest_gold["现价"])  # 元/克
                    # 估算涨跌
                    if len(df_gold) > 1:
                        open_gold = safe_float(df_gold.iloc[0]["现价"])
                        if open_gold > 0:
                            gold_change = (gold_price - open_gold) / open_gold * 100

                # 获取白银 Ag(T+D)
                # 注意：Ag(T+D) 是 元/千克
                df_silver = ak.spot_quotations_sge(symbol="Ag(T+D)")
                if not df_silver.empty:
                    latest_silver = df_silver.iloc[-1]
                    silver_price_kg = safe_float(latest_silver["现价"])  # 元/千克
                    silver_price = silver_price_kg / 1000  # 换算为 元/克
                    # 估算涨跌
                    if len(df_silver) > 1:
                        open_silver = safe_float(df_silver.iloc[0]["现价"])
                        if open_silver > 0:
                            silver_change = (
                                (silver_price_kg - open_silver) / open_silver * 100
                            )

            except Exception as e_sge:
                print(f"获取 SGE 数据失败: {e_sge}")

            if gold_price <= 0 or silver_price <= 0:
                print("无法获取有效的金银价格")
                return {"error": "数据源不可用", "ratio": {"current": 0}}

            # 计算金银比 (无量纲)
            ratio = gold_price / silver_price

            # 分析
            history_data = []  # 暂无历史
            ratio_analysis = GoldSilverAnalysis._analyze_ratio_level(
                ratio, history_data
            )
            investment_advice = GoldSilverAnalysis._get_investment_advice(
                ratio, ratio_analysis
            )

            return {
                "gold": {
                    "price": gold_price,
                    "change_pct": round(gold_change, 2),
                    "unit": "元/克 (SGE参考)",
                    "name": "黄金9999",
                },
                "silver": {
                    "price": silver_price * 1000,  # 还原为 元/千克 展示习惯
                    "change_pct": round(silver_change, 2),
                    "unit": "元/千克 (SGE参考)",
                    "name": "白银T+D",
                },
                "ratio": {
                    "current": round(ratio, 2),
                    "analysis": ratio_analysis,
                    "investment_advice": investment_advice,
                },
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "explanation": GoldSilverAnalysis._get_explanation(),
            }

        except Exception as e:
            print(f"❌ 获取金银比失败: {e}")
            return {"error": str(e), "ratio": {"current": 0}}

    @staticmethod
    def _analyze_ratio_level(
        current_ratio: float, history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析金银比水平"""
        # 简化版分析

        if current_ratio > 90:
            level = "极高"
            comment = "白银相对被低估"
        elif current_ratio > 85:
            level = "偏高"
            comment = "白银相对便宜"
        elif current_ratio < 65:
            level = "极低"
            comment = "黄金相对被低估"
        elif current_ratio < 75:
            level = "偏低"
            comment = "黄金相对便宜"
        else:
            level = "正常"
            comment = "处于合理区间"

        return {"level": level, "comment": comment}

    @staticmethod
    def _get_investment_advice(
        ratio: float, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """获取投资建议"""
        level = analysis.get("level", "正常")
        if level in ["极高", "偏高"]:
            return {
                "preferred_metal": "白银",
                "strategy": "关注白银",
                "reasoning": "金银比高企，白银胜率较高",
            }
        elif level in ["极低", "偏低"]:
            return {
                "preferred_metal": "黄金",
                "strategy": "关注黄金",
                "reasoning": "金银比低位，黄金性价比较高",
            }
        else:
            return {
                "preferred_metal": "均衡",
                "strategy": "均衡配置",
                "reasoning": "金银比正常",
            }

    @staticmethod
    def _get_explanation() -> str:
        return """
金银比(Gold-Silver Ratio)说明：
• 定义：黄金价格与白银价格的比值
• 核心逻辑：比值过高暗示白银低估，比值过低暗示黄金低估
• 数据来源：上海黄金交易所(SGE)现货价格
        """.strip()
