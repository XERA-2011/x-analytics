
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any
from analytics.core.cache import cached
from analytics.core.config import settings
from analytics.core.logger import logger
from analytics.core.utils import get_beijing_time, akshare_call_with_retry

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    return 100 - (100 / (1 + rs))

class HKFearGreed:
    DEFAULT_WEIGHTS = {
        "rsi": 0.35,
        "bias": 0.35,
        "daily_change": 0.30,
    }

    DEFAULT_LEVELS = [
        (75, "极度贪婪", "市场情绪极度乐观"),
        (55, "贪婪", "市场情绪偏向乐观"),
        (45, "中性", "市场情绪平衡"),
        (25, "恐慌", "市场情绪偏悲观"),
        (0, "极度恐慌", "市场情绪极度悲观"),
    ]

    @staticmethod
    def _get_weights() -> Dict[str, float]:
        return settings.FEAR_GREED_CONFIG.get("hk", {}).get("weights", HKFearGreed.DEFAULT_WEIGHTS)

    @staticmethod
    def _get_levels() -> list:
        return settings.FEAR_GREED_CONFIG.get("hk", {}).get("levels", HKFearGreed.DEFAULT_LEVELS)

    @staticmethod
    def _get_levels_payload() -> list:
        return [{"min": t, "label": l, "description": d} for t, l, d in HKFearGreed._get_levels()]

    @staticmethod
    def _sort_by_date(df: pd.DataFrame) -> pd.DataFrame:
        for date_col in ["date", "trade_date", "datetime"]:
            if date_col in df.columns:
                return df.sort_values(date_col)
        return df

    @staticmethod
    @cached(
        "market_hk:fear_greed",
        ttl=settings.CACHE_TTL["market"],  # Use standard market data TTL
        stale_ttl=settings.CACHE_TTL["market"] * settings.STALE_TTL_RATIO
    )
    def get_data() -> Dict[str, Any]:
        try:
            # 1. Fetch HSI Daily Data (for RSI and Bias)
            df = akshare_call_with_retry(ak.stock_hk_index_daily_sina, symbol="HSI")
            
            if df.empty or len(df) < 60:
                raise ValueError("Insufficient historical data for HSI")

            # Ensure numeric
            df['close'] = pd.to_numeric(df['close'])
            df = HKFearGreed._sort_by_date(df)
            
            # --- Indicator 1: RSI (14) ---
            # Measures Momentum: >70 Overbought (Greed), <30 Oversold (Fear)
            # We map 30-70 to Linear 0-100 roughly. 
            # Or better: Map RSI directly to score? 
            # Classic Fear/Greed: Low RSI = Fear (Low Score), High RSI = Greed (High Score).
            # So calculating RSI directly gives us a 0-100 score base.
            df['rsi'] = calculate_rsi(df['close'], 14)
            current_rsi = df['rsi'].iloc[-1]
            if pd.isna(current_rsi):
                current_rsi = 50.0

            # --- Indicator 2: Bias (60) ---
            # Price vs 60-day MA.
            # > +10% High Greed, < -10% High Fear.
            df['ma60'] = df['close'].rolling(window=60).mean()
            current_price = df['close'].iloc[-1]
            current_ma60 = df['ma60'].iloc[-1]
            if pd.isna(current_ma60) or current_ma60 == 0:
                current_ma60 = df['close'].rolling(window=60).mean().dropna().iloc[-1]
            
            # Calculate Bias%
            bias_pct = ((current_price - current_ma60) / current_ma60) * 100
            
            # Map Bias to 0-100 Score
            # Assume -20% is 0 (Extreme Fear), +20% is 100 (Extreme Greed), 0% is 50.
            # Linear mapping: Score = 50 + (Bias * 2.5) => 20*2.5 = 50.
            bias_score = 50 + (bias_pct * 2.5)
            bias_score = max(0, min(100, bias_score))

            # --- Indicator 3: Daily Change (Market Sentiment) ---
            # 权重 30%: 让当日大跌能显著拉低分数
            prev_close = df['close'].iloc[-2]
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            # Map Change% to 0-100
            # 0% = 50 (Neutral)
            # +1% = 60, -1% = 40 (Sensitivity: 10 points per 1%)
            # Max/Min clumping handled later
            daily_score = 50 + (change_pct * 10)
            daily_score = max(0, min(100, daily_score))

            # --- Final Score Calculation ---
            # Weights: RSI (35%), Bias (35%), Daily Change (30%)
            weights = HKFearGreed._get_weights()
            final_score = (
                (current_rsi * weights["rsi"])
                + (bias_score * weights["bias"])
                + (daily_score * weights["daily_change"])
            )
            final_score = round(final_score, 1)

            # Determine Level
            level_cn = "未知"
            for threshold, label, _desc in HKFearGreed._get_levels():
                if final_score >= threshold:
                    level_cn = label
                    break

            return {
                "score": final_score,
                "level": level_cn,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "indicators": {
                    "rsi_14": {
                        "value": round(current_rsi, 2),
                        "score": round(current_rsi, 1),
                        "name": "相对强弱 (RSI)"
                    },
                    "bias_60": {
                        "value": f"{round(bias_pct, 2)}%",
                        "score": round(bias_score, 1),
                        "name": "均线偏离 (Bias)"
                    },
                    "daily_change": {
                        "value": f"{round(change_pct, 2)}%",
                        "score": round(daily_score, 1),
                        "name": "当日涨跌"
                    },
                    "close": current_price,
                    "ma60": round(current_ma60, 2)
                },
                "description": f"HSI当日涨跌{round(change_pct, 2)}%，RSI(14)为{round(current_rsi, 1)}。",
                "explanation": HKFearGreed._get_explanation(),
                "levels": HKFearGreed._get_levels_payload(),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"❌ 计算港股恐慌贪婪指数失败: {e}")
            return {
                "error": str(e),
                "message": "无法计算港股恐慌贪婪指数",
                "status": "error"
            }

    @staticmethod
    def _get_explanation() -> str:
        weights = HKFearGreed._get_weights()
        return """
港股恐慌贪婪指数说明：
• 指数范围：0-100，数值越高表示市场越贪婪
• 计算因子：RSI({rsi}%)、均线偏离({bias}%)、当日涨跌({dc}%)
• 分值解读：
  - 0-25：极度恐慌
  - 25-45：恐慌
  - 45-55：中性
  - 55-75：贪婪
  - 75-100：极度贪婪
• 说明：此指标为技术指标合成，不构成投资建议
        """.strip().format(
            rsi=int(weights["rsi"] * 100),
            bias=int(weights["bias"] * 100),
            dc=int(weights["daily_change"] * 100),
        )
