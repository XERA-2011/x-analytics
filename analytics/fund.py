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
import requests
from akshare.utils import demjson
from akshare.utils.cons import headers as default_headers
import random

# -----------------------------------------------------------------------------
# Monkey Patch: 增强版 AkShare 基金排行获取
# 原版可能因 headers 简单而被云服务器屏蔽
# -----------------------------------------------------------------------------
def _patched_fund_open_fund_daily_em() -> pd.DataFrame:
    """
    (Patched) 东方财富网-天天基金网-基金数据-开放式基金净值
    增强了 Header 伪装
    """
    url = "https://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx"
    
    # 构建更真实的随机 Header
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Referer": "https://fund.eastmoney.com/fund.html",
        "Host": "fund.eastmoney.com",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive"
    }
    
    params = {
        "t": "1",
        "lx": "1",
        "letter": "",
        "gsid": "",
        "text": "",
        "sort": "zdf,desc",
        "page": "1,50000",
        "dt": str(int(datetime.now().timestamp() * 1000)),
        "atfc": "",
        "onlySale": "0",
    }
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        text_data = res.text
        
        # 处理返回数据
        # var db={...}
        json_str = text_data.strip()
        if json_str.startswith("var db="):
            json_str = json_str[7:]
            
        data_json = demjson.decode(json_str)
        temp_df = pd.DataFrame(data_json["datas"])
        show_day = data_json["showday"]
        
        # 映射列名
        temp_df.columns = [
            "基金代码", "基金简称", "-",
            f"{show_day[0]}-单位净值", f"{show_day[0]}-累计净值",
            f"{show_day[1]}-单位净值", f"{show_day[1]}-累计净值",
            "日增长值", "日增长率",
            "申购状态", "赎回状态",
            "-", "-", "-", "-", "-", "-",
            "手续费", "-", "-", "-"
        ]
        
        # 筛选必要列
        data_df = temp_df[[
            "基金代码", "基金简称", "日增长率", 
            "申购状态", "赎回状态", "手续费"
        ]]
        return data_df
        
    except Exception as e:
        print(f"[Patch Error] 获取基金排行异常: {e}")
        # 如果 Patch 失败，尝试回退或是直接返回空 DF
        return pd.DataFrame()

# 应用 Monkey Patch
ak.fund_open_fund_daily_em = _patched_fund_open_fund_daily_em


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
    @cached("fund:top", ttl=43200, stale_ttl=43200)
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
