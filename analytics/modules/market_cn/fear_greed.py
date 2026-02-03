"""
中国市场恐慌贪婪指数
基于多个技术指标计算综合情绪指数
"""

import akshare as ak
import pandas as pd
import numpy as np

from typing import Dict, Any, Optional
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger


class CNFearGreedIndex:
    """中国市场恐慌贪婪指数计算"""

    DEFAULT_WEIGHTS = {
        "price_momentum": 0.20,
        "volatility": 0.15,
        "volume": 0.15,
        "rsi": 0.20,
        "price_position": 0.10,
        "daily_change": 0.20,
    }

    DEFAULT_LEVELS = [
        (80, "极度贪婪", "市场情绪极度乐观，注意风险"),
        (65, "贪婪", "市场情绪偏向乐观，注意风险控制"),
        (55, "轻微贪婪", "市场情绪略显乐观"),
        (45, "中性", "市场情绪相对平衡"),
        (35, "轻微恐慌", "市场情绪略显悲观"),
        (20, "恐慌", "市场情绪偏向悲观"),
        (0, "极度恐慌", "市场情绪极度悲观"),
    ]

    @staticmethod
    def _get_weights() -> Dict[str, float]:
        return settings.FEAR_GREED_CONFIG.get("cn", {}).get("weights", CNFearGreedIndex.DEFAULT_WEIGHTS)

    @staticmethod
    def _get_levels() -> list:
        return settings.FEAR_GREED_CONFIG.get("cn", {}).get("levels", CNFearGreedIndex.DEFAULT_LEVELS)

    @staticmethod
    def _get_levels_payload() -> list:
        return [{"min": t, "label": l, "description": d} for t, l, d in CNFearGreedIndex._get_levels()]

    @staticmethod
    @cached("market_cn:fear_greed", ttl=settings.CACHE_TTL["fear_greed"], stale_ttl=settings.CACHE_TTL["fear_greed"] * settings.STALE_TTL_RATIO)
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
            if days < 2:
                raise ValueError("days 需 >= 2，确保可计算当日涨跌与RSI")

            # 获取指数数据


            # 获取指数行情数据
            index_data = akshare_call_with_retry(ak.stock_zh_index_daily, symbol=symbol)
            if index_data.empty:
                raise ValueError(f"无法获取指数数据: {symbol}")

            # DataFrame schema 校验
            required_columns = {"close", "high", "low"}
            missing_columns = required_columns - set(index_data.columns)
            if missing_columns:
                raise ValueError(f"数据缺少必要列: {missing_columns}")

            # 保证按时间升序
            for date_col in ["date", "trade_date"]:
                if date_col in index_data.columns:
                    index_data = index_data.sort_values(date_col)
                    break

            # 取最近的数据
            recent_data = index_data.tail(days)
            if len(recent_data) < days:
                raise ValueError(f"数据不足，需要{days}天，实际{len(recent_data)}天")

            # 计算各项指标
            indicators = CNFearGreedIndex._calculate_indicators(recent_data, symbol)
            
            # 如果指标计算失败，返回错误
            if "error" in indicators:
                return {
                    "error": indicators["error"],
                    "message": "无法计算指标数据",
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }

            # 计算综合指数 (0-100)
            fear_greed_score = CNFearGreedIndex._calculate_composite_score(indicators)
            
            # 如果无法计算综合得分，返回错误
            if fear_greed_score is None:
                return {
                    "error": "无法计算综合得分",
                    "message": "指标数据不足",
                    "indicators": indicators,
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }

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
                "levels": CNFearGreedIndex._get_levels_payload(),
            }

        except Exception as e:
            logger.error(f"❌ 计算恐慌贪婪指数失败: {e}")
            return {
                "error": str(e),
                "message": "无法计算恐慌贪婪指数",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def _calculate_indicators(data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """计算各项技术指标"""
        indicators = {}

        try:
            # 1. 价格动量 (Price Momentum) - 权重20% (原25%)
            price_change = (
                (data["close"].iloc[-1] - data["close"].iloc[0])
                / data["close"].iloc[0]
                * 100
            )
            momentum_score = min(100, max(0, 50 + price_change * 2))  # 转换为0-100
            indicators["price_momentum"] = {
                "value": round(price_change, 2),
                "score": round(momentum_score, 1),
                "weight": CNFearGreedIndex._get_weights()["price_momentum"],
            }

            # 2. 波动率 (Volatility) - 权重15%
            returns = data["close"].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100  # 年化波动率
            if pd.isna(volatility):
                return {"error": "波动率数据不足"}
            # 波动率越高，恐慌程度越高，分数越低
            volatility_score = max(0, min(100, 100 - volatility * 2))
            indicators["volatility"] = {
                "value": round(volatility, 2),
                "score": round(volatility_score, 1),
                "weight": CNFearGreedIndex._get_weights()["volatility"],
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
                    "weight": CNFearGreedIndex._get_weights()["volume"],
                }
            else:
                # 成交量数据不可用，跳过该指标（不填充假数据）
                logger.warning("⚠️ 成交量数据不可用，跳过 volume 指标")

            # 4. RSI指标 - 权重20% (不变)
            rsi = CNFearGreedIndex._calculate_rsi(data["close"])
            if rsi is None:
                return {"error": "RSI 数据不足"}
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
                "weight": CNFearGreedIndex._get_weights()["rsi"],
            }

            # 5. 价格区间位置 (Price Position) - 权重10%
            # 这里简化处理，使用价格区间相对位置（并非真实涨跌家数广度）
            price_range = data["high"].max() - data["low"].min()
            if price_range <= 0:
                return {"error": "价格区间不足，无法计算区间位置"}
            high_low_ratio = (data["close"].iloc[-1] - data["low"].min()) / price_range
            breadth_score = max(0, min(100, high_low_ratio * 100))
            indicators["price_position"] = {
                "value": round(high_low_ratio, 3),
                "score": round(breadth_score, 1),
                "weight": CNFearGreedIndex._get_weights()["price_position"],
            }
            # 兼容旧字段名
            indicators["market_breadth"] = indicators["price_position"]

            # 6. 当日涨跌 (Daily Change) - 权重20% (新增)
            # 增强对当日市场表现的敏感度
            if len(data) < 2:
                return {"error": "当日涨跌数据不足"}
            daily_chg_pct = (
                (data["close"].iloc[-1] - data["close"].iloc[-2])
                / data["close"].iloc[-2]
                * 100
            )
            daily_score = 50 + (daily_chg_pct * 10) # 1%涨幅 = +10分
            daily_score = min(100, max(0, daily_score))
            indicators["daily_change"] = {
                "value": round(daily_chg_pct, 2),
                "score": round(daily_score, 1),
                "weight": CNFearGreedIndex._get_weights()["daily_change"],
            }

        except Exception as e:
            logger.warning(f"⚠️ 计算指标时出错: {e}")
            # 返回错误而非假数据
            return {"error": str(e)}

        return indicators

    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
        """计算RSI指标"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
        except Exception:
            return None

    @staticmethod
    def _calculate_composite_score(indicators: Dict[str, Any]) -> Optional[float]:
        """计算综合得分，跳过有错误的指标"""
        # 如果指标本身是错误，返回 None
        if "error" in indicators:
            return None
        
        total_score: float = 0.0
        total_weight: float = 0.0
        valid_count = 0

        for indicator in indicators.values():
            # 跳过有错误的指标
            if "error" in indicator:
                continue
            
            score = safe_float(indicator.get("score"))
            weight = safe_float(indicator.get("weight", 0))
            
            if score is not None and weight > 0:
                total_score += score * weight
                total_weight += weight
                valid_count += 1

        # 如果没有有效指标，返回 None
        if total_weight == 0 or valid_count == 0:
            return None
        
        return total_score / total_weight

    @staticmethod
    def _get_level_description(score: float) -> tuple:
        """根据分数获取等级和描述"""
        for threshold, level, description in CNFearGreedIndex._get_levels():
            if score >= threshold:
                return level, description
        return "未知", "无法判断情绪等级"

    @staticmethod
    def _get_explanation() -> str:
        """获取指数说明"""
        weights = CNFearGreedIndex._get_weights()
        levels = CNFearGreedIndex._get_levels()
        level_lines = []
        for i, (min_score, label, _) in enumerate(levels):
            max_score = 100 if i == 0 else levels[i - 1][0] - 1
            level_lines.append(f"• {label}({min_score}-{max_score})")
        level_lines = "\n".join(level_lines)
        return """
恐慌贪婪指数说明：
• 指数范围：0-100，数值越高表示市场越贪婪
• 计算因子：价格动量({pm}%)、当日涨跌({dc}%)、RSI({rsi}%)、波动率({vol}%)、成交量({volu}%)、价格区间位置({pos}%)
{levels}
• 说明：此指标为技术指标合成，不构成投资建议
        """.strip().format(
            pm=int(weights["price_momentum"] * 100),
            dc=int(weights["daily_change"] * 100),
            rsi=int(weights["rsi"] * 100),
            vol=int(weights["volatility"] * 100),
            volu=int(weights["volume"] * 100),
            pos=int(weights["price_position"] * 100),
            levels=level_lines
        )
