"""
金银比分析
计算金银比及相关投资分析
使用 COMEX 期货数据 (美元计价)
"""

import akshare as ak
from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry


class GoldSilverAnalysis:
    """金银比分析 (COMEX 美元计价)"""

    # COMEX 合约代码
    GOLD_CODE = "GC00Y"   # COMEX黄金主力
    SILVER_CODE = "SI00Y"  # COMEX白银主力

    # 历史统计 (数据来源: 50年历史数据)
    HISTORICAL_HIGH = 123.8   # 2020年3月 COVID危机
    HISTORICAL_LOW = 14.0     # 1980年1月 (白银投机泡沫)
    HISTORICAL_AVG = 65.0     # 50年历史均值

    @staticmethod
    @cached("metals:gold_silver_ratio", ttl=settings.CACHE_TTL["metals"], stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO)
    def get_gold_silver_ratio() -> Dict[str, Any]:
        """
        获取金银比数据和分析 (COMEX 美元计价)
        """
        try:
            # 使用带重试的 API 调用
            df = akshare_call_with_retry(ak.futures_global_spot_em)

            if df.empty:
                return {"error": "无法获取期货数据", "ratio": {"current": 0}}

            # 获取黄金数据
            gold_row = df[df["代码"] == GoldSilverAnalysis.GOLD_CODE]
            silver_row = df[df["代码"] == GoldSilverAnalysis.SILVER_CODE]

            # 备用合约代码
            if gold_row.empty:
                gold_row = df[df["代码"].str.contains("GC2", na=False)].head(1)
            if silver_row.empty:
                silver_row = df[df["代码"].str.contains("SI2", na=False)].head(1)

            if gold_row.empty or silver_row.empty:
                return {"error": "无法获取黄金或白银数据", "ratio": {"current": 0}}

            gold = gold_row.iloc[0]
            silver = silver_row.iloc[0]

            gold_price = safe_float(gold["最新价"])
            silver_price = safe_float(silver["最新价"])
            gold_change = safe_float(gold["涨跌幅"])
            silver_change = safe_float(silver["涨跌幅"])

            if gold_price <= 0 or silver_price <= 0:
                return {"error": "价格数据无效", "ratio": {"current": 0}}

            # 计算金银比 (无量纲)
            ratio = gold_price / silver_price

            # 分析
            ratio_analysis = GoldSilverAnalysis._analyze_ratio_level(ratio, [])
            investment_advice = GoldSilverAnalysis._get_investment_advice(
                ratio, ratio_analysis
            )

            return {
                "gold": {
                    "price": round(gold_price, 2),
                    "change_pct": round(gold_change, 2),
                    "unit": "USD/oz",
                    "name": "COMEX黄金",
                },
                "silver": {
                    "price": round(silver_price, 2),
                    "change_pct": round(silver_change, 2),
                    "unit": "USD/oz",
                    "name": "COMEX白银",
                },
                "ratio": {
                    "current": round(ratio, 2),
                    "historical_high": GoldSilverAnalysis.HISTORICAL_HIGH,
                    "historical_low": GoldSilverAnalysis.HISTORICAL_LOW,
                    "historical_avg": GoldSilverAnalysis.HISTORICAL_AVG,
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
        # 基于历史均值 65.0 左右的正态分布逻辑调整
        # > 90: 极高 (偏离均值 +25)
        # 80-90: 偏高 (偏离均值 +15)
        # 55-80: 正常 (涵盖均值 65)
        # 45-55: 偏低
        # < 45: 极低

        if current_ratio > 90:
            level = "极高"
            comment = "处于历史高位区域"
        elif current_ratio > 80:
            level = "偏高"
            comment = "高于历史均值"
        elif current_ratio < 45:
            level = "极低"
            comment = "处于历史低位区域"
        elif current_ratio < 55:
            level = "偏低"
            comment = "低于历史均值"
        else:
            level = "正常"
            comment = "处于合理波动区间"

        return {"level": level, "comment": comment}

    @staticmethod
    def _get_investment_advice(
        ratio: float, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """获取投资建议 (仅供参考)"""
        level = analysis.get("level", "正常")
        
        if level in ["极高"]:
            return {
                "preferred_metal": "白银",
                "strategy": "关注白银修复机会",
                "reasoning": "金银比处于历史高位，统计上白银跑赢黄金概率较高 (仅供参考)",
            }
        elif level in ["偏高"]:
            return {
                "preferred_metal": "白银",
                "strategy": "适当关注白银",
                "reasoning": "金银比偏高，白银相对黄金性价比提升",
            }
        elif level in ["极低"]:
            return {
                "preferred_metal": "黄金",
                "strategy": "关注黄金避险属性",
                "reasoning": "金银比处于历史低位，统计上黄金跑赢白银概率较高 (仅供参考)",
            }
        elif level in ["偏低"]:
            return {
                "preferred_metal": "黄金",
                "strategy": "适当关注黄金",
                "reasoning": "金银比偏低，黄金相对白银性价比提升",
            }
        else:
            return {
                "preferred_metal": "均衡",
                "strategy": "均衡配置策略",
                "reasoning": "金银比处于正常区间，建议维持均衡配置",
            }

    @staticmethod
    def _get_explanation() -> str:
        return """
金银比(Gold-Silver Ratio)说明：
• 定义：1盎司黄金价格 ÷ 1盎司白银价格
• 核心逻辑：
  - 均值回归：历史长期均值约 65.0
  - 高位 (>80)：暗示白银相对黄金超卖，或有补涨需求
  - 低位 (<55)：暗示白银投机情绪过热，黄金避险性价比提升
• 策略参考：利用比值偏离均值的机会，进行相对价值配置
        """.strip()
