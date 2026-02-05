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
            cls._inject_realtime_data(df, symbol, name)
            
            # 计算技术指标
            indicators = cls._calculate_indicators(df)
            
            if not indicators:
                return {
                    "error": "无法计算技术指标",
                    "message": f"无法计算{name}恐慌贪婪指数",
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }
            
            # 计算综合得分
            score = cls._calculate_composite_score(indicators)
            
            if score is None:
                return {
                    "error": "无法计算综合得分",
                    "message": "指标数据不足",
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }
            
            # 等级描述
            level, description = cls._get_level(score)
            
            return {
                "score": round(score, 1),
                "level": level,
                "description": description,
                "indicators": indicators,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "explanation": cls._get_explanation(name),
                "levels": [{"min": t, "label": l, "description": d} for t, l, d in cls.LEVELS],
            }

        except Exception as e:
            logger.error(f"❌ 计算{name}恐慌贪婪指数失败: {e}")
            return {
                "error": str(e),
                "message": f"无法计算{name}恐慌贪婪指数",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            }

    @classmethod
    def _inject_realtime_data(cls, df: pd.DataFrame, symbol: str, name: str) -> None:
        """注入实时数据"""
        try:
            min_df = akshare_call_with_retry(ak.futures_zh_minute_sina, symbol=symbol, period="1")
            if min_df.empty:
                return
                
            latest_price = safe_float(min_df.iloc[-1]["close"])
            latest_time = min_df.iloc[-1]["datetime"]
            
            if latest_price is None:
                return
                
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
                
        except Exception as e:
            logger.warning(f"⚠️ 无法获取{name}实时数据: {e}")

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
            score_rsi = 50 + (rsi - 50) * 1.33 if rsi > 50 else 50 - (50 - rsi) * 1.33
            score_rsi = min(100, max(0, score_rsi))
            
            indicators["rsi"] = {
                "value": round(rsi, 2),
                "score": round(score_rsi, 1),
                "weight": BaseMetalFearGreedIndex.WEIGHTS["rsi"],
                "name": "RSI (14)"
            }

            # 2. 波动率
            returns = close.pct_change()
            current_vol = returns.tail(20).std() * np.sqrt(252)
            avg_vol = returns.tail(60).std() * np.sqrt(252)
            vol_ratio = current_vol / avg_vol if avg_vol and not pd.isna(avg_vol) else 1.0
            score_vol = min(100, max(0, 50 - (vol_ratio - 1.0) * 60))
             
            indicators["volatility"] = {
                "value": round(current_vol * 100, 2) if not pd.isna(current_vol) else 0,
                "ratio": round(vol_ratio, 2),
                "score": round(score_vol, 1),
                "weight": BaseMetalFearGreedIndex.WEIGHTS["volatility"],
                "name": "波动率趋势"
            }
            
            # 3. 价格动量 (MA50 偏离)
            current_price = close.iloc[-1]
            ma50 = close.rolling(window=50).mean().iloc[-1]
            if pd.isna(ma50):
                ma50 = close.mean()
            bias = (current_price - ma50) / ma50 * 100
            score_mom = min(100, max(0, 50 + bias * 4))
            
            indicators["momentum"] = {
                "value": round(bias, 2),
                "score": round(score_mom, 1),
                "weight": BaseMetalFearGreedIndex.WEIGHTS["momentum"],
                "name": "均线偏离 (MA50)"
            }
            
            # 4. 当日涨跌
            daily_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
            score_daily = min(100, max(0, 50 + daily_change * 10))
            
            indicators["daily_change"] = {
                "value": round(daily_change, 2),
                "score": round(score_daily, 1),
                "weight": BaseMetalFearGreedIndex.WEIGHTS["daily_change"],
                "name": "当日涨跌"
            }
            
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
        
        total_score, total_weight = 0.0, 0.0
        for v in indicators.values():
            if "score" in v and "weight" in v:
                total_score += v["score"] * v["weight"]
                total_weight += v["weight"]
        
        return total_score / total_weight if total_weight > 0 else None

    @staticmethod
    def _get_level(score: float) -> tuple:
        for threshold, level, description in BaseMetalFearGreedIndex.LEVELS:
            if score >= threshold:
                return level, description
        return "未知", "无法判断情绪等级"

    @staticmethod
    def _get_explanation(name: str) -> str:
        w = BaseMetalFearGreedIndex.WEIGHTS
        return f"""{name}恐慌贪婪指数 (技术面分析)
• RSI ({int(w['rsi']*100)}%): 相对强弱，衡量超买超卖
• 均线偏离 ({int(w['momentum']*100)}%): 价格与MA50乖离率
• 波动率 ({int(w['volatility']*100)}%): 近期vs历史波动对比
• 当日涨跌 ({int(w['daily_change']*100)}%): 实时价格变化
• 分值: 0-25极度恐慌, 75-100极度贪婪"""


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
