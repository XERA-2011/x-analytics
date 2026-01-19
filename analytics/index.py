#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/15
Desc: 指数分析工具
"""

import akshare as ak
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta


# 常用指数代码
MAJOR_INDICES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指", 
    "sz399006": "创业板指",
    "sh000300": "沪深300",
    "sh000016": "上证50",
    "sh000905": "中证500",
    "sh000688": "科创50",
}


from .cache import cached


class IndexAnalysis:
    """指数分析类"""
    
    def __init__(self, symbol: str = "sh000001"):
        """
        初始化指数分析对象
        
        Args:
            symbol: 指数代码，如 "sh000001" (上证指数)
        """
        self.symbol = symbol
        self.name = MAJOR_INDICES.get(symbol, "未知指数")
        self._hist_data: Optional[pd.DataFrame] = None
    
    def get_history(self) -> pd.DataFrame:
        """
        获取指数历史数据
        
        Returns:
            pd.DataFrame: 历史行情数据
        """
        self._hist_data = ak.stock_zh_index_daily(symbol=self.symbol)
        return self._hist_data
    
    def get_recent_performance(self, days: int = 30) -> pd.DataFrame:
        """
        获取近期表现
        
        Args:
            days: 天数
            
        Returns:
            pd.DataFrame: 近期行情数据
        """
        if self._hist_data is None:
            self.get_history()
        return self._hist_data.tail(days)
    
    def calculate_returns(self) -> Dict[str, str]:
        """
        计算各周期收益率
        
        Returns:
            dict: 收益率字典
        """
        if self._hist_data is None:
            self.get_history()
            
        df = self._hist_data.copy()
        latest = df["close"].iloc[-1]
        
        periods = {
            "1日": 1,
            "5日": 5,
            "20日": 20,
            "60日": 60,
            "120日": 120,
            "250日": 250,
        }
        
        results = {}
        for name, p in periods.items():
            if len(df) > p:
                prev = df["close"].iloc[-p-1]
                ret = (latest / prev - 1) * 100
                results[name] = f"{ret:+.2f}%"
        
        return results
    
    def calculate_stats(self) -> Dict[str, any]:
        """
        计算统计指标
        
        Returns:
            dict: 统计指标
        """
        if self._hist_data is None:
            self.get_history()
            
        df = self._hist_data.copy()
        
        # 计算年度数据
        current_year = datetime.now().year
        year_data = df[df["date"].str.startswith(str(current_year))]
        
        stats = {
            "最新收盘": df["close"].iloc[-1],
            "年内最高": year_data["high"].max() if len(year_data) > 0 else None,
            "年内最低": year_data["low"].min() if len(year_data) > 0 else None,
            "历史最高": df["high"].max(),
            "历史最低": df["low"].min(),
            "数据天数": len(df),
        }
        
        return stats
    
    def analyze(self) -> dict:
        """
        综合分析报告
        
        Returns:
            dict: 分析报告
        """
        report = {
            "指数代码": self.symbol,
            "指数名称": self.name,
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        try:
            stats = self.calculate_stats()
            report.update(stats)
            
            returns = self.calculate_returns()
            report["收益率"] = returns
        except Exception as e:
            report["错误"] = str(e)
        
        return report
    
    @staticmethod
    @cached("index:compare", ttl=60, stale_ttl=120)
    def compare_indices() -> pd.DataFrame:
        """
        对比主要指数表现 (使用实时行情)
        
        Returns:
            pd.DataFrame: 对比结果
        """
        try:
            # 获取实时行情
            df = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
            
            # 筛选我们关注的指数
            target_indices = ["上证指数", "深证成指", "创业板指", "沪深300", "上证50", "中证500", "科创50"]
            
            # 过滤并保留需要的列
            result_df = df[df["名称"].isin(target_indices)][["名称", "最新价", "涨跌幅"]]
            result_df.columns = ["指数名称", "最新点位", "1日涨跌"]
            
            # 转换格式: 1日涨跌改为百分比字符串
            result_df["1日涨跌"] = result_df["1日涨跌"].apply(lambda x: f"{x:+.2f}%")
            
            return result_df.to_dict(orient="records")
            
        except Exception as e:
            print(f"获取指数对比失败: {e}")
            return []


def demo():
    """演示函数"""
    print("=" * 60)
    print("📉 指数分析演示")
    print("=" * 60)
    
    # 单个指数分析
    analyzer = IndexAnalysis("sh000001")
    report = analyzer.analyze()
    
    print(f"\n📊 {report['指数名称']} 分析报告")
    print("-" * 40)
    print(f"最新点位: {report.get('最新收盘', '-')}")
    print(f"年内最高: {report.get('年内最高', '-')}")
    print(f"年内最低: {report.get('年内最低', '-')}")
    
    if "收益率" in report:
        print("\n📈 收益率:")
        for period, ret in report["收益率"].items():
            print(f"  {period}: {ret}")
    
    # 主要指数对比
    print("\n" + "=" * 60)
    print("📊 主要指数对比")
    print("=" * 60)
    
    compare_df = IndexAnalysis.compare_indices()
    print(compare_df.to_string(index=False))


if __name__ == "__main__":
    demo()
