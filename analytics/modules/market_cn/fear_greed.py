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
from ...core.utils import get_beijing_time, akshare_call_with_retry, safe_float
from ...core.fear_greed import (
    build_factor,
    calculate_composite_score,
    build_fear_greed_meta,
    build_fear_greed_response,
    build_fear_greed_error,
    build_fear_greed_explanation,
    score_percent_change,
    score_rsi,
    score_volatility_level,
)
from ...core.logger import logger


class CNFearGreedIndex:
    """中国市场恐慌贪婪指数计算"""

    META = build_fear_greed_meta(
        market="CN",
        asset="上证指数",
        methodology="technical_composite",
        cadence="daily+intraday",
    )

    DEFAULT_WEIGHTS = {
        "momentum": 0.20,
        "volatility": 0.15,
        "flow": 0.15,
        "rsi": 0.20,
        "breadth": 0.10,
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
        raw = settings.FEAR_GREED_CONFIG.get("cn", {}).get("weights", CNFearGreedIndex.DEFAULT_WEIGHTS)
        return {
            "momentum": raw.get("momentum", raw.get("price_momentum", CNFearGreedIndex.DEFAULT_WEIGHTS["momentum"])),
            "volatility": raw.get("volatility", CNFearGreedIndex.DEFAULT_WEIGHTS["volatility"]),
            "flow": raw.get("flow", raw.get("volume", CNFearGreedIndex.DEFAULT_WEIGHTS["flow"])),
            "rsi": raw.get("rsi", CNFearGreedIndex.DEFAULT_WEIGHTS["rsi"]),
            "breadth": raw.get("breadth", raw.get("price_position", CNFearGreedIndex.DEFAULT_WEIGHTS["breadth"])),
            "daily_change": raw.get("daily_change", CNFearGreedIndex.DEFAULT_WEIGHTS["daily_change"]),
        }

    @staticmethod
    def _get_levels() -> list:
        return settings.FEAR_GREED_CONFIG.get("cn", {}).get("levels", CNFearGreedIndex.DEFAULT_LEVELS)

    @staticmethod
    def _get_levels_payload() -> list:
        return [{"min": t, "label": l, "description": d} for t, l, d in CNFearGreedIndex._get_levels()]

    @staticmethod
    def _apply_realtime_index_snapshot(index_data: pd.DataFrame, symbol: str) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """用实时指数快照修正最后一根数据，避免盘中仍使用上一交易日收盘价。"""
        snapshot: Dict[str, Any] = {"source": "daily"}

        try:
            spot_df = akshare_call_with_retry(
                ak.stock_zh_index_spot_sina,
                max_retries=3,
            )
            if spot_df.empty or "代码" not in spot_df.columns:
                return index_data, snapshot

            rows = spot_df[spot_df["代码"] == symbol]
            if rows.empty:
                compact_symbol = symbol[2:] if symbol.startswith(("sh", "sz")) else symbol
                rows = spot_df[spot_df["代码"].astype(str).str.endswith(compact_symbol)]
            if rows.empty:
                return index_data, snapshot

            row = rows.iloc[0]
            latest = safe_float(row.get("最新价"), None)
            prev_close = safe_float(row.get("昨收"), None)
            change_pct = safe_float(row.get("涨跌幅"), None)
            if latest is None or latest <= 0:
                return index_data, snapshot

            patched = index_data.copy()
            date_col = next((col for col in ["date", "trade_date"] if col in patched.columns), None)
            today = get_beijing_time().date()

            if date_col:
                parsed_dates = pd.to_datetime(patched[date_col], errors="coerce").dt.date
                if parsed_dates.iloc[-1] == today:
                    target_index = patched.index[-1]
                    patched.loc[target_index, "close"] = latest
                    patched.loc[target_index, "high"] = max(
                        safe_float(row.get("最高"), latest) or latest,
                        safe_float(patched.loc[target_index, "high"], latest) or latest,
                    )
                    patched.loc[target_index, "low"] = min(
                        safe_float(row.get("最低"), latest) or latest,
                        safe_float(patched.loc[target_index, "low"], latest) or latest,
                    )
                else:
                    new_row = patched.iloc[-1].copy()
                    new_row[date_col] = today
                    new_row["open"] = safe_float(row.get("今开"), latest) or latest
                    new_row["high"] = safe_float(row.get("最高"), latest) or latest
                    new_row["low"] = safe_float(row.get("最低"), latest) or latest
                    new_row["close"] = latest
                    if "volume" in patched.columns:
                        new_row["volume"] = safe_float(row.get("成交量"), 0) or 0
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
            logger.warning(f"⚠️ A股实时指数快照获取失败，回退日线数据: {e}")
            return index_data, snapshot

    @staticmethod
    @cached(
        "market_cn:fear_greed_v2",
        ttl=settings.CACHE_TTL["fear_greed_realtime"],
        stale_ttl=settings.CACHE_TTL["fear_greed_stale"],
    )
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
            update_time = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")

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

            index_data, realtime_snapshot = CNFearGreedIndex._apply_realtime_index_snapshot(index_data, symbol)

            # 取最近的数据
            recent_data = index_data.tail(days)
            if len(recent_data) < days:
                raise ValueError(f"数据不足，需要{days}天，实际{len(recent_data)}天")

            # 计算各项指标
            indicators = CNFearGreedIndex._calculate_indicators(recent_data, symbol)
            if "daily_change" in indicators and realtime_snapshot.get("change_pct") is not None:
                change_pct = realtime_snapshot["change_pct"]
                indicators["daily_change"] = build_factor(
                    value=round(change_pct, 2),
                    score=score_percent_change(change_pct, sensitivity=10),
                    weight=CNFearGreedIndex._get_weights()["daily_change"],
                    label="当日涨跌",
                )
            
            # 如果指标计算失败，返回错误
            if "error" in indicators:
                return build_fear_greed_error(
                    error=indicators["error"],
                    message="无法计算指标数据",
                    update_time=update_time,
                    meta=CNFearGreedIndex.META,
                )

            # 计算综合指数 (0-100)
            fear_greed_score = CNFearGreedIndex._calculate_composite_score(indicators)
            
            # 如果无法计算综合得分，返回错误
            if fear_greed_score is None:
                return build_fear_greed_error(
                    error="无法计算综合得分",
                    message="指标数据不足",
                    update_time=update_time,
                    meta=CNFearGreedIndex.META,
                    extra={"indicators": indicators},
                )

            # 确定等级
            level, description = CNFearGreedIndex._get_level_description(
                fear_greed_score
            )

            return build_fear_greed_response(
                score=fear_greed_score,
                level=level,
                description=description,
                indicators=indicators,
                update_time=update_time,
                explanation=CNFearGreedIndex._get_explanation(),
                levels=CNFearGreedIndex._get_levels_payload(),
                meta=CNFearGreedIndex.META,
                extra={"symbol": symbol, "days": days, "data_source": realtime_snapshot["source"]},
            )

        except Exception as e:
            logger.error(f"❌ 计算恐慌贪婪指数失败: {e}")
            return build_fear_greed_error(
                error=str(e),
                message="无法计算恐慌贪婪指数",
                update_time=get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                meta=CNFearGreedIndex.META,
            )

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
            momentum_score = score_percent_change(price_change, sensitivity=4)
            indicators["momentum"] = build_factor(
                value=round(price_change, 2),
                score=momentum_score,
                weight=CNFearGreedIndex._get_weights()["momentum"],
                label="价格动量",
            )

            # 2. 波动率 (Volatility) - 权重15%
            returns = data["close"].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100  # 年化波动率
            if pd.isna(volatility):
                return {"error": "波动率数据不足"}
            # 波动率越高，恐慌程度越高，分数越低
            volatility_score = score_volatility_level(volatility, neutral_level=22.0)
            indicators["volatility"] = build_factor(
                value=round(volatility, 2),
                score=volatility_score,
                weight=CNFearGreedIndex._get_weights()["volatility"],
                label="年化波动率",
            )

            # 3. 成交量 (Volume) - 权重15%
            if "volume" in data.columns:
                avg_volume = data["volume"].tail(5).mean()
                prev_avg_volume = data["volume"].head(5).mean()
                volume_change = (
                    (avg_volume - prev_avg_volume) / prev_avg_volume * 100
                    if prev_avg_volume > 0
                    else 0
                )
                volume_score = score_percent_change(volume_change, sensitivity=0.5)
                indicators["flow"] = build_factor(
                    value=round(volume_change, 2),
                    score=volume_score,
                    weight=CNFearGreedIndex._get_weights()["flow"],
                    label="成交量变化",
                )
            else:
                logger.warning("⚠️ 成交量数据不可用，跳过 flow 指标")

            # 4. RSI指标 - 权重20% (不变)
            rsi = CNFearGreedIndex._calculate_rsi(data["close"])
            if rsi is None:
                return {"error": "RSI 数据不足"}
            # RSI > 70 贪婪，RSI < 30 恐慌
            rsi_score = score_rsi(rsi)
            indicators["rsi"] = build_factor(
                value=round(rsi, 2),
                score=rsi_score,
                weight=CNFearGreedIndex._get_weights()["rsi"],
                label="RSI (14)",
            )

            # 5. 价格区间位置 (Price Position) - 权重10%
            # 这里简化处理，使用价格区间相对位置（并非真实涨跌家数广度）
            price_range = data["high"].max() - data["low"].min()
            if price_range <= 0:
                return {"error": "价格区间不足，无法计算区间位置"}
            high_low_ratio = (data["close"].iloc[-1] - data["low"].min()) / price_range
            breadth_score = max(0, min(100, high_low_ratio * 100))
            indicators["breadth"] = build_factor(
                value=round(high_low_ratio, 3),
                score=breadth_score,
                weight=CNFearGreedIndex._get_weights()["breadth"],
                label="价格区间位置",
                note="以指数区间位置近似广度",
            )

            # 6. 当日涨跌 (Daily Change) - 权重20% (新增)
            # 增强对当日市场表现的敏感度
            if len(data) < 2:
                return {"error": "当日涨跌数据不足"}
            daily_chg_pct = (
                (data["close"].iloc[-1] - data["close"].iloc[-2])
                / data["close"].iloc[-2]
                * 100
            )
            daily_score = score_percent_change(daily_chg_pct, sensitivity=10)
            indicators["daily_change"] = build_factor(
                value=round(daily_chg_pct, 2),
                score=daily_score,
                weight=CNFearGreedIndex._get_weights()["daily_change"],
                label="当日涨跌",
            )

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
        if "error" in indicators:
            return None
        return calculate_composite_score(indicators)

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
        return build_fear_greed_explanation(
            title="中国市场情绪指数",
            factors=[
                ("动量", weights["momentum"], "反映价格趋势强弱"),
                ("当日涨跌", weights["daily_change"], "反映短线价格变化"),
                ("RSI", weights["rsi"], "衡量超买超卖状态"),
                ("波动率", weights["volatility"], "反映市场紧张程度"),
                ("资金流", weights["flow"], "反映成交与活跃度变化"),
                ("广度代理", weights["breadth"], "以指数区间位置近似市场广度"),
            ],
            levels=CNFearGreedIndex._get_levels(),
            methodology_note="该指数基于A股技术与行情因子合成，更适合同市场内部纵向观察，不建议直接跨市场比较。",
        )
