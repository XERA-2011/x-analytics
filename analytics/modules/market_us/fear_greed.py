"""
美国市场恐慌贪婪指数
获取CNN Fear & Greed Index和自定义计算
"""

import akshare as ak
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.fear_greed import (
    build_factor,
    calculate_composite_score,
    build_fear_greed_meta,
    build_fear_greed_response,
    build_fear_greed_error,
    build_fear_greed_explanation,
    score_percent_change,
    score_volatility_level,
)
from ...core.logger import logger


class USFearGreedIndex:
    """美国市场恐慌贪婪指数"""

    META = build_fear_greed_meta(
        market="US",
        asset="标普500代理情绪",
        methodology="custom_proxy",
        cadence="daily",
        reference_note="与 CNN Fear & Greed 官方指数并非同口径，不能直接对比",
    )

    DEFAULT_WEIGHTS = {
        "volatility": 0.30,
        "momentum": 0.25,
        "daily_change": 0.25,
        "breadth": 0.20,
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
        raw = settings.FEAR_GREED_CONFIG.get("us", {}).get("weights", USFearGreedIndex.DEFAULT_WEIGHTS)
        return {
            "volatility": raw.get("volatility", raw.get("vix", USFearGreedIndex.DEFAULT_WEIGHTS["volatility"])),
            "momentum": raw.get("momentum", raw.get("sp500_momentum", USFearGreedIndex.DEFAULT_WEIGHTS["momentum"])),
            "daily_change": raw.get("daily_change", USFearGreedIndex.DEFAULT_WEIGHTS["daily_change"]),
            "breadth": raw.get("breadth", raw.get("market_breadth", USFearGreedIndex.DEFAULT_WEIGHTS["breadth"])),
        }

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
    def _fetch_market_frames(symbols: Tuple[str, ...]) -> Dict[str, pd.DataFrame]:
        """
        批量拉取并缓存本次计算所需的市场数据，避免同一轮计算重复请求。
        """
        frames: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            try:
                df = akshare_call_with_retry(ak.stock_us_daily, symbol=symbol)
                if df is not None and not df.empty:
                    frames[symbol] = USFearGreedIndex._sort_by_date(df)
            except Exception as e:
                logger.warning(f"⚠️ 获取 {symbol} 数据失败: {e}")
        return frames

    @staticmethod
    @cached(
        "market_us:fear_greed_v2",
        ttl=settings.CACHE_TTL["fear_greed_realtime"],
        stale_ttl=settings.CACHE_TTL["fear_greed_stale"],
    )
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
                return build_fear_greed_error(
                    error=custom_data["error"],
                    message="无法获取自定义美股情绪指数",
                    update_time=get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                    meta=USFearGreedIndex.META,
                )

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
                "meta": USFearGreedIndex.META,
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
            "meta": USFearGreedIndex.META,
        }
    @staticmethod
    @cached(
        "market_us:custom_fear_greed_v2",
        ttl=settings.CACHE_TTL["fear_greed_realtime"],
        stale_ttl=settings.CACHE_TTL["fear_greed_stale"],
    )
    def calculate_custom_index() -> Dict[str, Any]:
        """
        计算自定义美国市场恐慌贪婪指数
        基于VIX、标普500等指标
        """
        try:
            update_time = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            frames = USFearGreedIndex._fetch_market_frames((".INX", ".DJI", ".IXIC", ".VIX"))
            inx_df = frames.get(".INX")
            dji_df = frames.get(".DJI")
            ndx_df = frames.get(".IXIC")
            vix_df = frames.get(".VIX")

            indicators = {
                "volatility": USFearGreedIndex._get_vix_data(vix_df=vix_df, sp500_df=inx_df),
                "momentum": USFearGreedIndex._get_sp500_data(inx_df=inx_df),
                "daily_change": USFearGreedIndex._get_daily_change(inx_df=inx_df),
                "breadth": USFearGreedIndex._get_market_breadth(dji_df=dji_df, ndx_df=ndx_df),
            }

            composite_score = USFearGreedIndex._calculate_composite_score(indicators)
            
            # 如果无法计算综合得分（所有指标都失败），返回错误
            if composite_score is None:
                return build_fear_greed_error(
                    error="无法获取足够的指标数据",
                    message="所有指标获取失败",
                    update_time=update_time,
                    meta=USFearGreedIndex.META,
                    extra={"indicators": indicators},
                )
            
            level, description = USFearGreedIndex._get_level_description(
                composite_score
            )

            return build_fear_greed_response(
                score=composite_score,
                level=level,
                description=description,
                indicators=indicators,
                update_time=update_time,
                explanation=USFearGreedIndex._get_custom_explanation(),
                levels=USFearGreedIndex._get_levels_payload(),
                meta=USFearGreedIndex.META,
            )

        except Exception as e:
            logger.error(f"❌ 计算自定义恐慌贪婪指数失败: {e}")
            return build_fear_greed_error(
                error=str(e),
                message="无法计算自定义恐慌贪婪指数",
                update_time=get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                meta=USFearGreedIndex.META,
            )

    @staticmethod
    def _get_vix_data(
        vix_df: Optional[pd.DataFrame] = None,
        sp500_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        获取 VIX 数据
        策略: 优先尝试 API (.VIX), 失败则计算标普500历史波动率作为替代
        """
        try:
            # 1. 优先尝试直接获取 VIX 数据
            try:
                df = vix_df.copy() if vix_df is not None else akshare_call_with_retry(ak.stock_us_daily, symbol=".VIX")
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
            df_sp500 = sp500_df.copy() if sp500_df is not None else akshare_call_with_retry(ak.stock_us_daily, symbol=".INX")
            
            if df_sp500.empty or len(df_sp500) < 30:
                return {"error": "数据不足无法计算VIX", "weight": USFearGreedIndex._get_weights()["volatility"]}
            df_sp500 = USFearGreedIndex._sort_by_date(df_sp500)

            # 计算对数收益率
            df_sp500["close"] = pd.to_numeric(df_sp500["close"], errors="coerce")
            df_sp500["log_ret"] = np.log(df_sp500["close"] / df_sp500["close"].shift(1))
            
            # 计算20日滚动波动率 (年化)
            # window=20 (约一个月交易日), x 100 (百分比), x sqrt(252) (年化)
            rolling_vol = df_sp500["log_ret"].rolling(window=20).std() * np.sqrt(252) * 100
            
            latest_vol = safe_float(rolling_vol.iloc[-1])
            
            if latest_vol is None:
                return {"error": "波动率计算失败", "weight": USFearGreedIndex._get_weights()["volatility"]}

            return USFearGreedIndex._format_vix_score(latest_vol, is_estimated=True)

        except Exception as e:
            logger.warning(f"⚠️ 获取/计算 VIX 数据失败: {e}")
            return {"error": str(e), "weight": USFearGreedIndex._get_weights()["volatility"]}

    @staticmethod
    def _get_daily_change(inx_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """获取标普500单日涨跌幅 (Sentiment Sensitivity)"""
        try:
            df = inx_df.copy() if inx_df is not None else akshare_call_with_retry(ak.stock_us_daily, symbol=".INX")
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
            score = score_percent_change(change_pct, sensitivity=10)
            
            return build_factor(
                value=round(change_pct, 2),
                score=score,
                weight=USFearGreedIndex._get_weights()["daily_change"],
                label="当日涨跌",
            )
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
        
        vix_score = score_volatility_level(
            vix_value,
            neutral_level=20.0,
            calm_sensitivity=2.0,
            stress_sensitivity=2.5,
        )
        
        return build_factor(
            value=round(vix_value, 2),
            score=vix_score,
            weight=USFearGreedIndex._get_weights()["volatility"],
            label="VIX波动率",
            is_estimated=is_estimated,
            note="基于标普500波动率估算" if is_estimated else "API直接获取",
        )


    @staticmethod
    def _get_sp500_data(inx_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """获取标普500动量数据"""
        try:
            # 使用 AkShare 获取标普500指数数据 (代号 .INX)
            df = inx_df.copy() if inx_df is not None else akshare_call_with_retry(ak.stock_us_daily, symbol=".INX")
            if df.empty or len(df) < 20:
                return {"error": "数据不足", "weight": USFearGreedIndex._get_weights()["momentum"]}
            df = USFearGreedIndex._sort_by_date(df)
            
            # 计算20日动量 (新接口返回英文列名: close)
            recent = df.tail(20)
            momentum_pct = (
                (recent["close"].iloc[-1] - recent["close"].iloc[0])
                / recent["close"].iloc[0]
                * 100
            )
            
            # 动量转换为分数 (涨5%=75, 涨10%=100, 跌5%=25)
            score = score_percent_change(momentum_pct, sensitivity=4)
            
            return build_factor(
                value=round(momentum_pct, 2),
                score=score,
                weight=USFearGreedIndex._get_weights()["momentum"],
                label="标普500动量",
            )
        except Exception as e:
            logger.warning(f"⚠️ 获取标普500数据失败: {e}")
            return {"error": str(e), "weight": USFearGreedIndex._get_weights()["momentum"]}

    @staticmethod
    def _get_market_breadth(
        dji_df: Optional[pd.DataFrame] = None,
        ndx_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        获取市场广度数据
        注: 美国市场涨跌家数难以直接获取，使用道琼斯/纳斯达克相对表现代替
        """
        try:
            # 获取道琼斯(.DJI)和纳斯达克(.IXIC)
            dji = dji_df.copy() if dji_df is not None else akshare_call_with_retry(ak.stock_us_daily, symbol=".DJI")
            ndx = ndx_df.copy() if ndx_df is not None else akshare_call_with_retry(ak.stock_us_daily, symbol=".IXIC") # 纳斯达克综合
            
            if dji.empty or ndx.empty:
                return {"error": "数据不足", "weight": USFearGreedIndex._get_weights()["breadth"]}
            dji = USFearGreedIndex._sort_by_date(dji)
            ndx = USFearGreedIndex._sort_by_date(ndx)
            
            # 比较近5日表现 (新接口返回英文列名: close)
            dji_change = (dji["close"].iloc[-1] - dji["close"].iloc[-5]) / dji["close"].iloc[-5] * 100
            ndx_change = (ndx["close"].iloc[-1] - ndx["close"].iloc[-5]) / ndx["close"].iloc[-5] * 100
            
            # 如果大盘股(道琼斯)和成长股(纳斯达克)同涨=贪婪, 同跌=恐慌
            avg_change = (dji_change + ndx_change) / 2
            score = score_percent_change(avg_change, sensitivity=4)
            
            return build_factor(
                value=round(avg_change, 2),
                score=score,
                weight=USFearGreedIndex._get_weights()["breadth"],
                label="市场分化",
                note="以道指/纳指近5日表现近似广度",
                dji_5d_change=round(dji_change, 2),
                ndx_5d_change=round(ndx_change, 2),
            )
        except Exception as e:
            logger.warning(f"⚠️ 获取市场广度数据失败: {e}")
            return {"error": str(e), "weight": USFearGreedIndex._get_weights()["breadth"]}

    @staticmethod
    def _calculate_composite_score(indicators: Dict[str, Any]) -> Optional[float]:
        """计算综合得分，跳过有错误的指标"""
        return calculate_composite_score(indicators)

    @staticmethod
    def _get_level_description(score: float) -> tuple:
        for threshold, level, description in USFearGreedIndex._get_levels():
            if score >= threshold:
                return level, description
        return "未知", "无法判断情绪等级"

    @staticmethod
    def _get_cnn_explanation() -> str:
        return build_fear_greed_explanation(
            title="美国市场情绪指数",
            factors=[
                ("CNN 官方指数", 1.0, "当前接口已切换为 AkShare 代理估算，不直接抓取 CNN 原始页面"),
            ],
            levels=USFearGreedIndex._get_levels(),
            methodology_note="当前页面展示的是基于美股行情因子的代理情绪指数，用于替代 CNN 官方指数，不代表 CNN 官方观点。",
        )

    @staticmethod
    def _get_custom_explanation() -> str:
        weights = USFearGreedIndex._get_weights()
        return build_fear_greed_explanation(
            title="美国市场情绪指数",
            factors=[
                ("波动率代理", weights["volatility"], "反映市场避险与紧张程度"),
                ("动量", weights["momentum"], "反映主要指数趋势强弱"),
                ("当日涨跌", weights["daily_change"], "反映短线价格变化"),
                ("广度代理", weights["breadth"], "以道指与纳指表现差异近似市场分化"),
            ],
            levels=USFearGreedIndex._get_levels(),
            methodology_note="该指数为基于美股行情因子的代理估算，用于替代 CNN 官方指数，不代表 CNN 官方观点，也不建议与其他市场横向直接比较。",
        )
