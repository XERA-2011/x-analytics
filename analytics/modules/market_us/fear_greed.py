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

    @staticmethod
    @cached("market_us:fear_greed", ttl=settings.CACHE_TTL["fear_greed"], stale_ttl=settings.CACHE_TTL["fear_greed"] * settings.STALE_TTL_RATIO)
    def get_cnn_fear_greed() -> Dict[str, Any]:
        """
        获取CNN恐慌贪婪指数
        来源: https://production.dataviz.cnn.io/index/fearandgreed/graphdata

        Returns:
            CNN恐慌贪婪指数数据
        """
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            # 增加超时设置
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()

                # CNN 数据结构通常包含 fear_and_greed 字段
                if "fear_and_greed" in data:
                    fg_data = data["fear_and_greed"]

                    score = float(fg_data.get("score", 0))
                    rating = fg_data.get("rating", "neutral")
                    timestamp = fg_data.get("timestamp")

                    # 转换 rating 为中文
                    rating_map = {
                        "extreme fear": "极度恐慌",
                        "fear": "恐慌",
                        "neutral": "中性",
                        "greed": "贪婪",
                        "extreme greed": "极度贪婪",
                    }
                    rating_cn = rating_map.get(rating.lower(), "中性")

                    # 格式化日期
                    date_str = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
                    if timestamp:
                        try:
                            # 尝试解析 timestamp (ISO format)
                            dt = datetime.fromisoformat(
                                timestamp.replace("Z", "+00:00")
                            )
                            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            pass

                    # 构建历史数据结构 (兼容前端)
                    history: List[Dict[str, Any]] = []
                    # CNN API返回的数据中包含历史趋势字段: previous_close, 1_week_ago, etc
                    # 我们可以伪造一个简单的history列表，或者尝试解析 graph_data (如果API返回)

                    return {
                        "current_value": round(score, 1),
                        "current_level": rating_cn,
                        "change_1d": round(
                            score - float(fg_data.get("previous_close", score)), 1
                        ),
                        "change_7d": round(
                            score - float(fg_data.get("previous_1_week", score)), 1
                        ),
                        "date": date_str,
                        "history": history,  # 暂时留空
                        "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                        "explanation": USFearGreedIndex._get_cnn_explanation(),
                    }

            logger.warning(f"CNN API返回状态码: {response.status_code}")
            return USFearGreedIndex._get_fallback_data(
                f"API Error: {response.status_code}"
            )

        except Exception as e:
            logger.error(f" 获取CNN恐慌贪婪指数失败: {e}")
            return USFearGreedIndex._get_fallback_data(str(e))

    @staticmethod
    def _get_fallback_data(error_msg: str) -> Dict[str, Any]:
        """获取失败时返回错误信息，不返回假数据"""
        return {
            "error": error_msg,
            "message": "无法获取CNN恐慌贪婪指数",
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
                "market_breadth": USFearGreedIndex._get_market_breadth(),
                "safe_haven": USFearGreedIndex._get_safe_haven_demand(),
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
                    latest_vix = safe_float(df.iloc[-1]["close"])
                    if latest_vix is not None:
                        return USFearGreedIndex._format_vix_score(latest_vix)
            except Exception as e:
                logger.warning(f"⚠️ VIX API 获取失败 (将使用计算回退): {e}")

            # 2. 回退模式: 计算标普500的历史波动率 (Realized Volatility)
            # 逻辑: VIX ≈ 预期波动率，历史波动率是其良好近似
            logger.info("🔄 使用标普500波动率计算 VIX 替代值...")
            
            # 获取标普500数据 (多取一些数据以计算滚动窗口)
            df_sp500 = akshare_call_with_retry(ak.stock_us_daily, symbol=".INX")
            
            if df_sp500.empty or len(df_sp500) < 30:
                return {"error": "数据不足无法计算VIX", "weight": 0.3}

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
            return {"error": str(e), "weight": 0.3}

    @staticmethod
    def _format_vix_score(vix_value: float, is_estimated: bool = False) -> Dict[str, Any]:
        """格式化 VIX 分数"""
        if vix_value > 30:
            vix_score = max(0, 100 - (vix_value - 30) * 3)
        elif vix_value > 20:
            vix_score = 70 - (vix_value - 20) * 2
        else:
            vix_score = 70 + (20 - vix_value) * 1.5
        vix_score = min(100, max(0, vix_score))
        
        return {
            "value": round(vix_value, 2),
            "score": round(vix_score, 1),
            "weight": 0.3,
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
                return {"error": "数据不足", "weight": 0.25}
            
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
                "weight": 0.25,
            }
        except Exception as e:
            logger.warning(f"⚠️ 获取标普500数据失败: {e}")
            return {"error": str(e), "weight": 0.25}

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
                return {"error": "数据不足", "weight": 0.2}
            
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
                "weight": 0.2,
            }
        except Exception as e:
            logger.warning(f"⚠️ 获取市场广度数据失败: {e}")
            return {"error": str(e), "weight": 0.2}

    @staticmethod
    def _get_safe_haven_demand() -> Dict[str, Any]:
        """
        获取避险需求数据
        使用 VIX 作为主要参考指标
        """
        try:
            vix_data = USFearGreedIndex._get_vix_data()
            vix_score = vix_data.get("score", 50)
            
            # VIX越高(恐慌)，避险需求越高，这应该贡献给"恐慌"分数(低分)
            # 所以直接复用 VIX 的分数即可
            
            return {
                "treasury_demand": 0, # 暂时无法获取美债数据
                "score": vix_score,
                "weight": 0.25,
                "note": "基于VIX推算",
            }
        except Exception as e:
            logger.warning(f"⚠️ 获取避险需求数据失败: {e}")
            return {"error": str(e), "weight": 0.25}

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
        if score >= 80:
            return "极度贪婪", "市场情绪极度乐观"
        elif score >= 65:
            return "贪婪", "市场情绪乐观"
        elif score >= 55:
            return "轻微贪婪", "市场情绪略显乐观"
        elif score >= 45:
            return "中性", "市场情绪平衡"
        elif score >= 35:
            return "轻微恐慌", "市场情绪略显悲观"
        elif score >= 20:
            return "恐慌", "市场情绪悲观"
        else:
            return "极度恐慌", "市场情绪极度悲观"

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
        return """
自定义美国市场恐慌贪婪指数说明：
• 基于VIX、标普500动量、市场广度、避险需求综合计算
        """.strip()
