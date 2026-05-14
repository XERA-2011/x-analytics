
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any
from analytics.core.cache import cached
from analytics.core.config import settings
from analytics.core.fear_greed import (
    build_factor,
    calculate_composite_score,
    build_fear_greed_meta,
    build_fear_greed_response,
    build_fear_greed_error,
    build_fear_greed_explanation,
    score_percent_change,
    score_rsi,
)
from analytics.core.logger import logger
from analytics.core.utils import get_beijing_time, akshare_call_with_retry, safe_float

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    return 100 - (100 / (1 + rs))

class HKFearGreed:
    META = build_fear_greed_meta(
        market="HK",
        asset="恒生指数",
        methodology="technical_composite",
        cadence="daily",
    )

    DEFAULT_WEIGHTS = {
        "rsi": 0.35,
        "momentum": 0.35,
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
        raw = settings.FEAR_GREED_CONFIG.get("hk", {}).get("weights", HKFearGreed.DEFAULT_WEIGHTS)
        return {
            "rsi": raw.get("rsi", HKFearGreed.DEFAULT_WEIGHTS["rsi"]),
            "momentum": raw.get("momentum", raw.get("bias", HKFearGreed.DEFAULT_WEIGHTS["momentum"])),
            "daily_change": raw.get("daily_change", HKFearGreed.DEFAULT_WEIGHTS["daily_change"]),
        }

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
    def _apply_realtime_hsi_snapshot(df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Patch the latest HSI close with the spot index snapshot when available.

        Sina's daily HSI endpoint often lags during the trading session. The
        spot endpoint has the live level and previous close, so use it as the
        last observation while keeping the historical daily series for RSI/MA.
        """
        snapshot: Dict[str, Any] = {"source": "daily"}

        try:
            spot_df = akshare_call_with_retry(
                ak.stock_hk_index_spot_sina,
                max_retries=3,
            )
            if spot_df.empty or "代码" not in spot_df.columns:
                return df, snapshot

            hsi_rows = spot_df[spot_df["代码"] == "HSI"]
            if hsi_rows.empty:
                return df, snapshot

            row = hsi_rows.iloc[0]
            latest = safe_float(row.get("最新价"), None)
            prev_close = safe_float(row.get("昨收"), None)
            change_pct = safe_float(row.get("涨跌幅"), None)
            if latest is None or latest <= 0:
                return df, snapshot

            today = get_beijing_time().date()
            patched = df.copy()
            date_col = next((col for col in ["date", "trade_date", "datetime"] if col in patched.columns), None)

            if date_col:
                parsed_dates = pd.to_datetime(patched[date_col], errors="coerce").dt.date
                if parsed_dates.iloc[-1] == today:
                    patched.loc[patched.index[-1], "close"] = latest
                else:
                    new_row = patched.iloc[-1].copy()
                    new_row[date_col] = today
                    new_row["open"] = safe_float(row.get("今开"), latest) or latest
                    new_row["high"] = safe_float(row.get("最高"), latest) or latest
                    new_row["low"] = safe_float(row.get("最低"), latest) or latest
                    new_row["close"] = latest
                    if "volume" in patched.columns:
                        new_row["volume"] = 0
                    patched = pd.concat([patched, pd.DataFrame([new_row])], ignore_index=True)
            else:
                patched.loc[patched.index[-1], "close"] = latest

            snapshot.update(
                {
                    "source": "spot",
                    "price": latest,
                    "prev_close": prev_close,
                    "change_pct": change_pct,
                }
            )
            return patched, snapshot
        except Exception as e:
            logger.warning(f"港股实时指数快照获取失败，回退日线数据: {e}")
            return df, snapshot

    @staticmethod
    @cached(
        "market_hk:fear_greed_v2",
        ttl=settings.CACHE_TTL["fear_greed_realtime"],
        stale_ttl=settings.CACHE_TTL["fear_greed_stale"],
    )
    def get_data() -> Dict[str, Any]:
        try:
            update_time = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            # 1. Fetch HSI Daily Data (for RSI and Bias)
            df = akshare_call_with_retry(ak.stock_hk_index_daily_sina, symbol="HSI")
            
            if df.empty or len(df) < 60:
                raise ValueError("Insufficient historical data for HSI")

            # Ensure numeric
            df['close'] = pd.to_numeric(df['close'])
            df = HKFearGreed._sort_by_date(df)
            df, realtime_snapshot = HKFearGreed._apply_realtime_hsi_snapshot(df)
            
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
            bias_score = score_percent_change(bias_pct, sensitivity=4)

            # --- Indicator 3: Daily Change (Market Sentiment) ---
            # 权重 30%: 让当日大跌能显著拉低分数
            prev_close = df['close'].iloc[-2]
            if realtime_snapshot.get("prev_close"):
                prev_close = realtime_snapshot["prev_close"]

            if realtime_snapshot.get("change_pct") is not None:
                change_pct = realtime_snapshot["change_pct"]
            else:
                change_pct = ((current_price - prev_close) / prev_close) * 100
            
            # Map Change% to 0-100
            # 0% = 50 (Neutral)
            # +1% = 60, -1% = 40 (Sensitivity: 10 points per 1%)
            # Max/Min clumping handled later
            daily_score = score_percent_change(change_pct, sensitivity=10)

            # --- Final Score Calculation ---
            # Weights: RSI (35%), Bias (35%), Daily Change (30%)
            weights = HKFearGreed._get_weights()
            indicators = {
                "rsi": build_factor(
                    value=round(current_rsi, 2),
                    score=score_rsi(current_rsi),
                    weight=weights["rsi"],
                    label="RSI (14)",
                ),
                "momentum": build_factor(
                    value=round(bias_pct, 2),
                    score=bias_score,
                    weight=weights["momentum"],
                    label="均线偏离 (Bias60)",
                ),
                "daily_change": build_factor(
                    value=round(change_pct, 2),
                    score=daily_score,
                    weight=weights["daily_change"],
                    label="当日涨跌",
                ),
                "close": current_price,
                "ma60": round(current_ma60, 2)
            }

            final_score = calculate_composite_score(indicators)
            if final_score is None:
                raise ValueError("无法计算港股恐慌贪婪综合得分")

            level_cn = "未知"
            for threshold, label, _desc in HKFearGreed._get_levels():
                if final_score >= threshold:
                    level_cn = label
                    break

            return build_fear_greed_response(
                score=final_score,
                level=level_cn,
                description=f"HSI当日涨跌{round(change_pct, 2)}%，RSI(14)为{round(current_rsi, 1)}。",
                indicators=indicators,
                update_time=update_time,
                explanation=HKFearGreed._get_explanation(),
                levels=HKFearGreed._get_levels_payload(),
                meta=HKFearGreed.META,
                extra={"status": "success", "data_source": realtime_snapshot["source"]},
            )

        except Exception as e:
            logger.error(f"❌ 计算港股恐慌贪婪指数失败: {e}")
            return build_fear_greed_error(
                error=str(e),
                message="无法计算港股恐慌贪婪指数",
                update_time=get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                meta=HKFearGreed.META,
                extra={"status": "error"},
            )

    @staticmethod
    def _get_explanation() -> str:
        weights = HKFearGreed._get_weights()
        return build_fear_greed_explanation(
            title="香港市场情绪指数",
            factors=[
                ("RSI", weights["rsi"], "衡量超买超卖状态"),
                ("动量代理", weights["momentum"], "反映价格相对均线的偏离"),
                ("当日涨跌", weights["daily_change"], "反映短线价格变化"),
            ],
            levels=HKFearGreed._get_levels(),
            methodology_note="该指数基于港股核心技术与行情因子合成，更适合同市场内部纵向观察，不建议直接跨市场比较。",
        )
