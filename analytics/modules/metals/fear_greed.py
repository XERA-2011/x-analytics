"""
黄金恐慌贪婪指数 (Custom)
基于技术指标计算: RSI, 波动率, 动量, 均线偏离
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
    """金属恐慌贪婪指数基类"""

    DEFAULT_WEIGHTS = {
        "rsi": 0.30,
        "volatility": 0.20,
        "momentum": 0.30,
        "daily_change": 0.20,
    }

    DEFAULT_LEVELS = [
        (75, "极度贪婪", "市场情绪极度乐观"),
        (55, "贪婪", "市场情绪偏向乐观"),
        (45, "中性", "多空平衡，方向不明"),
        (25, "恐慌", "市场情绪偏悲观"),
        (0, "极度恐慌", "市场情绪极度悲观"),
    ]

    @staticmethod
    def _get_weights() -> Dict[str, float]:
        return settings.FEAR_GREED_CONFIG.get("metals", {}).get("weights", BaseMetalFearGreedIndex.DEFAULT_WEIGHTS)

    @staticmethod
    def _get_levels() -> list:
        return settings.FEAR_GREED_CONFIG.get("metals", {}).get("levels", BaseMetalFearGreedIndex.DEFAULT_LEVELS)

    @staticmethod
    def _get_levels_payload() -> list:
        return [{"min": t, "label": l, "description": d} for t, l, d in BaseMetalFearGreedIndex._get_levels()]

    @classmethod
    def calculate(cls, symbol: str, cache_key: str, name: str) -> Dict[str, Any]:
        """
        计算恐慌贪婪指数
        """
        try:
            # 获取历史数据 (用于计算指标)
            # 使用 ak.futures_zh_daily_sina 获取沪金/沪银主力合约日线数据
            df = akshare_call_with_retry(ak.futures_zh_daily_sina, symbol=symbol)
            
            if df.empty or len(df) < 60:
                raise ValueError(f"无法获取足够的{name}历史数据")
            
            # 数据清洗
            # futures_zh_daily 返回列: date, open, high, low, close, volume, ...
            df.columns = [c.lower() for c in df.columns]
            
            # 确保按日期升序
            if "date" in df.columns:
                df = df.sort_values(by="date")
            elif "time" in df.columns: # Sometimes it returns 'time'
                 df = df.rename(columns={"time": "date"})
                 df = df.sort_values(by="date")

            # --- 注入实时数据 (Fix Stale Data) ---
            try:
                # 获取1分钟级数据，取最新一根K线的收盘价作为当前价格
                # 这能确保即使在盘中，指标也能反映最新跌势
                min_df = akshare_call_with_retry(ak.futures_zh_minute_sina, symbol=symbol, period="1")
                if not min_df.empty:
                    latest_price = safe_float(min_df.iloc[-1]["close"])
                    # column is 'datetime', not 'day' for minute data
                    latest_time = min_df.iloc[-1]["datetime"] 
                    
                    if latest_price is not None:
                        # 检查 Daily 数据的最后一行日期
                        last_date_str = str(df.iloc[-1]["date"])[:10] # YYYY-MM-DD
                        current_date_str = str(latest_time)[:10]
                        
                        logger.info(f"[{name}] DailyLast: {last_date_str}, Realtime: {current_date_str}, Price: {latest_price}")
                        print(f"✅ [Metals] {name} 实时注入成功: {current_date_str} Price={latest_price}")

                        if last_date_str == current_date_str:
                            # 如果日期相同，更新最后一行收盘价 (Overwrite)
                            df.iloc[-1, df.columns.get_loc("close")] = latest_price
                        else:
                            # 如果日期不同 (Daily还没更新)，追加一行 (Append)
                            new_row = df.iloc[-1].copy()
                            new_row["date"] = current_date_str
                            new_row["close"] = latest_price
                            # 其他字段(open/high/low)暂时复用上一行或置为NaN，
                            # 但计算RSI/Change只需要Close，所以问题不大
                            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                else:
                     print(f"❌ [Metals] {name} 实时数据为空!")

            except Exception as e_rt:
                logger.warning(f"⚠️ 无法获取{name}实时数据，将使用昨日收盘价: {e_rt}")
                print(f"❌ [Metals] {name} 实时获取异常: {e_rt}")
            # -----------------------------------
            
            # 计算各项指标
            indicators = cls._calculate_indicators(df)
            
            # 如果指标计算失败，返回错误
            if not indicators:
                return {
                    "error": "无法计算技术指标",
                    "message": f"无法计算{name}恐慌贪婪指数",
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }
            
            # 计算综合得分
            score = cls._calculate_composite_score(indicators)
            
            # 如果无法计算综合得分，返回错误
            if score is None:
                return {
                    "error": "无法计算综合得分",
                    "message": "指标数据不足",
                    "indicators": indicators,
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }
            
            # 等级描述
            level, description = cls._get_level_description(score)
            
            return {
                "score": round(score, 1),
                "level": level,
                "description": description,
                "indicators": indicators,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "explanation": cls._get_explanation(name),
                "levels": cls._get_levels_payload(),
            }

        except Exception as e:
            logger.error(f"❌ 计算{name}恐慌贪婪指数失败: {e}")
            return {
                "error": str(e),
                "message": f"无法计算{name}恐慌贪婪指数",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def _calculate_indicators(df: pd.DataFrame) -> Dict[str, Any]:
        """计算技术指标"""
        indicators = {}
        try:
            close_prices = df["close"]
            
            # 1. RSI (14) - 权重 30%
            rsi = BaseMetalFearGreedIndex._calculate_rsi(close_prices, 14)
            if rsi is None:
                return {}
            if rsi > 50:
                 score_rsi = 50 + (rsi - 50) * 1.33 
            else:
                 score_rsi = 50 - (50 - rsi) * 1.33
            score_rsi = min(100, max(0, score_rsi))
            
            indicators["rsi"] = {
                "value": round(rsi, 2),
                "score": round(score_rsi, 1),
                "weight": BaseMetalFearGreedIndex._get_weights()["rsi"],
                "name": "RSI (14)"
            }

            # 2. 波动率 (Volatility) - 权重 20%
            returns = close_prices.pct_change()
            current_vol = returns.tail(20).std() * np.sqrt(252) # 当前20日年化波动
            avg_vol = returns.tail(60).std() * np.sqrt(252)     # 过去60日年化波动
            
            if pd.isna(current_vol) or pd.isna(avg_vol) or avg_vol == 0:
                vol_ratio = 1.0
            else:
                vol_ratio = current_vol / avg_vol
            
            # 高波动 -> 恐慌
            score_vol = 50 - (vol_ratio - 1.0) * 60 
            score_vol = min(100, max(0, score_vol))
             
            indicators["volatility"] = {
                "value": round(current_vol * 100, 2), # Show as %
                "ratio": round(vol_ratio, 2),
                "score": round(score_vol, 1),
                "weight": BaseMetalFearGreedIndex._get_weights()["volatility"],
                "name": "波动率趋势"
            }
            
            # 3. 价格动量 (Momentum) vs 均线 - 权重 30%
            current_price = close_prices.iloc[-1]
            ma50 = close_prices.rolling(window=50).mean().iloc[-1]
            if pd.isna(ma50):
                ma50 = close_prices.mean()
                
            bias = (current_price - ma50) / ma50 * 100
            score_mom = 50 + bias * 4
            score_mom = min(100, max(0, score_mom))
            
            indicators["momentum"] = {
                "value": round(bias, 2), # Bias %
                "score": round(score_mom, 1),
                "weight": BaseMetalFearGreedIndex._get_weights()["momentum"],
                "name": "均线偏离 (MA50)"
            }
            
            # 4. 当日涨跌 (Daily Change) - 权重 20%
            # 替代周趋势，增强日内敏感度
            daily_change = (close_prices.iloc[-1] - close_prices.iloc[-2]) / close_prices.iloc[-2] * 100
            score_daily = 50 + daily_change * 10 
            score_daily = min(100, max(0, score_daily))
            
            indicators["daily_change"] = {
                "value": round(daily_change, 2),
                "score": round(score_daily, 1),
                "weight": BaseMetalFearGreedIndex._get_weights()["daily_change"],
                "name": "当日涨跌"
            }
            
        except Exception as e:
            logger.warning(f"指标计算部分失败: {e}")
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
        """计算综合得分，如果没有有效指标返回 None"""
        if not indicators:
            return None
        
        total_score, total_weight = 0.0, 0.0
        valid_count = 0
        
        for k, v in indicators.items():
            if "score" in v and "weight" in v:
                total_score += v["score"] * v["weight"]
                total_weight += v["weight"]
                valid_count += 1
        
        if total_weight == 0 or valid_count == 0:
            return None
        
        return total_score / total_weight

    @staticmethod
    def _get_level_description(score: float) -> tuple:
        for threshold, level, description in BaseMetalFearGreedIndex._get_levels():
            if score >= threshold:
                return level, description
        return "未知", "无法判断情绪等级"

    @staticmethod
    def _get_explanation(name: str) -> str:
        weights = BaseMetalFearGreedIndex._get_weights()
        return f"""
{name}恐慌贪婪指数模型：
• 核心逻辑：基于价格行为(Price Action)量化市场情绪
• 组成因子：
  1. RSI ({int(weights["rsi"] * 100)}%)：相对强弱指标，衡量超买超卖
  2. 均线偏离 ({int(weights["momentum"] * 100)}%)：当前价格与50日均线乖离率
  3. 波动率 ({int(weights["volatility"] * 100)}%)：近期波动率与历史波动率对比
  4. 当日涨跌 ({int(weights["daily_change"] * 100)}%)：当日价格变化
• 分值解读：
  - 0-25 (极度恐慌)：市场情绪极度悲观
  - 75-100 (极度贪婪)：市场情绪极度乐观
• 说明：此指标为技术指标合成，不构成投资建议
""".strip()


class GoldFearGreedIndex(BaseMetalFearGreedIndex):
    """黄金市场恐慌贪婪指数计算"""
    GOLD_SYMBOL = "au0"

    @staticmethod
    @cached("metals:fear_greed_v2", ttl=settings.CACHE_TTL["metals"], stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO)
    def calculate() -> Dict[str, Any]:
        return BaseMetalFearGreedIndex.calculate(GoldFearGreedIndex.GOLD_SYMBOL, "metals:fear_greed_v2", "黄金")


class SilverFearGreedIndex(BaseMetalFearGreedIndex):
    """白银市场恐慌贪婪指数计算"""
    SILVER_SYMBOL = "ag0" # 沪银主力

    @staticmethod
    @cached("metals:silver_fear_greed_v2", ttl=settings.CACHE_TTL["metals"], stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO)
    def calculate() -> Dict[str, Any]:
        return BaseMetalFearGreedIndex.calculate(SilverFearGreedIndex.SILVER_SYMBOL, "metals:silver_fear_greed_v2", "白银")
