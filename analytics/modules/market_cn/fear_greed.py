"""
中国市场恐慌贪婪指数
基于多个技术指标计算综合情绪指数
"""

import akshare as ak
import pandas as pd
import numpy as np

from typing import Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time


class CNFearGreedIndex:
    """中国市场恐慌贪婪指数计算"""

    @staticmethod
    @cached("market_cn:fear_greed", ttl=settings.CACHE_TTL["fear_greed"], stale_ttl=300)
    def calculate(symbol: str = "sh000001", days: int = 14) -> Dict[str, Any]:
        """
        计算恐慌贪婪指数

        Args:
            symbol: 指数代码，默认上证指数
            days: 计算天数

        Returns:
            包含指数值、等级、各项指标的字典
        """
        try:
            # 获取指数数据


            # 获取指数行情数据
            index_data = ak.stock_zh_index_daily(symbol=symbol)
            if index_data.empty:
                raise ValueError(f"无法获取指数数据: {symbol}")

            # 取最近的数据
            recent_data = index_data.tail(days)
            if len(recent_data) < days:
                raise ValueError(f"数据不足，需要{days}天，实际{len(recent_data)}天")

            # 计算各项指标
            indicators = CNFearGreedIndex._calculate_indicators(recent_data, symbol)

            # 计算综合指数 (0-100)
            fear_greed_score = CNFearGreedIndex._calculate_composite_score(indicators)

            # 确定等级
            level, description = CNFearGreedIndex._get_level_description(
                fear_greed_score
            )

            return {
                "score": round(fear_greed_score, 1),
                "level": level,
                "description": description,
                "indicators": indicators,
                "symbol": symbol,
                "days": days,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "explanation": CNFearGreedIndex._get_explanation(),
            }

        except Exception as e:
            print(f"❌ 计算恐慌贪婪指数失败: {e}")
            return {
                "error": str(e),
                "score": 50,  # 默认中性
                "level": "中性",
                "description": "数据获取失败，显示默认值",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def _calculate_indicators(data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """计算各项技术指标"""
        indicators = {}

        try:
            # 1. 价格动量 (Price Momentum) - 权重25%
            price_change = (
                (data["close"].iloc[-1] - data["close"].iloc[0])
                / data["close"].iloc[0]
                * 100
            )
            momentum_score = min(100, max(0, 50 + price_change * 2))  # 转换为0-100
            indicators["price_momentum"] = {
                "value": round(price_change, 2),
                "score": round(momentum_score, 1),
                "weight": 0.25,
            }

            # 2. 波动率 (Volatility) - 权重20%
            returns = data["close"].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100  # 年化波动率
            # 波动率越高，恐慌程度越高，分数越低
            volatility_score = max(0, min(100, 100 - volatility * 2))
            indicators["volatility"] = {
                "value": round(volatility, 2),
                "score": round(volatility_score, 1),
                "weight": 0.20,
            }

            # 3. 成交量 (Volume) - 权重15%
            if "volume" in data.columns:
                avg_volume = data["volume"].tail(5).mean()
                prev_avg_volume = data["volume"].head(5).mean()
                volume_change = (
                    (avg_volume - prev_avg_volume) / prev_avg_volume * 100
                    if prev_avg_volume > 0
                    else 0
                )
                volume_score = min(100, max(0, 50 + volume_change * 0.5))
                indicators["volume"] = {
                    "value": round(volume_change, 2),
                    "score": round(volume_score, 1),
                    "weight": 0.15,
                }
            else:
                indicators["volume"] = {"value": 0, "score": 50, "weight": 0.15}

            # 4. RSI指标 - 权重20%
            rsi = CNFearGreedIndex._calculate_rsi(data["close"])
            # RSI > 70 贪婪，RSI < 30 恐慌
            if rsi > 70:
                rsi_score = 70 + (rsi - 70) * 1.5  # 贪婪区间
            elif rsi < 30:
                rsi_score = rsi * 1.67  # 恐慌区间
            else:
                rsi_score = 30 + (rsi - 30) * 1  # 中性区间
            rsi_score = min(100, max(0, rsi_score))
            indicators["rsi"] = {
                "value": round(rsi, 2),
                "score": round(rsi_score, 1),
                "weight": 0.20,
            }

            # 5. 市场广度 (Market Breadth) - 权重20%
            # 这里简化处理，使用价格相对位置
            high_low_ratio = (data["close"].iloc[-1] - data["low"].min()) / (
                data["high"].max() - data["low"].min()
            )
            breadth_score = high_low_ratio * 100
            indicators["market_breadth"] = {
                "value": round(high_low_ratio, 3),
                "score": round(breadth_score, 1),
                "weight": 0.20,
            }

        except Exception as e:
            print(f"⚠️ 计算指标时出错: {e}")
            # 返回默认值
            indicators = {
                "price_momentum": {"value": 0, "score": 50, "weight": 0.25},
                "volatility": {"value": 20, "score": 50, "weight": 0.20},
                "volume": {"value": 0, "score": 50, "weight": 0.15},
                "rsi": {"value": 50, "score": 50, "weight": 0.20},
                "market_breadth": {"value": 0.5, "score": 50, "weight": 0.20},
            }

        return indicators

    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """计算RSI指标"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        except Exception:
            return 50

    @staticmethod
    def _calculate_composite_score(indicators: Dict[str, Any]) -> float:
        """计算综合得分"""
        total_score = 0
        total_weight = 0

        for indicator in indicators.values():
            score = safe_float(indicator.get("score", 50))
            weight = safe_float(indicator.get("weight", 0))
            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 50

    @staticmethod
    def _get_level_description(score: float) -> tuple:
        """根据分数获取等级和描述"""
        if score >= 80:
            return "极度贪婪", "市场情绪极度乐观，可能存在泡沫风险"
        elif score >= 65:
            return "贪婪", "市场情绪偏向乐观，注意风险控制"
        elif score >= 55:
            return "轻微贪婪", "市场情绪略显乐观"
        elif score >= 45:
            return "中性", "市场情绪相对平衡"
        elif score >= 35:
            return "轻微恐慌", "市场情绪略显悲观"
        elif score >= 20:
            return "恐慌", "市场情绪偏向悲观，可能存在机会"
        else:
            return "极度恐慌", "市场情绪极度悲观，可能是抄底时机"

    @staticmethod
    def _get_explanation() -> str:
        """获取指数说明"""
        return """
恐慌贪婪指数说明：
• 指数范围：0-100，数值越高表示市场越贪婪
• 计算因子：价格动量(25%)、波动率(20%)、RSI(20%)、市场广度(20%)、成交量(15%)
• 极度恐慌(0-20)：可能是买入时机
• 恐慌(20-35)：市场悲观，谨慎观望
• 中性(35-65)：市场情绪平衡
• 贪婪(65-80)：市场乐观，注意风险
• 极度贪婪(80-100)：可能存在泡沫，考虑减仓
        """.strip()
