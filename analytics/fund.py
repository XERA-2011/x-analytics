#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/15
Desc: 基金分析工具
"""

import akshare as ak
import pandas as pd
from typing import Optional, List
from datetime import datetime


from .cache import cached


class FundAnalysis:
    """基金分析类"""
    
    def __init__(self, fund_code: str):
        """
        初始化基金分析对象
        
        Args:
            fund_code: 基金代码，如 "000001" (华夏成长)
        """
        self.fund_code = fund_code
        self._info: Optional[pd.DataFrame] = None
        self._nav_data: Optional[pd.DataFrame] = None
    
    def get_info(self) -> pd.DataFrame:
        """
        获取基金基本信息
        
        Returns:
            pd.DataFrame: 基金信息
        """
        try:
            self._info = ak.fund_individual_basic_info_xq(symbol=self.fund_code)
            return self._info
        except Exception as e:
            print(f"获取基金信息失败: {e}")
            return pd.DataFrame()
    
    def get_nav_history(self) -> pd.DataFrame:
        """
        获取基金净值历史
        
        Returns:
            pd.DataFrame: 净值历史数据
        """
        try:
            self._nav_data = ak.fund_open_fund_info_em(
                symbol=self.fund_code, 
                indicator="单位净值走势"
            )
            return self._nav_data
        except Exception as e:
            print(f"获取净值历史失败: {e}")
            return pd.DataFrame()
    
    def calculate_returns(self) -> dict:
        """
        计算基金收益率
        
        Returns:
            dict: 各周期收益率
        """
        if self._nav_data is None or len(self._nav_data) == 0:
            self.get_nav_history()
            
        if self._nav_data is None or len(self._nav_data) == 0:
            return {}
            
        df = self._nav_data.copy()
        
        # 获取净值列名（可能有不同的列名）
        nav_col = None
        for col in df.columns:
            if "净值" in col or "nav" in col.lower():
                nav_col = col
                break
        
        if nav_col is None and len(df.columns) >= 2:
            nav_col = df.columns[1]  # 假设第二列是净值
            
        if nav_col is None:
            return {"错误": "无法识别净值列"}
        
        latest = float(df[nav_col].iloc[-1])
        
        periods = {
            "近1周": 5,
            "近1月": 20,
            "近3月": 60,
            "近6月": 120,
            "近1年": 250,
        }
        
        results = {}
        for name, p in periods.items():
            if len(df) > p:
                prev = float(df[nav_col].iloc[-p-1])
                ret = (latest / prev - 1) * 100
                results[name] = f"{ret:+.2f}%"
        
        return results
    
    def analyze(self) -> dict:
        """
        综合分析报告
        
        Returns:
            dict: 分析报告
        """
        report = {
            "基金代码": self.fund_code,
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # 获取基金信息
        try:
            info = self.get_info()
            if len(info) > 0:
                for _, row in info.iterrows():
                    if "item" in info.columns and "value" in info.columns:
                        report[row["item"]] = row["value"]
        except Exception as e:
            report["基本信息"] = f"获取失败: {e}"
        
        # 获取收益率
        try:
            returns = self.calculate_returns()
            if returns:
                report["收益率"] = returns
        except Exception as e:
            report["收益率分析"] = f"获取失败: {e}"
        
        return report
    
    @staticmethod
    @cached("fund:top", ttl=3600, stale_ttl=7200)
    def get_top_funds(indicator: str = "近1年", top_n: int = 10) -> pd.DataFrame:
        """
        获取热门基金排行
        
        Args:
            indicator: 排名指标，可选 "日增长率" 等
            top_n: 返回数量
            
        Returns:
            pd.DataFrame: 排行榜
        """
        try:
            df = ak.fund_open_fund_daily_em()
            
            # 尝试按日增长率排序
            if "日增长率" in df.columns:
                # 转换为数字，不仅为了排序，也为了过滤无效数据 (如货币基金可能为空)
                df["日增长率_num"] = pd.to_numeric(df["日增长率"], errors="coerce")
                
                # 关键修复：过滤掉 NaN (即原数据为空或非数字的记录)
                df = df.dropna(subset=["日增长率_num"])
                
                df = df.sort_values("日增长率_num", ascending=False)
                
            return df.head(top_n).to_dict(orient="records")
        except Exception as e:
            print(f"获取基金排行失败: {e}")
            return []
    
    @staticmethod
    def search_fund(keyword: str) -> pd.DataFrame:
        """
        搜索基金
        
        Args:
            keyword: 关键词（基金名称或代码）
            
        Returns:
            pd.DataFrame: 匹配的基金列表
        """
        try:
            df = ak.fund_open_fund_daily_em()
            
            # 按代码或名称筛选
            mask = (
                df["基金代码"].str.contains(keyword, na=False) | 
                df["基金简称"].str.contains(keyword, na=False)
            )
            return df[mask]
        except Exception as e:
            print(f"搜索基金失败: {e}")
            return pd.DataFrame()


def demo():
    """演示函数"""
    print("=" * 60)
    print("💰 基金分析演示")
    print("=" * 60)
    
    # 获取今日涨幅榜
    print("\n📈 今日基金涨幅榜 Top 5")
    print("-" * 60)
    
    # get_top_funds 返回的是 list[dict]
    top_funds = FundAnalysis.get_top_funds(top_n=5)
    
    if len(top_funds) > 0:
        print(f"{'基金代码':<10} {'基金简称':<20} {'日增长率':<10}")
        print("-" * 60)
        for item in top_funds:
            code = item.get("基金代码", "")
            name = item.get("基金简称", "")
            # 截断过长名称
            if len(name) > 15:
                name = name[:13] + ".."
            
            rate = item.get("日增长率", "")
            print(f"{code:<10} {name:<20} {str(rate):<10}")
    
    # 搜索示例
    print("\n🔍 搜索包含 '沪深300' 的基金")
    print("-" * 60)
    
    results = FundAnalysis.search_fund("沪深300")
    if len(results) > 0:
        display_cols = ["基金代码", "基金简称", "日增长率"]
        available_cols = [c for c in display_cols if c in results.columns]
        print(results[available_cols].head(5).to_string(index=False))


if __name__ == "__main__":
    demo()
