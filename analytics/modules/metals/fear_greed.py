"""
黄金恐慌贪婪指数 (Custom)
基于技术指标计算: RSI, 波动率, 动量, 均线偏离
"""

import akshare as ak
import pandas as pd
import numpy as np

from typing import Dict, Any, List, Optional
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger

class GoldFearGreedIndex:
    """黄金市场恐慌贪婪指数计算"""

    # 黄金现货/期货代码 (使用 沪金主力 Au0 作为替代，因 COMEX 接口不稳定)
    GOLD_SYMBOL = "au0"

    @staticmethod
    @cached("metals:fear_greed", ttl=settings.CACHE_TTL["metals"], stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO)
    def calculate() -> Dict[str, Any]:
        """
        计算黄金恐慌贪婪指数
        """
        try:
            # 获取历史数据 (用于计算指标)
            # 使用 ak.futures_zh_daily_sina 获取沪金主力合约日线数据
            df = akshare_call_with_retry(ak.futures_zh_daily_sina, symbol=GoldFearGreedIndex.GOLD_SYMBOL)
            
            if df.empty or len(df) < 60:
                raise ValueError("无法获取足够的黄金历史数据")
            
            # 数据清洗
            # futures_zh_daily 返回列: date, open, high, low, close, volume, ...
            df.columns = [c.lower() for c in df.columns]
            
            # 确保按日期升序
            if "date" in df.columns:
                df = df.sort_values(by="date")
            elif "time" in df.columns: # Sometimes it returns 'time'
                 df = df.rename(columns={"time": "date"})
                 df = df.sort_values(by="date")
            
            # 计算各项指标
            indicators = GoldFearGreedIndex._calculate_indicators(df)
            
            # 计算综合得分
            score = GoldFearGreedIndex._calculate_composite_score(indicators)
            
            # 等级描述
            level, description = GoldFearGreedIndex._get_level_description(score)
            
            return {
                "score": round(score, 1),
                "level": level,
                "description": description,
                "indicators": indicators,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "explanation": GoldFearGreedIndex._get_explanation()
            }

        except Exception as e:
            logger.error(f" 计算黄金恐慌贪婪指数失败: {e}")
            return {
                "error": str(e),
                "score": 50,
                "level": "中性",
                "description": "数据获取失败",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def _calculate_indicators(df: pd.DataFrame) -> Dict[str, Any]:
        """计算技术指标"""
        indicators = {}
        try:
            close_prices = df["close"]
            
            # 1. RSI (14) - 权重 30%
            rsi = GoldFearGreedIndex._calculate_rsi(close_prices, 14)
            # RSI > 80: 极度贪婪, < 20: 极度恐慌
            # 映射 0-100: 
            # RSI=50 -> 50
            # RSI=80 -> 90
            # RSI=20 -> 10
            if rsi > 50:
                 score_rsi = 50 + (rsi - 50) * 1.33  # 50->50, 80->90
            else:
                 score_rsi = 50 - (50 - rsi) * 1.33  # 50->50, 20->10
            score_rsi = min(100, max(0, score_rsi))
            
            indicators["rsi"] = {
                "value": round(rsi, 2),
                "score": round(score_rsi, 1),
                "weight": 0.30,
                "name": "RSI (14)"
            }

            # 2. 波动率 (Volatility) - 权重 20%
            # 比较当前波动率与历史平均波动率
            # 波动率高 -> 恐慌
            returns = close_prices.pct_change()
            current_vol = returns.tail(20).std() * np.sqrt(252) # 当前20日年化波动
            avg_vol = returns.tail(60).std() * np.sqrt(252)     # 过去60日年化波动
            
            if pd.isna(current_vol) or pd.isna(avg_vol) or avg_vol == 0:
                vol_ratio = 1.0
            else:
                vol_ratio = current_vol / avg_vol
            
            # Ratio > 1.5 -> 恐慌 (Score < 30)
            # Ratio < 0.7 -> 贪婪 (Score > 70) (低波动通常伴随牛市，但也可能是暴跌前夕，这里简化为平稳=贪婪)
            # 修正: 黄金作为避险资产，高波动通常意味着恐慌买入或恐慌抛售。
            # 传统VIX逻辑: 高波动=恐慌=低分。
            # 1.0 -> 50
            # 1.5 -> 20
            # 0.5 -> 80
            score_vol = 50 - (vol_ratio - 1.0) * 60 
            score_vol = min(100, max(0, score_vol))
             
            indicators["volatility"] = {
                "value": round(current_vol * 100, 2), # Show as %
                "ratio": round(vol_ratio, 2),
                "score": round(score_vol, 1),
                "weight": 0.20,
                "name": "波动率趋势"
            }
            
            # 3. 价格动量 (Momentum) vs 均线 - 权重 30%
            # 当前价格 vs MA50
            current_price = close_prices.iloc[-1]
            ma50 = close_prices.rolling(window=50).mean().iloc[-1]
            
            if pd.isna(ma50):
                ma50 = close_prices.mean()
                
            bias = (current_price - ma50) / ma50 * 100
            
            # Bias = +10% -> 贪婪 (90分)
            # Bias = -10% -> 恐慌 (10分)
            score_mom = 50 + bias * 4
            score_mom = min(100, max(0, score_mom))
            
            indicators["momentum"] = {
                "value": round(bias, 2), # Bias %
                "score": round(score_mom, 1),
                "weight": 0.30,
                "name": "均线偏离 (MA50)"
            }
            
            # 4. 短期趋势 (5日涨跌) - 权重 20%
            change_5d = (close_prices.iloc[-1] - close_prices.iloc[-6]) / close_prices.iloc[-6] * 100
            # +5% -> 90分
            # -5% -> 10分
            score_trend = 50 + change_5d * 8
            score_trend = min(100, max(0, score_trend))
            
            indicators["trend"] = {
                "value": round(change_5d, 2),
                "score": round(score_trend, 1),
                "weight": 0.20,
                "name": "周趋势"
            }
            
        except Exception as e:
            logger.warning(f"指标计算部分失败: {e}")
            # Fallback
            return {}
            
        return indicators

    @staticmethod
    def _calculate_rsi(series: pd.Series, period: int = 14) -> float:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0

    @staticmethod
    def _calculate_composite_score(indicators: Dict[str, Any]) -> float:
        total_score = 0.0
        total_weight = 0.0
        
        for k, v in indicators.items():
            if "score" in v and "weight" in v:
                total_score += v["score"] * v["weight"]
                total_weight += v["weight"]
                
        if total_weight == 0:
            return 50.0
            
        return total_score / total_weight

    @staticmethod
    def _get_level_description(score: float) -> tuple:
        if score >= 85: return "极度贪婪", "市场情绪极度高涨，注意回调风险"
        if score >= 65: return "贪婪", "买盘积极，趋势向好"
        if score >= 45: return "中性", "多空平衡，方向不明"
        if score >= 25: return "恐慌", "抛压较重，市场悲观"
        return "极度恐慌", "非理性抛售，可能存在超跌反弹机会"

    @staticmethod
    def _get_explanation() -> str:
        return """
黄金恐慌贪婪指数模型：
• 核心逻辑：基于价格行为(Price Action)量化市场情绪
• 组成因子：
  1. RSI (30%)：相对强弱指标，衡量超买超卖
  2. 均线偏离 (30%)：当前价格与50日均线乖离率
  3. 波动率 (20%)：近期波动率与历史波动率对比
  4. 周趋势 (20%)：近5日价格动量
• 分值解读：
  - 0-25 (极度恐慌)：往往对应阶段性底部
  - 75-100 (极度贪婪)：往往对应阶段性顶部
""".strip()
