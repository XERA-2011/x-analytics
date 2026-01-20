#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/15
Desc: 技术分析工具
包含常用技术指标的计算
"""

import pandas as pd
import numpy as np
from typing import Tuple


class TechnicalIndicators:
    """技术指标计算类"""

    @staticmethod
    def MA(series: pd.Series, window: int) -> pd.Series:
        """
        简单移动平均线 (Simple Moving Average)

        Args:
            series: 价格序列
            window: 窗口大小

        Returns:
            pd.Series: MA 序列
        """
        return series.rolling(window=window).mean()

    @staticmethod
    def EMA(series: pd.Series, span: int) -> pd.Series:
        """
        指数移动平均线 (Exponential Moving Average)

        Args:
            series: 价格序列
            span: 跨度

        Returns:
            pd.Series: EMA 序列
        """
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def MACD(
        series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD 指标 (Moving Average Convergence Divergence)

        Args:
            series: 价格序列
            fast: 快线周期，默认12
            slow: 慢线周期，默认26
            signal: 信号线周期，默认9

        Returns:
            Tuple[MACD线, 信号线, 柱状图]
        """
        ema_fast = TechnicalIndicators.EMA(series, fast)
        ema_slow = TechnicalIndicators.EMA(series, slow)

        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.EMA(macd_line, signal)
        histogram = (macd_line - signal_line) * 2  # 柱状图

        return macd_line, signal_line, histogram

    @staticmethod
    def RSI(series: pd.Series, window: int = 14) -> pd.Series:
        """
        相对强弱指标 (Relative Strength Index)

        Args:
            series: 价格序列
            window: 窗口大小，默认14

        Returns:
            pd.Series: RSI 值 (0-100)
        """
        delta = series.diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def BOLL(
        series: pd.Series, window: int = 20, num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        布林带 (Bollinger Bands)

        Args:
            series: 价格序列
            window: 窗口大小，默认20
            num_std: 标准差倍数，默认2

        Returns:
            Tuple[上轨, 中轨, 下轨]
        """
        middle = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()

        upper = middle + (std * num_std)
        lower = middle - (std * num_std)

        return upper, middle, lower

    @staticmethod
    def KDJ(
        high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        KDJ 随机指标

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            n: 周期，默认9

        Returns:
            Tuple[K值, D值, J值]
        """
        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()

        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100

        k = rsv.ewm(alpha=1 / 3, adjust=False).mean()
        d = k.ewm(alpha=1 / 3, adjust=False).mean()
        j = 3 * k - 2 * d

        return k, d, j

    @staticmethod
    def ATR(
        high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14
    ) -> pd.Series:
        """
        平均真实波幅 (Average True Range)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            window: 窗口大小，默认14

        Returns:
            pd.Series: ATR 值
        """
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=window).mean()

        return atr

    @staticmethod
    def OBV(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        能量潮 (On-Balance Volume)

        Args:
            close: 收盘价序列
            volume: 成交量序列

        Returns:
            pd.Series: OBV 值
        """
        direction = np.sign(close.diff())
        direction.iloc[0] = 0

        obv = (direction * volume).cumsum()
        return obv


def apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    为 DataFrame 添加常用技术指标

    Args:
        df: 股票数据，需包含 '收盘', '最高', '最低', '成交量' 列

    Returns:
        pd.DataFrame: 添加了技术指标的数据
    """
    result = df.copy()

    close = df["收盘"]
    high = df["最高"]
    low = df["最低"]
    volume = df["成交量"]

    TI = TechnicalIndicators  # 简写

    # 均线
    result["MA5"] = TI.MA(close, 5)
    result["MA10"] = TI.MA(close, 10)
    result["MA20"] = TI.MA(close, 20)
    result["MA60"] = TI.MA(close, 60)

    # MACD
    macd, signal, hist = TI.MACD(close)
    result["MACD"] = macd
    result["MACD_Signal"] = signal
    result["MACD_Hist"] = hist

    # RSI
    result["RSI"] = TI.RSI(close)

    # 布林带
    upper, middle, lower = TI.BOLL(close)
    result["BOLL_Upper"] = upper
    result["BOLL_Middle"] = middle
    result["BOLL_Lower"] = lower

    # KDJ
    k, d, j = TI.KDJ(high, low, close)
    result["K"] = k
    result["D"] = d
    result["J"] = j

    # ATR
    result["ATR"] = TI.ATR(high, low, close)

    # OBV
    result["OBV"] = TI.OBV(close, volume)

    return result


def demo():
    """演示函数"""
    import akshare as ak

    print("=" * 60)
    print("📊 技术分析演示 - 平安银行 (000001)")
    print("=" * 60)

    # 获取数据
    df = ak.stock_zh_a_hist(
        symbol="000001", period="daily", start_date="20240101", end_date="20250115"
    )

    # 应用技术指标
    df_with_indicators = apply_indicators(df)

    # 显示最近数据
    print("\n📈 最近5天技术指标:")
    print("-" * 60)

    cols = ["日期", "收盘", "MA5", "MA20", "RSI", "MACD", "K", "D"]
    print(df_with_indicators[cols].tail(5).to_string(index=False))

    # 当前信号判断
    latest = df_with_indicators.iloc[-1]
    print("\n" + "=" * 60)
    print("📊 当前技术信号判断:")
    print("-" * 60)

    # RSI 判断
    rsi = latest["RSI"]
    if rsi > 70:
        rsi_signal = "超买区域 ⚠️"
    elif rsi < 30:
        rsi_signal = "超卖区域 ✅"
    else:
        rsi_signal = "中性区域"
    print(f"RSI({rsi:.1f}): {rsi_signal}")

    # MACD 判断
    if latest["MACD"] > latest["MACD_Signal"]:
        macd_signal = "金叉/多头 ✅"
    else:
        macd_signal = "死叉/空头 ❌"
    print(f"MACD: {macd_signal}")

    # 均线判断
    if latest["收盘"] > latest["MA20"]:
        ma_signal = "价格在20日均线上方 ✅"
    else:
        ma_signal = "价格在20日均线下方 ❌"
    print(f"均线: {ma_signal}")

    # KDJ 判断
    if latest["J"] > 100:
        kdj_signal = "超买区域 ⚠️"
    elif latest["J"] < 0:
        kdj_signal = "超卖区域 ✅"
    else:
        kdj_signal = "中性区域"
    print(f"KDJ J值({latest['J']:.1f}): {kdj_signal}")


if __name__ == "__main__":
    demo()
