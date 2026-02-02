"""
技术指标计算工具库
提供 RSI、MACD、布林带、KDJ、成交量异常检测等指标计算
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from ...core.logger import logger


def calculate_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
    """
    计算 RSI (Relative Strength Index)
    
    Args:
        prices: 收盘价序列
        period: 计算周期，默认14
    
    Returns:
        RSI 值 (0-100)，数据不足时返回 None
    """
    if len(prices) < period + 1:
        return None
    
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    result = rsi.iloc[-1]
    return float(result) if not pd.isna(result) else None


def calculate_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Dict[str, Any]:
    """
    计算 MACD (Moving Average Convergence Divergence)
    
    Returns:
        {
            "macd": DIF线值,
            "signal": DEA线值,
            "histogram": MACD柱 (DIF - DEA),
            "divergence": 是否存在背离,
            "divergence_type": "bullish" | "bearish" | None
        }
    """
    if len(prices) < slow + signal:
        return {"error": "数据不足"}
    
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow  # DIF
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()  # DEA
    histogram = macd_line - signal_line  # MACD 柱
    
    # 背离检测 (简化版: 比较最近5根K线)
    divergence = False
    divergence_type = None
    
    if len(prices) >= 10:
        recent_prices = prices.tail(10)
        recent_macd = macd_line.tail(10)
        
        # 熊市背离: 价格创新高，但 MACD 未创新高
        price_new_high = recent_prices.iloc[-1] >= recent_prices.iloc[:-1].max()
        macd_no_new_high = recent_macd.iloc[-1] < recent_macd.iloc[:-1].max()
        
        if price_new_high and macd_no_new_high:
            divergence = True
            divergence_type = "bearish"
        
        # 牛市背离: 价格创新低，但 MACD 未创新低
        price_new_low = recent_prices.iloc[-1] <= recent_prices.iloc[:-1].min()
        macd_no_new_low = recent_macd.iloc[-1] > recent_macd.iloc[:-1].min()
        
        if price_new_low and macd_no_new_low:
            divergence = True
            divergence_type = "bullish"
    
    return {
        "macd": float(macd_line.iloc[-1]),
        "signal": float(signal_line.iloc[-1]),
        "histogram": float(histogram.iloc[-1]),
        "divergence": divergence,
        "divergence_type": divergence_type
    }


def calculate_bollinger(
    prices: pd.Series,
    window: int = 20,
    num_std: float = 2.0
) -> Dict[str, Any]:
    """
    计算布林带 (Bollinger Bands)
    
    Returns:
        {
            "upper": 上轨,
            "middle": 中轨 (MA),
            "lower": 下轨,
            "position": 当前价格位置 (-1 到 1，0为中轨)
            "bandwidth": 带宽百分比
        }
    """
    if len(prices) < window:
        return {"error": "数据不足"}
    
    middle = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    current_price = prices.iloc[-1]
    current_upper = upper.iloc[-1]
    current_lower = lower.iloc[-1]
    current_middle = middle.iloc[-1]
    
    # 计算位置: -1 (下轨) 到 +1 (上轨)
    band_range = current_upper - current_lower
    if band_range > 0:
        position = (current_price - current_middle) / (band_range / 2)
        position = max(-1.5, min(1.5, position))  # 允许略微超出
    else:
        position = 0.0
    
    # 带宽百分比
    bandwidth = (band_range / current_middle * 100) if current_middle > 0 else 0.0
    
    return {
        "upper": float(current_upper),
        "middle": float(current_middle),
        "lower": float(current_lower),
        "position": float(position),
        "bandwidth": float(bandwidth)
    }


def calculate_kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3
) -> Dict[str, Any]:
    """
    计算 KDJ 随机指标
    
    Args:
        high, low, close: 最高、最低、收盘价序列
        n: RSV 周期，默认9
        m1, m2: K、D 平滑系数，默认3
    
    Returns:
        {"k": K值, "d": D值, "j": J值}
    """
    if len(close) < n:
        return {"error": "数据不足"}
    
    # 计算 RSV
    low_n = low.rolling(window=n).min()
    high_n = high.rolling(window=n).max()
    
    rsv = (close - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50)  # 避免除零
    
    # 计算 K, D (EMA 平滑)
    k = rsv.ewm(span=m1, adjust=False).mean()
    d = k.ewm(span=m2, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return {
        "k": float(k.iloc[-1]),
        "d": float(d.iloc[-1]),
        "j": float(j.iloc[-1])
    }


def detect_volume_anomaly(
    close: pd.Series,
    volume: pd.Series,
    lookback: int = 20
) -> Dict[str, Any]:
    """
    检测量价背离 (成交量异常)
    
    Returns:
        {
            "anomaly": 是否存在异常,
            "type": "divergence_up" (放量滞涨) | "divergence_down" (缩量新低) | None,
            "volume_ratio": 当前成交量 / 平均成交量
        }
    """
    if len(close) < lookback or len(volume) < lookback:
        return {"error": "数据不足"}
    
    avg_volume = volume.tail(lookback).mean()
    current_volume = volume.iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # 价格变化
    price_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
    
    anomaly = False
    anomaly_type = None
    
    # 放量滞涨: 成交量放大 (>1.5倍) 但价格涨幅有限 (<1%)
    if volume_ratio > 1.5 and 0 <= price_change < 1:
        anomaly = True
        anomaly_type = "divergence_up"
    
    # 缩量新低: 成交量萎缩 (<0.7倍) 且价格创20日新低
    recent_low = close.tail(lookback).min()
    if volume_ratio < 0.7 and close.iloc[-1] <= recent_low:
        anomaly = True
        anomaly_type = "divergence_down"
    
    return {
        "anomaly": anomaly,
        "type": anomaly_type,
        "volume_ratio": round(volume_ratio, 2)
    }


def get_signal_from_rsi(rsi: Optional[float]) -> Tuple[str, float]:
    """
    RSI 信号判断
    Returns: (signal, score)
        signal: "overbought" | "oversold" | "neutral"
        score: 0-100 (50=中性, >50超买方向, <50超卖方向)
    """
    if rsi is None:
        return "neutral", 50
    
    if rsi >= 80:
        return "overbought", 90
    elif rsi >= 70:
        return "overbought", 70 + (rsi - 70)
    elif rsi <= 20:
        return "oversold", 10
    elif rsi <= 30:
        return "oversold", 30 - (30 - rsi)
    else:
        return "neutral", 50


def get_signal_from_kdj(k: float, d: float) -> Tuple[str, float]:
    """KDJ 信号判断"""
    if k >= 80 and d >= 80:
        return "overbought", 85
    elif k <= 20 and d <= 20:
        return "oversold", 15
    else:
        return "neutral", 50


def get_signal_from_bollinger(position: float) -> Tuple[str, float]:
    """布林带信号判断"""
    if position >= 1.0:
        return "overbought", 80 + min(20, (position - 1) * 20)
    elif position <= -1.0:
        return "oversold", 20 - min(20, abs(position + 1) * 20)
    else:
        return "neutral", 50 + position * 15
