#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 全球主要市场指数分析
提供日经225、纳斯达克、标普500、恒生指数、恒生科技、道琼斯、KOSPI等指数行情
"""

import akshare as ak
from typing import List, Dict, Any

from .cache import cached


# 目标指数配置
# name: 用于匹配 index_global_spot_em 的名称
# code: 用于港股指数 (stock_hk_index_spot_em)
# flag: 国旗 emoji
TARGET_INDICES = [
    {"name": "上证指数", "flag": "🇨🇳", "region": "中国"},
    {"name": "沪深300", "flag": "🇨🇳", "region": "中国"},
    {"name": "恒生指数", "flag": "🇭🇰", "region": "香港"},
    {"code": "HSTECH", "display_name": "恒生科技", "flag": "🇭🇰", "region": "香港"},
    {"name": "纳斯达克", "flag": "🇺🇸", "region": "美国"},
    {"name": "标普500", "flag": "🇺🇸", "region": "美国"},
    {"name": "道琼斯", "flag": "🇺🇸", "region": "美国"},
    {"name": "日经225", "flag": "🇯🇵", "region": "日本"},
    {"name": "韩国KOSPI", "flag": "🇰🇷", "region": "韩国"},
]


class GlobalIndexAnalysis:
    """全球主要市场指数分析类"""

    @staticmethod
    @cached("global:indices", ttl=300, stale_ttl=600)
    def get_global_indices() -> List[Dict[str, Any]]:
        """
        获取全球主要市场指数行情

        Returns:
            List[Dict]: 指数列表，每个包含:
                - name: 指数名称
                - flag: 国旗 emoji
                - region: 地区
                - price: 最新价
                - change: 涨跌额
                - change_pct: 涨跌幅
                - update_time: 更新时间

        缓存: 5分钟 TTL + 10分钟 Stale
        """
        results: List[Dict[str, Any]] = []

        # 1. 获取全球指数 (index_global_spot_em)
        try:
            df_global = ak.index_global_spot_em()
            if not df_global.empty:
                for target in TARGET_INDICES:
                    if "name" in target:
                        # 按名称匹配
                        match = df_global[df_global["名称"] == target["name"]]
                        if not match.empty:
                            row = match.iloc[0]
                            results.append({
                                "name": target["name"],
                                "flag": target["flag"],
                                "region": target["region"],
                                "price": float(row["最新价"]),
                                "change": float(row["涨跌额"]),
                                "change_pct": float(row["涨跌幅"]),
                                "update_time": str(row.get("最新行情时间", "")),
                            })
        except Exception as e:
            print(f"获取全球指数失败: {e}")

        # 2. 获取港股指数 (恒生科技 HSTECH)
        try:
            df_hk = ak.stock_hk_index_spot_em()
            if not df_hk.empty:
                for target in TARGET_INDICES:
                    if "code" in target:
                        match = df_hk[df_hk["代码"] == target["code"]]
                        if not match.empty:
                            row = match.iloc[0]
                            results.append({
                                "name": target["display_name"],
                                "flag": target["flag"],
                                "region": target["region"],
                                "price": float(row["最新价"]),
                                "change": float(row["涨跌额"]),
                                "change_pct": float(row["涨跌幅"]),
                                "update_time": "",  # 港股指数无时间字段
                            })
        except Exception as e:
            print(f"获取港股指数失败: {e}")

        # 3. 按照 TARGET_INDICES 的顺序排序
        order_map = {}
        for i, target in enumerate(TARGET_INDICES):
            key = target.get("name") or target.get("display_name")
            order_map[key] = i

        results.sort(key=lambda x: order_map.get(x["name"], 999))

        return results


if __name__ == "__main__":
    # 测试
    indices = GlobalIndexAnalysis.get_global_indices()
    print("=== 全球主要市场指数 ===")
    for idx in indices:
        sign = "+" if idx["change"] >= 0 else ""
        color = "🟢" if idx["change"] >= 0 else "🔴"
        print(
            f"{idx['flag']} {idx['name']}: "
            f"{idx['price']:.2f} ({sign}{idx['change_pct']:.2f}%) {color}"
        )
