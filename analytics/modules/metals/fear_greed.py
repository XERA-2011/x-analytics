"""
黄金/白银恐慌贪婪指数 (纯技术面分析)

技术指标:
- RSI (30%): 相对强弱指标
- 波动率 (20%): 当前波动率 vs 历史波动率
- 动量 (30%): 价格与 MA50 偏离度
- 当日涨跌 (20%): 实时价格变化
"""

import akshare as ak
import pandas as pd
import numpy as np

from typing import Dict, Any, Optional
from ...core.cache import cached
from ...core.config import settings
from ...core.fear_greed import (
    build_factor,
    calculate_composite_score,
    build_fear_greed_meta,
    build_fear_greed_response,
    build_fear_greed_error,
    build_fear_greed_explanation,
    score_inverse_ratio,
    score_percent_change,
    score_rsi,
)
from ...core.utils import get_beijing_time, akshare_call_with_retry, safe_float
from ...core.logger import logger


class BaseMetalFearGreedIndex:
    """金属恐慌贪婪指数基类 (纯技术面)"""

    # 技术指标权重
    WEIGHTS = {
        "rsi": 0.30,
        "volatility": 0.20,
        "momentum": 0.30,
        "daily_change": 0.20,
    }

    # 情绪等级
    LEVELS = [
        (75, "极度贪婪", "市场情绪极度乐观"),
        (55, "贪婪", "市场情绪偏向乐观"),
        (45, "中性", "多空平衡，方向不明"),
        (25, "恐慌", "市场情绪偏悲观"),
        (0, "极度恐慌", "市场情绪极度悲观"),
    ]

    @classmethod
    def calculate(cls, symbol: str, name: str) -> Dict[str, Any]:
        """计算恐慌贪婪指数"""
        try:
            update_time = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            meta = build_fear_greed_meta(
                market="METALS",
                asset=name,
                methodology="technical_composite",
                cadence="daily+intraday",
            )
            # 获取历史日线数据
            df = akshare_call_with_retry(ak.futures_zh_daily_sina, symbol=symbol)
            
            if df.empty or len(df) < 60:
                raise ValueError(f"无法获取足够的{name}历史数据")
            
            # 数据清洗
            df.columns = [c.lower() for c in df.columns]
            if "date" in df.columns:
                df = df.sort_values(by="date")
            elif "time" in df.columns:
                df = df.rename(columns={"time": "date"})
                df = df.sort_values(by="date")

            # 注入实时数据
            df = cls._inject_realtime_data(df, symbol, name)
            
            # 计算技术指标
            indicators = cls._calculate_indicators(df)
            
            if not indicators:
                return build_fear_greed_error(
                    error="无法计算技术指标",
                    message=f"无法计算{name}恐慌贪婪指数",
                    update_time=update_time,
                    meta=meta,
                )
            
            # 计算综合得分
            score = cls._calculate_composite_score(indicators)
            
            if score is None:
                return build_fear_greed_error(
                    error="无法计算综合得分",
                    message="指标数据不足",
                    update_time=update_time,
                    meta=meta,
                )
            
            # 等级描述
            level, description = cls._get_level(score)
            
            return build_fear_greed_response(
                score=score,
                level=level,
                description=description,
                indicators=indicators,
                update_time=update_time,
                explanation=cls._get_explanation(name),
                levels=[{"min": t, "label": l, "description": d} for t, l, d in cls.LEVELS],
                meta=meta,
            )

        except Exception as e:
            logger.error(f"❌ 计算{name}恐慌贪婪指数失败: {e}")
            return build_fear_greed_error(
                error=str(e),
                message=f"无法计算{name}恐慌贪婪指数",
                update_time=get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                meta=build_fear_greed_meta(
                    market="METALS",
                    asset=name,
                    methodology="technical_composite",
                    cadence="daily+intraday",
                ),
            )

    @classmethod
    def _inject_realtime_data(cls, df: pd.DataFrame, symbol: str, name: str) -> pd.DataFrame:
        """注入实时数据"""
        try:
            min_df = akshare_call_with_retry(ak.futures_zh_minute_sina, symbol=symbol, period="1")
            if min_df.empty:
                return df
                
            latest_price = safe_float(min_df.iloc[-1]["close"])
            latest_time = min_df.iloc[-1]["datetime"]
            
            if latest_price is None:
                return df
                
            last_date_str = str(df.iloc[-1]["date"])[:10]
            current_date_str = str(latest_time)[:10]
            
            logger.info(f"[{name}] DailyLast: {last_date_str}, Realtime: {current_date_str}, Price: {latest_price}")

            if last_date_str == current_date_str:
                df.iloc[-1, df.columns.get_loc("close")] = latest_price
            else:
                new_row = df.iloc[-1].copy()
                new_row["date"] = current_date_str
                new_row["close"] = latest_price
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            return df
        except Exception as e:
            logger.warning(f"⚠️ 无法获取{name}实时数据: {e}")
            return df

    @staticmethod
    def _calculate_indicators(df: pd.DataFrame) -> Dict[str, Any]:
        """计算技术指标"""
        indicators = {}
        try:
            close = df["close"]
            
            # 1. RSI (14)
            rsi = BaseMetalFearGreedIndex._calculate_rsi(close, 14)
            if rsi is None:
                return {}
            rsi_score = score_rsi(rsi)
            
            indicators["rsi"] = build_factor(
                value=round(rsi, 2),
                score=rsi_score,
                weight=BaseMetalFearGreedIndex.WEIGHTS["rsi"],
                label="RSI (14)",
            )

            # 2. 波动率
            returns = close.pct_change()
            current_vol = returns.tail(20).std() * np.sqrt(252)
            avg_vol = returns.tail(60).std() * np.sqrt(252)
            vol_ratio = current_vol / avg_vol if avg_vol and not pd.isna(avg_vol) else 1.0
            score_vol = score_inverse_ratio(vol_ratio, sensitivity=60)
             
            indicators["volatility"] = build_factor(
                value=round(current_vol * 100, 2) if not pd.isna(current_vol) else 0,
                score=score_vol,
                weight=BaseMetalFearGreedIndex.WEIGHTS["volatility"],
                label="波动率趋势",
                ratio=round(vol_ratio, 2),
            )
            
            # 3. 价格动量 (MA50 偏离)
            current_price = close.iloc[-1]
            ma50 = close.rolling(window=50).mean().iloc[-1]
            if pd.isna(ma50):
                ma50 = close.mean()
            bias = (current_price - ma50) / ma50 * 100
            score_mom = score_percent_change(bias, sensitivity=4)
            
            indicators["momentum"] = build_factor(
                value=round(bias, 2),
                score=score_mom,
                weight=BaseMetalFearGreedIndex.WEIGHTS["momentum"],
                label="均线偏离 (MA50)",
            )
            
            # 4. 当日涨跌
            daily_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
            score_daily = score_percent_change(daily_change, sensitivity=10)
            
            indicators["daily_change"] = build_factor(
                value=round(daily_change, 2),
                score=score_daily,
                weight=BaseMetalFearGreedIndex.WEIGHTS["daily_change"],
                label="当日涨跌",
            )
            
        except Exception as e:
            logger.warning(f"指标计算失败: {e}")
            return {}
            
        return indicators

    @staticmethod
    def _calculate_rsi(series: pd.Series, period: int = 14) -> Optional[float]:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None

    @staticmethod
    def _calculate_composite_score(indicators: Dict[str, Any]) -> Optional[float]:
        """计算综合得分"""
        if not indicators:
            return None
        return calculate_composite_score(indicators)

    @staticmethod
    def _get_level(score: float) -> tuple:
        for threshold, level, description in BaseMetalFearGreedIndex.LEVELS:
            if score >= threshold:
                return level, description
        return "未知", "无法判断情绪等级"

    @staticmethod
    def _get_explanation(name: str) -> str:
        w = BaseMetalFearGreedIndex.WEIGHTS
        return build_fear_greed_explanation(
            title=f"{name}情绪指数",
            factors=[
                ("RSI", w["rsi"], "衡量超买超卖状态"),
                ("均线偏离", w["momentum"], "反映价格相对 MA50 的偏离"),
                ("波动率", w["volatility"], "反映近期相对历史的波动变化"),
                ("当日涨跌", w["daily_change"], "反映短线价格变化"),
            ],
            levels=BaseMetalFearGreedIndex.LEVELS,
            methodology_note=f"该指数基于{name}技术与行情因子合成，更适合同品种内部纵向观察，不建议与股票市场直接比较。",
        )


class GoldFearGreedIndex(BaseMetalFearGreedIndex):
    """黄金恐慌贪婪指数"""
    
    @staticmethod
    @cached("metals:fear_greed_v3", ttl=settings.CACHE_TTL["metals"], stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO)
    def calculate() -> Dict[str, Any]:
        return BaseMetalFearGreedIndex.calculate("au0", "黄金")


class SilverFearGreedIndex(BaseMetalFearGreedIndex):
    """白银恐慌贪婪指数"""
    
    @staticmethod
    @cached("metals:silver_fear_greed_v3", ttl=settings.CACHE_TTL["metals"], stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO)
    def calculate() -> Dict[str, Any]:
        return BaseMetalFearGreedIndex.calculate("ag0", "白银")
