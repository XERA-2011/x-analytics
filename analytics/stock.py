#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/15
Desc: A股股票分析工具
"""

import akshare as ak
import pandas as pd
from typing import Optional, List, Tuple
from datetime import datetime, timedelta

from .cache import cached


class StockAnalysis:
    """A股股票分析类"""
    
    def __init__(self, symbol: str):
        """
        初始化股票分析对象
        
        Args:
            symbol: 股票代码，如 "000001" (平安银行)
        """
        self.symbol = symbol
        self._hist_data: Optional[pd.DataFrame] = None
        self._realtime_data: Optional[pd.Series] = None
    
    def get_history(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            start_date: 开始日期，格式 "YYYYMMDD"，默认一年前
            end_date: 结束日期，格式 "YYYYMMDD"，默认今天
            period: 周期，可选 "daily", "weekly", "monthly"
            adjust: 复权类型，"" 不复权，"qfq" 前复权，"hfq" 后复权
            
        Returns:
            pd.DataFrame: 历史行情数据
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
            
        self._hist_data = ak.stock_zh_a_hist(
            symbol=self.symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )
        return self._hist_data
    
    def get_realtime(self) -> pd.Series:
        """
        获取实时行情
        
        Returns:
            pd.Series: 该股票的实时行情
        """
        df = ak.stock_zh_a_spot_em()
        self._realtime_data = df[df["代码"] == self.symbol].iloc[0]
        return self._realtime_data
    
    def calculate_returns(self, periods: List[int] = [1, 5, 20, 60]) -> pd.DataFrame:
        """
        计算不同周期的收益率
        
        Args:
            periods: 周期列表，默认 [1, 5, 20, 60] 代表日、周、月、季
            
        Returns:
            pd.DataFrame: 各周期收益率
        """
        if self._hist_data is None:
            self.get_history()
            
        df = self._hist_data.copy()
        df = df.set_index("日期")
        
        results = {}
        for p in periods:
            if len(df) > p:
                ret = (df["收盘"].iloc[-1] / df["收盘"].iloc[-p-1] - 1) * 100
                results[f"{p}日收益率"] = f"{ret:.2f}%"
        
        return pd.DataFrame([results])
    
    def calculate_ma(self, windows: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
        """
        计算移动平均线
        
        Args:
            windows: 均线周期列表
            
        Returns:
            pd.DataFrame: 带均线的数据
        """
        if self._hist_data is None:
            self.get_history()
            
        df = self._hist_data.copy()
        for w in windows:
            df[f"MA{w}"] = df["收盘"].rolling(window=w).mean()
        
        return df
    
    def calculate_volatility(self, window: int = 20) -> float:
        """
        计算波动率 (标准差年化)
        
        Args:
            window: 计算周期
            
        Returns:
            float: 年化波动率百分比
        """
        if self._hist_data is None:
            self.get_history()
            
        returns = self._hist_data["收盘"].pct_change().dropna()
        volatility = returns.tail(window).std() * (252 ** 0.5) * 100
        return round(volatility, 2)
    
    def get_financial_summary(self) -> pd.DataFrame:
        """
        获取财务摘要
        
        Returns:
            pd.DataFrame: 财务数据摘要
        """
        try:
            # 获取个股指标
            df = ak.stock_individual_info_em(symbol=self.symbol)
            return df
        except Exception as e:
            print(f"获取财务数据失败: {e}")
            return pd.DataFrame()
    
    def analyze(self) -> dict:
        """
        综合分析报告
        
        Returns:
            dict: 分析报告字典
        """
        report = {
            "股票代码": self.symbol,
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # 获取实时数据
        try:
            rt = self.get_realtime()
            report["股票名称"] = rt["名称"]
            report["最新价"] = rt["最新价"]
            report["涨跌幅"] = f"{rt['涨跌幅']}%"
            report["成交额"] = f"{rt['成交额']/1e8:.2f}亿"
        except Exception as e:
            report["实时数据"] = f"获取失败: {e}"
        
        # 获取历史数据分析
        try:
            self.get_history()
            report["波动率(20日年化)"] = f"{self.calculate_volatility()}%"
            
            returns = self.calculate_returns()
            for col in returns.columns:
                report[col] = returns[col].iloc[0]
        except Exception as e:
            report["历史分析"] = f"获取失败: {e}"
        
        return report
    
    @staticmethod
    @cached("stock:spot_data", ttl=30, stale_ttl=60)
    def _get_spot_data() -> list:
        """
        获取 A 股实时行情数据（带缓存）
        
        缓存: 30秒 TTL + 60秒 Stale
        """
        try:
            df = ak.stock_zh_a_spot_em()
            return df[["代码", "名称", "最新价", "涨跌幅"]].to_dict(orient="records")
        except Exception as e:
            print(f"获取 A 股行情失败: {e}")
            return []
    
    @staticmethod
    def search(keyword: str) -> list:
        """
        搜索 A 股股票 (代码或名称)
        
        Args:
            keyword: 搜索关键词（支持代码或名称模糊匹配）
            
        Returns:
            list: 匹配的股票列表（最多 10 条）
        """
        try:
            # 从缓存获取 A 股列表
            data = StockAnalysis._get_spot_data()
            if not data:
                return []
            
            # 转换为 DataFrame 进行筛选
            df = pd.DataFrame(data)
            mask = df["名称"].str.contains(keyword, na=False) | df["代码"].str.contains(keyword, na=False)
            return df[mask].head(10).to_dict(orient="records")
        except Exception as e:
            print(f"搜索失败: {e}")
            return []


def demo():
    """演示函数"""
    print("=" * 60)
    print("📈 股票分析演示 - 平安银行 (000001)")
    print("=" * 60)
    
    analyzer = StockAnalysis("000001")
    
    # 综合分析
    report = analyzer.analyze()
    for key, value in report.items():
        print(f"{key}: {value}")
    
    print("\n" + "=" * 60)
    print("📊 均线数据 (最近5天)")
    print("=" * 60)
    ma_df = analyzer.calculate_ma()
    print(ma_df[["日期", "收盘", "MA5", "MA10", "MA20"]].tail(5).to_string(index=False))


if __name__ == "__main__":
    demo()
