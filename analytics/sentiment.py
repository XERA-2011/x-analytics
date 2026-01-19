#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/15
Desc: 市场情绪分析工具
包含恐慌指数(VIX)、贪婪指数及资金情绪分析
"""

import akshare as ak
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

from .cache import cached


class SentimentAnalysis:
    """市场情绪分析类"""

    @staticmethod
    @cached("sentiment:fear_greed", ttl=300, stale_ttl=600)
    def calculate_fear_greed_custom(symbol: str = "sh000001", days: int = 14) -> dict:
        """
        计算自定义恐慌贪婪指数 (基于 RSI 和 Bias)
        
        Args:
            symbol: 指数代码，默认上证指数
            days: 计算周期
        
        Returns:
            dict: 恐慌贪婪评分 (0-100, 越低越恐慌)
        
        缓存: 300秒 TTL + 600秒 Stale
        """
        try:
            # 获取历史数据
            df = ak.stock_zh_index_daily(symbol=symbol)
            if df.empty:
                return {}
            
            close = df["close"]
            
            # 1. 计算 RSI (权重 60%)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=days).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=days).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # 2. 计算 Bias 乖离率 (权重 40%)
            ma20 = close.rolling(window=20).mean()
            bias = (close - ma20) / ma20 * 100
            current_bias = bias.iloc[-1]
            
            # 将 Bias 映射到 0-100 (假设 Bias -5 到 5 是正常区间)
            # Bias -5 -> 0, Bias 5 -> 100
            bias_score = (current_bias + 5) * 10
            bias_score = max(0, min(100, bias_score))
            
            # 综合评分
            final_score = current_rsi * 0.6 + bias_score * 0.4
            
            return {
                "score": final_score,
                "rsi": current_rsi,
                "bias": current_bias,
                "date": df["date"].iloc[-1]
            }
        except Exception as e:
            print(f"计算自定义恐慌指数失败: {e}")
            return {}

    @staticmethod
    @cached("sentiment:qvix", ttl=600, stale_ttl=1200)
    def get_qvix_indices() -> Dict[str, float]:
        """
        获取中国波指 (QVIX) - 类 VIX 指数
        反映市场对未来30天波动率的预期

        Returns:
            dict: 各主要指数的 QVIX 最新值
        
        缓存: 10分钟 TTL + 20分钟 Stale
        """
        indices = {
            "50ETF_QVIX": ak.index_option_50etf_qvix,
            "300ETF_QVIX": ak.index_option_300etf_qvix,
            "500ETF_QVIX": ak.index_option_500etf_qvix,
            "创业板_QVIX": ak.index_option_cyb_qvix,
        }

        results = {}
        for name, func in indices.items():
            try:
                df = func()
                if not df.empty:
                    # 通常最后一行为最新数据
                    # 检查列名，可能是 close 或 qvix
                    if "close" in df.columns:
                        val = df.iloc[-1]["close"]
                    elif "qvix" in df.columns:
                        val = df.iloc[-1]["qvix"]
                    else:
                        val = df.iloc[-1][0] # 盲猜第一列
                        
                    results[name] = float(val)
            except Exception as e:
                pass
        
        return results
    
    @staticmethod
    def analyze_qvix_trend(days: int = 5) -> pd.DataFrame:
        """
        分析 50ETF 期权波动率趋势
        
        Args:
            days: 分析最近几天
            
        Returns:
            pd.DataFrame: 最近几天的 QVIX 数据
        """
        try:
            df = ak.index_option_50etf_qvix()
            return df.tail(days)
        except Exception as e:
            print(f"获取 50ETF QVIX 趋势失败: {e}")
            return pd.DataFrame()

    @staticmethod
    @cached("sentiment:north_funds", ttl=300, stale_ttl=600)
    def get_north_funds_sentiment() -> Dict[str, Any]:
        """
        获取北向资金情绪 (外资态度)
        
        Returns:
            dict: 北向资金流向数据
        
        缓存: 5分钟 TTL + 10分钟 Stale
        """
        try:
            # 获取北向资金实时流向
            # 返回列: 交易日, 类型, 板块, 资金方向, 交易状态, 成交净买额, 资金净流入, ...
            df = ak.stock_hsgt_fund_flow_summary_em()
            
            if not df.empty:
                # 筛选北向资金 (通常资金方向="北向")
                # 如果没有"资金方向"列，则查看"类型"或"板块"
                # 这里假设列名如源码所示
                north_df = df[df['资金方向'] == '北向']
                
                if north_df.empty:
                    # 如果没有显式的北向汇总，可能需要加总“沪股通”和“深股通”
                    hgt = df[df['类型'].astype(str).str.contains('沪股通', na=False)]
                    sgt = df[df['类型'].astype(str).str.contains('深股通', na=False)]
                    
                    # 取最新日期
                    if not hgt.empty:
                        latest_date = hgt.iloc[0]['交易日']
                        # 确保是同一天的
                        net_inflow = 0
                        if not hgt.empty:
                            net_inflow += hgt.iloc[0]['资金净流入']
                        if not sgt.empty:
                            net_inflow += sgt.iloc[0]['资金净流入']
                            
                        # 单位修正: 源码里已经是 "资金净流入 = ... / 10000" (万元)? 
                        # 源码中: temp_df["资金净流入"] = temp_df["资金净流入"] / 10000 
                        # 所以单位是 '万元'。
                        # 我们需要转换成 '亿元' -> / 10000
                        val_billion = net_inflow / 10000
                        
                        return {
                            "日期": latest_date,
                            "净流入": f"{val_billion:.2f}亿",
                            "数值": val_billion
                        }

                else:
                    # 如果有直接的北向汇总
                    latest = north_df.iloc[0]
                    val = latest['资金净流入'] # 单位万元
                    val_billion = val / 10000
                    return {
                        "日期": latest['交易日'],
                        "净流入": f"{val_billion:.2f}亿",
                        "数值": val_billion
                    }

        except Exception as e:
            print(f"获取北向资金失败: {e}")
            # 备用方案：尝试 stock_hsgt_north_cash_em (如果有)
            try:
                 df_cash = ak.stock_hsgt_north_cash_em(symbol="北向资金")
                 if not df_cash.empty:
                      # 假设返回最近的数据
                      latest = df_cash.iloc[-1]
                      # 此接口格式未知，暂不深入
                      pass
            except:
                pass
                
        return {}


def analyze_sentiment_report():
    """生成市场情绪综合报告"""
    print("=" * 60)
    print("🎭 市场情绪与恐慌能级报告")
    print(f"📅 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 恐慌贪婪指数 (自定义)
    print("\n😨 恐慌与贪婪指数 (自定义算法)")
    print("-" * 60)
    print("基于 上证指数 的 RSI(60%) + Bias(40%) 计算")
    fg_data = SentimentAnalysis.calculate_fear_greed_custom()
    
    score = 50 # 默认中性
    if fg_data:
        score = fg_data['score']
        status = "中性"
        if score > 80: status = "极度贪婪 🔴"
        elif score > 60: status = "贪婪 🟠"
        elif score < 20: status = "极度恐慌 🟢"
        elif score < 40: status = "恐慌 🔵"
        
        print(f"日期: {fg_data.get('date', '-')}")
        print(f"综合评分: {score:.1f} / 100 ({status})")
        print(f"  - RSI指标: {fg_data.get('rsi', 0):.1f}")
        print(f"  - 乖离率Bias: {fg_data.get('bias', 0):.2f}%")
    else:
        print("计算失败，暂无数据")

    # 2. VIX 波动率分析
    print("\n📉 中国波指 (QVIX) - '恐慌指数'")
    print("-" * 60)
    print("提示: QVIX 越高代表市场预期未来波动越大（通常伴随恐慌下跌）")
    qvix_data = SentimentAnalysis.get_qvix_indices()
    if qvix_data:
        sorted_qvix = sorted(qvix_data.items(), key=lambda x: x[1], reverse=True)
        for name, value in sorted_qvix:
            print(f"{name:<15}: {value:.2f}")
    else:
        print("获取 QVIX 数据失败或暂无数据")

    # 3. 资金情绪
    print("\n💰 聪明钱情绪 (北向资金)")
    print("-" * 60)
    north_data = SentimentAnalysis.get_north_funds_sentiment()
    if north_data:
        flow = north_data.get("数值", 0)
        sentiment = "中性"
        if flow > 20: sentiment = "大幅流入 (积极看多) 🟢"
        elif flow > 0: sentiment = "小幅流入 (谨慎看多) 🟡"
        elif flow < -20: sentiment = "大幅流出 (恐慌抛售) 🔴"
        else: sentiment = "小幅流出 (谨慎减仓) 🟠"
        
        print(f"日期: {north_data.get('日期', '-')}")
        print(f"北向资金净流入: {north_data.get('净流入', '-')} ({sentiment})")
    else:
        print("暂无北向资金数据")
        
    # 4. 综合研判
    print("\n" + "=" * 60)
    print("💡 情绪研判摘要")
    print("-" * 60)
    
    signals = []
    
    # VIX 信号
    if "50ETF_QVIX" in qvix_data:
        vix = qvix_data["50ETF_QVIX"]
        if vix > 25:
            signals.append("⚠️ 波动率高企 (>25)，市场恐慌情绪明显，注意防守。")
        elif vix < 15:
            signals.append("💤 波动率低位 (<15)，市场情绪可能过于安逸。")
        else:
            signals.append("✅ 波动率处于正常区间。")
            
    # 评分信号
    if score < 20: 
        signals.append("💎 市场处于极度恐慌区间，这通常是底部特征。")
    elif score > 80:
        signals.append("🔥 市场处于极度贪婪区间，风险正在积聚。")
    
    # 北向信号
    if north_data and north_data.get("数值", 0) > 50:
        signals.append("💼 外资大幅扫货 (>50亿)，情绪显著提振。")
    elif north_data and north_data.get("数值", 0) < -50:
        signals.append("🏃 外资大幅出逃 (<-50亿)，需警惕风险。")

    if not signals:
        signals.append("市场情绪整体平稳，无显著极端信号。")

    for s in signals:
        print(f"- {s}")
    print("=" * 60)

if __name__ == "__main__":
    analyze_sentiment_report()
