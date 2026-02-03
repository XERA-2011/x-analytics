"""
美国市场恐慌贪婪指数
获取CNN Fear & Greed Index和自定义计算
"""

import requests
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger


class USFearGreedIndex:
    """美国市场恐慌贪婪指数"""

    DEFAULT_WEIGHTS = {
        "vix": 0.30,
        "sp500_momentum": 0.25,
        "daily_change": 0.25,
        "market_breadth": 0.20,
    }

    DEFAULT_LEVELS = [
        (80, "极度贪婪", "市场情绪极度乐观"),
        (65, "贪婪", "市场情绪乐观"),
        (55, "轻微贪婪", "市场情绪略显乐观"),
        (45, "中性", "市场情绪平衡"),
        (35, "轻微恐慌", "市场情绪略显悲观"),
        (20, "恐慌", "市场情绪悲观"),
        (0, "极度恐慌", "市场情绪极度悲观"),
    ]

    @staticmethod
    def _get_weights() -> Dict[str, float]:
        return settings.FEAR_GREED_CONFIG.get("us", {}).get("weights", USFearGreedIndex.DEFAULT_WEIGHTS)

    @staticmethod
    def _get_levels() -> list:
        return settings.FEAR_GREED_CONFIG.get("us", {}).get("levels", USFearGreedIndex.DEFAULT_LEVELS)

    @staticmethod
    def _get_levels_payload() -> list:
        return [{"min": t, "label": l, "description": d} for t, l, d in USFearGreedIndex._get_levels()]

    @staticmethod
    def _sort_by_date(df: pd.DataFrame) -> pd.DataFrame:
        for date_col in ["date", "trade_date", "datetime"]:
            if date_col in df.columns:
                return df.sort_values(date_col)
        return df

    @staticmethod
    @cached("market_us:fear_greed", ttl=settings.CACHE_TTL["fear_greed"], stale_ttl=settings.CACHE_TTL["fear_greed"] * settings.STALE_TTL_RATIO)
    def get_cnn_fear_greed() -> Dict[str, Any]:
        """
        获取恐慌贪婪指数
        
        注意：由于 strict "Only AkShare" 政策，原直接爬取 CNN 官网的逻辑已被移除。
        现在使用 calculate_custom_index() 计算的自定义指数作为该接口的返回值。
        保持接口签名兼容前端调用。
        """
        try:
            # 使用自定义计算逻辑 (基于 AkShare 的 VIX 和 SP500)
            custom_data = USFearGreedIndex.calculate_custom_index()
            
            if "error" in custom_data:
                return {
                    "error": custom_data["error"], 
                    "message": "无法获取恐慌贪婪指数 (AkShare源)",
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
                }

            # 映射字段以兼容前端
            score = custom_data.get("score", 50)
            level = custom_data.get("level", "中性")
            
            # 由于是实时计算，暂时无法提供准确的 change_1d (除非有历史缓存)
            # 兼容前端：如果为 None，前端应隐藏变动显示，而不是显示 0
            return {
                "current_value": score,
                "current_level": level,
                "change_1d": None, 
                "change_7d": None,
                "date": custom_data.get("update_time"),
                "history": [], 
                "update_time": custom_data.get("update_time"),
                "explanation": USFearGreedIndex._get_custom_explanation(), # 使用自定义说明
                "source": "AkShare (Calculated, CNN proxy)", # 明确标注来源
                "levels": USFearGreedIndex._get_levels_payload(),
            }

        except Exception as e:
            logger.error(f" 获取恐慌贪婪指数失败: {e}")
            return USFearGreedIndex._get_fallback_data(str(e))

    @staticmethod
    def _get_fallback_data(error_msg: str) -> Dict[str, Any]:
        """获取失败时返回错误信息，不返回假数据"""
        return {
            "error": error_msg,
            "message": "无法获取恐慌贪婪指数",
            "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
        }
    @staticmethod
    @cached(
        "market_us:custom_fear_greed",
        ttl=settings.CACHE_TTL.get("fear_greed", 3600),
        stale_ttl=settings.CACHE_TTL.get("fear_greed", 3600) * settings.STALE_TTL_RATIO,
    )
    def calculate_custom_index() -> Dict[str, Any]:
        """
        计算自定义美国市场恐慌贪婪指数
        基于VIX、标普500等指标
        """
        try:
            vix_data = USFearGreedIndex._get_vix_data()
            sp500_data = USFearGreedIndex._get_sp500_data()

            indicators = {
                "vix": vix_data,
                "sp500_momentum": sp500_data,
                "daily_change": USFearGreedIndex._get_daily_change(),
                "market_breadth": USFearGreedIndex._get_market_breadth(),
            }

            composite_score = USFearGreedIndex._calculate_composite_score(indicators)
            
            # 如果无法计算综合得分（所有指标都失败），返回错误
            if composite_score is None:
                return {
                    "error": "无法获取足够的指标数据",
                    "message": "所有指标获取失败",
                    "indicators": indicators,
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }
            
            level, description = USFearGreedIndex._get_level_description(
                composite_score
            )

            return {
                "score": round(composite_score, 1),
                "level": level,
                "description": description,
                "indicators": indicators,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "explanation": USFearGreedIndex._get_custom_explanation(),
                "levels": USFearGreedIndex._get_levels_payload(),
            }

        except Exception as e:
            logger.error(f"❌ 计算自定义恐慌贪婪指数失败: {e}")
            return {
                "error": str(e),
                "message": "无法计算自定义恐慌贪婪指数",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def _get_vix_data() -> Dict[str, Any]:
        """
        获取 VIX 数据
        策略: 优先尝试 API (.VIX), 失败则计算标普500历史波动率作为替代
        """
        try:
            # 1. 优先尝试直接获取 VIX 数据
            try:
                df = akshare_call_with_retry(ak.stock_us_daily, symbol=".VIX")
                if not df.empty:
                    df = USFearGreedIndex._sort_by_date(df)
                    latest_vix = safe_float(df.iloc[-1]["close"])
                    if latest_vix is not None:
                        return USFearGreedIndex._format_vix_score(latest_vix)
            except (IndexError, KeyError, ValueError) as e:
                # 常见错误：Sina 接口返回格式异常导致 akshare 全局 split 失败 (IndexError)
                logger.info(f"VIX API 暫不可用 (.VIX), 将切换至计算模式: {e}")
            except Exception as e:
                logger.warning(f"⚠️ VIX API 获取失败 (将使用计算回退): {e}")

            # 2. 回退模式: 计算标普500的历史波动率 (Realized Volatility)
            # 逻辑: VIX ≈ 预期波动率，历史波动率是其良好近似
            logger.info("🔄 使用标普500波动率计算 VIX 替代值...")
            
            # 获取标普500数据 (多取一些数据以计算滚动窗口)
            df_sp500 = akshare_call_with_retry(ak.stock_us_daily, symbol=".INX")
            
            if df_sp500.empty or len(df_sp500) < 30:
                return {"error": "数据不足无法计算VIX", "weight": 0.3}
            df_sp500 = USFearGreedIndex._sort_by_date(df_sp500)

            # 计算对数收益率
            df_sp500["close"] = pd.to_numeric(df_sp500["close"], errors="coerce")
            df_sp500["log_ret"] = np.log(df_sp500["close"] / df_sp500["close"].shift(1))
            
            # 计算20日滚动波动率 (年化)
            # window=20 (约一个月交易日), x 100 (百分比), x sqrt(252) (年化)
            rolling_vol = df_sp500["log_ret"].rolling(window=20).std() * np.sqrt(252) * 100
            
            latest_vol = safe_float(rolling_vol.iloc[-1])
            
            if latest_vol is None:
                return {"error": "波动率计算失败", "weight": 0.3}

            return USFearGreedIndex._format_vix_score(latest_vol, is_estimated=True)

        except Exception as e:
            logger.warning(f"⚠️ 获取/计算 VIX 数据失败: {e}")
            return {"error": str(e), "weight": 0.25}

    @staticmethod
    def _get_daily_change() -> Dict[str, Any]:
        """获取标普500单日涨跌幅 (Sentiment Sensitivity)"""
        try:
            df = akshare_call_with_retry(ak.stock_us_daily, symbol=".INX")
            if df.empty or len(df) < 2:
                return {"error": "数据不足", "weight": USFearGreedIndex._get_weights()["daily_change"]}
            df = USFearGreedIndex._sort_by_date(df)
            
            # 计算单日涨跌
            # new akshare returns 'close'
            current = df["close"].iloc[-1]
            prev = df["close"].iloc[-2]
            
            change_pct = (current - prev) / prev * 100
            
            # Map spread: -2% (Fear) to +2% (Greed)
            # 0% = 50
            # 1% = 60 (Sensitivity 10)
            score = 50 + change_pct * 10
            score = min(100, max(0, score))
            
            return {
                "change_pct": round(change_pct, 2),
                "score": round(score, 1),
                "weight": USFearGreedIndex._get_weights()["daily_change"],
            }
        except Exception as e:
            return {"error": str(e), "weight": USFearGreedIndex._get_weights()["daily_change"]}

    @staticmethod
    def _format_vix_score(vix_value: float, is_estimated: bool = False) -> Dict[str, Any]:
        """格式化 VIX 分数"""
        # VIX Score Mapping Formula (Calibrated to approximate CNN model)
        # Baseline: VIX=20 is Neutral (Score 50)
        # Sensitivity: ~2 points per 1 VIX unit
        # VIX 12 (Low) -> 50 + (20-12)*2 = 66 (Greed) -> Matches CNN ~62
        # VIX 30 (High) -> 50 + (20-30)*2.5 = 25 (Fear)
        
        diff = 20 - vix_value
        if diff >= 0:
            # VIX < 20: Greed side (Lower VIX = Higher Score)
            vix_score = 50 + diff * 2.0
        else:
            # VIX > 20: Fear side (Higher VIX = Lower Score)
            # Higher sensitivity for high volatility
            vix_score = 50 + diff * 2.5
            
        vix_score = min(100, max(0, vix_score))
        
        return {
            "value": round(vix_value, 2),
            "score": round(vix_score, 1),
            "weight": USFearGreedIndex._get_weights()["vix"],
            "is_estimated": is_estimated,
            "note": "基于标普500波动率估算" if is_estimated else "API直接获取"
        }


    @staticmethod
    def _get_sp500_data() -> Dict[str, Any]:
        """获取标普500动量数据"""
        try:
            # 使用 AkShare 获取标普500指数数据 (代号 .INX)
            df = akshare_call_with_retry(ak.stock_us_daily, symbol=".INX")
            if df.empty or len(df) < 20:
                return {"error": "数据不足", "weight": USFearGreedIndex._get_weights()["sp500_momentum"]}
            df = USFearGreedIndex._sort_by_date(df)
            
            # 计算20日动量 (新接口返回英文列名: close)
            recent = df.tail(20)
            momentum_pct = (
                (recent["close"].iloc[-1] - recent["close"].iloc[0])
                / recent["close"].iloc[0]
                * 100
            )
            
            # 动量转换为分数 (涨5%=75, 涨10%=100, 跌5%=25)
            score = min(100, max(0, 50 + momentum_pct * 5))
            
            return {
                "momentum_pct": round(momentum_pct, 2),
                "score": round(score, 1),
                "weight": USFearGreedIndex._get_weights()["sp500_momentum"],
            }
        except Exception as e:
            logger.warning(f"⚠️ 获取标普500数据失败: {e}")
            return {"error": str(e), "weight": USFearGreedIndex._get_weights()["sp500_momentum"]}

    @staticmethod
    def _get_market_breadth() -> Dict[str, Any]:
        """
        获取市场广度数据
        注: 美国市场涨跌家数难以直接获取，使用道琼斯/纳斯达克相对表现代替
        """
        try:
            # 获取道琼斯(.DJI)和纳斯达克(.IXIC)
            dji = akshare_call_with_retry(ak.stock_us_daily, symbol=".DJI")
            ndx = akshare_call_with_retry(ak.stock_us_daily, symbol=".IXIC") # 纳斯达克综合
            
            if dji.empty or ndx.empty:
                return {"error": "数据不足", "weight": USFearGreedIndex._get_weights()["market_breadth"]}
            dji = USFearGreedIndex._sort_by_date(dji)
            ndx = USFearGreedIndex._sort_by_date(ndx)
            
            # 比较近5日表现 (新接口返回英文列名: close)
            dji_change = (dji["close"].iloc[-1] - dji["close"].iloc[-5]) / dji["close"].iloc[-5] * 100
            ndx_change = (ndx["close"].iloc[-1] - ndx["close"].iloc[-5]) / ndx["close"].iloc[-5] * 100
            
            # 如果大盘股(道琼斯)和成长股(纳斯达克)同涨=贪婪, 同跌=恐慌
            avg_change = (dji_change + ndx_change) / 2
            score = min(100, max(0, 50 + avg_change * 5))
            
            return {
                "dji_5d_change": round(dji_change, 2),
                "ndx_5d_change": round(ndx_change, 2),
                "score": round(score, 1),
                "weight": USFearGreedIndex._get_weights()["market_breadth"],
            }
        except Exception as e:
            logger.warning(f"⚠️ 获取市场广度数据失败: {e}")
            return {"error": str(e), "weight": USFearGreedIndex._get_weights()["market_breadth"]}

    @staticmethod
    def _calculate_composite_score(indicators: Dict[str, Any]) -> Optional[float]:
        """计算综合得分，跳过有错误的指标"""
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
        
        # 如果没有有效指标，返回 None 而非假数据
        if total_weight == 0 or valid_count == 0:
            return None
        
        return total_score / total_weight

    @staticmethod
    def _get_level_description(score: float) -> tuple:
        for threshold, level, description in USFearGreedIndex._get_levels():
            if score >= threshold:
                return level, description
        return "未知", "无法判断情绪等级"

    @staticmethod
    def _get_cnn_explanation() -> str:
        return """
CNN恐慌贪婪指数说明：
• 指数范围：0-100，数值越高表示市场越贪婪
• 数据来源：CNN Business官方发布
• 更新频率：实时/每日
        """.strip()

    @staticmethod
    def _get_custom_explanation() -> str:
        weights = USFearGreedIndex._get_weights()
        return """
自定义美国市场恐慌贪婪指数说明：
• 计算因子：VIX({vix}%)、标普500动量({mom}%)、当日涨跌({dc}%)、市场分化({breadth}%)
• 说明：该指数为自定义估算，用于替代CNN官方指数，不代表CNN观点
        """.strip().format(
            vix=int(weights["vix"] * 100),
            mom=int(weights["sp500_momentum"] * 100),
            dc=int(weights["daily_change"] * 100),
            breadth=int(weights["market_breadth"] * 100),
        )
