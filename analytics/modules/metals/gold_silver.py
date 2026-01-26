"""
金银比分析
计算金银比及相关投资分析
使用 COMEX 期货数据 (美元计价)
"""

import akshare as ak
from typing import Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger


class GoldSilverAnalysis:
    """金银比分析 (COMEX 美元计价)"""

    # COMEX 合约代码
    GOLD_CODE = "GC00Y"   # COMEX黄金主力
    SILVER_CODE = "SI00Y"  # COMEX白银主力

    # 阈值常量 (用于分析金银比水平)
    # 核心逻辑：基于50年历史均值(65.0)的标准差偏离
    RATIO_LEVEL_EXTREME_HIGH = 90.0  # 极高 (> +25)
    RATIO_LEVEL_HIGH = 80.0          # 偏高 (> +15)
    RATIO_LEVEL_LOW = 55.0           # 偏低 (< -10)
    RATIO_LEVEL_EXTREME_LOW = 45.0   # 极低 (< -20)

    @staticmethod
    @cached("metals:gold_silver_ratio", ttl=settings.CACHE_TTL["metals"], stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO)
    def get_gold_silver_ratio() -> Dict[str, Any]:
        """
        获取金银比数据和分析 (COMEX 美元计价)

        Returns:
            Dict[str, Any]: 包含黄金价格、白银价格、比率及投资建议的字典
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

            if gold_price is None or silver_price is None or gold_price <= 0 or silver_price <= 0:
                return {"error": "价格数据无效", "ratio": {"current": 0}}

            # 计算金银比 (无量纲)
            ratio = gold_price / silver_price

            # 分析
            ratio_analysis = GoldSilverAnalysis._analyze_ratio_level(ratio)
            investment_advice = GoldSilverAnalysis._get_investment_advice(
                ratio, ratio_analysis
            )

            return {
                "gold": {
                    "price": round(gold_price, 2),
                    "change_pct": round(gold_change if gold_change else 0.0, 2),
                    "unit": "USD/oz",
                    "name": "COMEX黄金",
                },
                "silver": {
                    "price": round(silver_price, 2),
                    "change_pct": round(silver_change if silver_change else 0.0, 2),
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
            logger.error(f" 获取金银比失败: {e}")
            return {"error": str(e), "ratio": {"current": 0}}

    @staticmethod
    def _analyze_ratio_level(current_ratio: float) -> Dict[str, str]:
        """
        分析金银比所处的历史水平区间

        Args:
            current_ratio (float): 当前金银比值

        Returns:
            Dict[str, str]: 包含 level (评级) 和 comment (评价)
        """
        if current_ratio > GoldSilverAnalysis.RATIO_LEVEL_EXTREME_HIGH:
            level = "极高"
            comment = "处于历史高位区域"
        elif current_ratio > GoldSilverAnalysis.RATIO_LEVEL_HIGH:
            level = "偏高"
            comment = "高于历史均值"
        elif current_ratio < GoldSilverAnalysis.RATIO_LEVEL_EXTREME_LOW:
            level = "极低"
            comment = "处于历史低位区域"
        elif current_ratio < GoldSilverAnalysis.RATIO_LEVEL_LOW:
            level = "偏低"
            comment = "低于历史均值"
        else:
            level = "正常"
            comment = "处于合理波动区间"

        return {"level": level, "comment": comment}

    @staticmethod
    def _get_investment_advice(
        ratio: float, analysis: Dict[str, str]
    ) -> Dict[str, str]:
        """
        根据金银比水平生成投资参考建议

        Args:
            ratio (float): 当前金银比
            analysis (Dict[str, str]): 包含 level 的分析结果

        Returns:
            Dict[str, str]: 包含 strategy (策略) 和 reasoning (理由)
        """
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
        """
        获取前端显示的说明文本 (Explain Why)
        
        Returns:
            str: 格式化的说明文本
        """
        return f"""
金银比(Gold-Silver Ratio)说明：
• 定义：1盎司黄金价格 ÷ 1盎司白银价格
• 核心逻辑：
  - 均值回归：历史长期均值约 {GoldSilverAnalysis.HISTORICAL_AVG}
  - 高位 (>{int(GoldSilverAnalysis.RATIO_LEVEL_HIGH)})：暗示白银相对黄金超卖，或有补涨需求
  - 低位 (<{int(GoldSilverAnalysis.RATIO_LEVEL_LOW)})：暗示白银投机情绪过热，黄金避险性价比提升
• 策略参考：利用比值偏离均值的机会，进行相对价值配置
        """.strip()
