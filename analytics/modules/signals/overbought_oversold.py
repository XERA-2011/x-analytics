"""
超买超卖综合信号计算模块
基于多技术指标综合判断市场超买超卖状态
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, Optional, List
from .indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_bollinger,
    calculate_kdj,
    detect_volume_anomaly,
    get_signal_from_rsi,
    get_signal_from_kdj,
    get_signal_from_bollinger,
)
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import get_beijing_time, akshare_call_with_retry, safe_float
from ...core.logger import logger


# 指标权重配置
INDICATOR_WEIGHTS = {
    "rsi": 0.30,
    "macd": 0.25,
    "bollinger": 0.20,
    "kdj": 0.15,
    "volume": 0.10,
}


class OverboughtOversoldSignal:
    """超买超卖综合信号计算器"""

    # 市场标的配置
    MARKET_SYMBOLS = {
        "CN": {"symbol": "sh000001", "name": "上证指数", "func": "stock_zh_index_daily"},
        "HK": {"symbol": "HSI", "name": "恒生指数", "func": "stock_hk_index_daily_em"},
        "US": {"symbol": ".INX", "name": "标普500", "func": "stock_us_daily"},
        "GOLD": {"symbol": "au0", "name": "沪金主力", "func": "futures_zh_daily_sina"},
        "SILVER": {"symbol": "ag0", "name": "沪银主力", "func": "futures_zh_daily_sina"},
    }

    @staticmethod
    @cached(
        "signals:obo:cn:daily",
        ttl=settings.CACHE_TTL.get("market", 1800),
        stale_ttl=settings.CACHE_TTL.get("market", 1800) * settings.STALE_TTL_RATIO,
    )
    def get_cn_signal(period: str = "daily") -> Dict[str, Any]:
        """获取A股超买超卖信号"""
        return OverboughtOversoldSignal._calculate("CN", period)

    @staticmethod
    @cached(
        "signals:obo:hk:daily",
        ttl=settings.CACHE_TTL.get("market", 1800),
        stale_ttl=settings.CACHE_TTL.get("market", 1800) * settings.STALE_TTL_RATIO,
    )
    def get_hk_signal(period: str = "daily") -> Dict[str, Any]:
        """获取港股超买超卖信号"""
        return OverboughtOversoldSignal._calculate("HK", period)

    @staticmethod
    @cached(
        "signals:obo:us:daily",
        ttl=settings.CACHE_TTL.get("market", 1800),
        stale_ttl=settings.CACHE_TTL.get("market", 1800) * settings.STALE_TTL_RATIO,
    )
    def get_us_signal(period: str = "daily") -> Dict[str, Any]:
        """获取美股超买超卖信号"""
        return OverboughtOversoldSignal._calculate("US", period)

    @staticmethod
    @cached(
        "signals:obo:gold:daily",
        ttl=settings.CACHE_TTL.get("metals", 3600),
        stale_ttl=settings.CACHE_TTL.get("metals", 3600) * settings.STALE_TTL_RATIO,
    )
    def get_gold_signal(period: str = "daily") -> Dict[str, Any]:
        """获取黄金超买超卖信号"""
        return OverboughtOversoldSignal._calculate("GOLD", period)

    @staticmethod
    @cached(
        "signals:obo:silver:daily",
        ttl=settings.CACHE_TTL.get("metals", 3600),
        stale_ttl=settings.CACHE_TTL.get("metals", 3600) * settings.STALE_TTL_RATIO,
    )
    def get_silver_signal(period: str = "daily") -> Dict[str, Any]:
        """获取白银超买超卖信号"""
        return OverboughtOversoldSignal._calculate("SILVER", period)

    @staticmethod
    def _calculate(market: str, period: str = "daily") -> Dict[str, Any]:
        """
        计算超买超卖综合信号
        
        Args:
            market: CN, US, GOLD, SILVER
            period: daily 或 60min
        """
        try:
            config = OverboughtOversoldSignal.MARKET_SYMBOLS.get(market)
            if not config:
                return {"error": f"不支持的市场: {market}"}

            # 获取K线数据
            df = OverboughtOversoldSignal._fetch_data(market, period)
            if df is None or df.empty:
                return {
                    "error": "无法获取行情数据",
                    "market": market,
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }

            # 确保数据足够
            if len(df) < 60:
                return {
                    "error": f"数据不足: 需要60条，实际{len(df)}条",
                    "market": market,
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }

            # 计算各项指标
            indicators = OverboughtOversoldSignal._calculate_all_indicators(df)

            # 计算综合信号
            composite = OverboughtOversoldSignal._calculate_composite(indicators)

            return {
                "market": market,
                "symbol": config["symbol"],
                "name": config["name"],
                "period": period,
                "signal": composite["signal"],
                "strength": composite["strength"],
                "level": composite["level"],
                "description": composite["description"],
                "indicators": indicators,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception as e:
            logger.error(f"❌ 计算{market}超买超卖信号失败: {e}")
            return {
                "error": str(e),
                "message": f"无法计算{market}超买超卖信号",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def _fetch_data(market: str, period: str) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        config = OverboughtOversoldSignal.MARKET_SYMBOLS.get(market)
        if not config:
            return None

        try:
            if market == "CN":
                if period == "60min":
                    df = akshare_call_with_retry(
                        ak.stock_zh_a_minute,
                        symbol=config["symbol"],
                        period="60",
                    )
                else:
                    df = akshare_call_with_retry(
                        ak.stock_zh_index_daily,
                        symbol=config["symbol"],
                    )
            elif market == "HK":
                # 恒生指数日线 (使用 sina 源，与 fear_greed 模块一致)
                df = akshare_call_with_retry(
                    ak.stock_hk_index_daily_sina,
                    symbol=config["symbol"],
                )
            elif market == "US":
                # 美股日线
                df = akshare_call_with_retry(
                    ak.stock_us_daily,
                    symbol=config["symbol"],
                )
            elif market in ("GOLD", "SILVER"):
                if period == "60min":
                    df = akshare_call_with_retry(
                        ak.futures_zh_minute_sina,
                        symbol=config["symbol"],
                        period="60",
                    )
                else:
                    df = akshare_call_with_retry(
                        ak.futures_zh_daily_sina,
                        symbol=config["symbol"],
                    )
            else:
                return None

            # 标准化列名
            df.columns = [c.lower() for c in df.columns]
            
            # 确保数值类型
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            
            if "volume" in df.columns:
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            
            return df

        except Exception as e:
            logger.warning(f"⚠️ 获取{market} {period}数据失败: {e}")
            return None

    @staticmethod
    def _calculate_all_indicators(df: pd.DataFrame) -> Dict[str, Any]:
        """计算所有技术指标"""
        indicators = {}
        close = df["close"]

        # 1. RSI
        rsi_value = calculate_rsi(close, 14)
        rsi_signal, rsi_score = get_signal_from_rsi(rsi_value)
        indicators["rsi"] = {
            "value": round(rsi_value, 2) if rsi_value else None,
            "signal": rsi_signal,
            "score": rsi_score,
            "weight": INDICATOR_WEIGHTS["rsi"],
        }

        # 2. MACD
        macd_data = calculate_macd(close)
        if "error" not in macd_data:
            # MACD 背离作为超买超卖信号
            if macd_data["divergence"]:
                if macd_data["divergence_type"] == "bearish":
                    macd_signal, macd_score = "overbought", 75
                else:
                    macd_signal, macd_score = "oversold", 25
            else:
                # 根据 histogram 判断
                hist = macd_data["histogram"]
                if hist > 0:
                    macd_signal = "neutral"
                    macd_score = 50 + min(30, hist * 100)
                else:
                    macd_signal = "neutral"
                    macd_score = 50 + max(-30, hist * 100)
            
            indicators["macd"] = {
                "histogram": round(macd_data["histogram"], 4),
                "divergence": macd_data["divergence"],
                "divergence_type": macd_data["divergence_type"],
                "signal": macd_signal,
                "score": macd_score,
                "weight": INDICATOR_WEIGHTS["macd"],
            }
        else:
            indicators["macd"] = {"error": macd_data["error"], "weight": INDICATOR_WEIGHTS["macd"]}

        # 3. 布林带
        boll_data = calculate_bollinger(close)
        if "error" not in boll_data:
            boll_signal, boll_score = get_signal_from_bollinger(boll_data["position"])
            indicators["bollinger"] = {
                "position": round(boll_data["position"], 3),
                "bandwidth": round(boll_data["bandwidth"], 2),
                "signal": boll_signal,
                "score": boll_score,
                "weight": INDICATOR_WEIGHTS["bollinger"],
            }
        else:
            indicators["bollinger"] = {"error": boll_data["error"], "weight": INDICATOR_WEIGHTS["bollinger"]}

        # 4. KDJ
        if all(col in df.columns for col in ["high", "low", "close"]):
            kdj_data = calculate_kdj(df["high"], df["low"], close)
            if "error" not in kdj_data:
                kdj_signal, kdj_score = get_signal_from_kdj(kdj_data["k"], kdj_data["d"])
                indicators["kdj"] = {
                    "k": round(kdj_data["k"], 2),
                    "d": round(kdj_data["d"], 2),
                    "j": round(kdj_data["j"], 2),
                    "signal": kdj_signal,
                    "score": kdj_score,
                    "weight": INDICATOR_WEIGHTS["kdj"],
                }
            else:
                indicators["kdj"] = {"error": kdj_data["error"], "weight": INDICATOR_WEIGHTS["kdj"]}
        else:
            indicators["kdj"] = {"error": "缺少高低价数据", "weight": INDICATOR_WEIGHTS["kdj"]}

        # 5. 成交量异常
        if "volume" in df.columns:
            vol_data = detect_volume_anomaly(close, df["volume"])
            if "error" not in vol_data:
                # 量价背离转信号
                if vol_data["anomaly"]:
                    if vol_data["type"] == "divergence_up":
                        vol_signal, vol_score = "overbought", 70
                    else:
                        vol_signal, vol_score = "oversold", 30
                else:
                    vol_signal, vol_score = "neutral", 50
                
                indicators["volume"] = {
                    "anomaly": vol_data["anomaly"],
                    "type": vol_data["type"],
                    "ratio": vol_data["volume_ratio"],
                    "signal": vol_signal,
                    "score": vol_score,
                    "weight": INDICATOR_WEIGHTS["volume"],
                }
            else:
                indicators["volume"] = {"error": vol_data["error"], "weight": INDICATOR_WEIGHTS["volume"]}
        else:
            indicators["volume"] = {"error": "无成交量数据", "weight": INDICATOR_WEIGHTS["volume"]}

        return indicators

    @staticmethod
    def _calculate_composite(indicators: Dict[str, Any]) -> Dict[str, Any]:
        """计算综合信号"""
        total_score = 0.0
        total_weight = 0.0
        signals: List[str] = []

        for name, data in indicators.items():
            if "error" in data:
                continue
            
            score = safe_float(data.get("score"), None)
            weight = safe_float(data.get("weight", 0))
            
            if score is not None and weight > 0:
                total_score += score * weight
                total_weight += weight
                signals.append(data.get("signal", "neutral"))

        if total_weight == 0:
            return {
                "signal": "neutral",
                "strength": 50,
                "level": "中性",
                "description": "指标数据不足",
            }

        composite_score = total_score / total_weight

        # 判断信号
        if composite_score >= 75:
            signal = "overbought"
            level = "强烈超买"
            desc = "多项指标共振，市场处于强烈超买状态，回调风险较高"
        elif composite_score >= 60:
            signal = "overbought"
            level = "超买"
            desc = "技术指标偏向超买，建议谨慎追高"
        elif composite_score <= 25:
            signal = "oversold"
            level = "强烈超卖"
            desc = "多项指标共振，市场处于强烈超卖状态，可能存在反弹机会"
        elif composite_score <= 40:
            signal = "oversold"
            level = "超卖"
            desc = "技术指标偏向超卖，可关注企稳信号"
        else:
            signal = "neutral"
            level = "中性"
            desc = "技术指标未出现明显超买超卖信号"

        return {
            "signal": signal,
            "strength": round(composite_score, 1),
            "level": level,
            "description": desc,
        }
