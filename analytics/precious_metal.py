#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 贵金属分析模块
提供黄金、白银价格及金银比（Gold-Silver Ratio）
"""

import akshare as ak
from typing import Dict, Any

from .cache import cached


class PreciousMetalAnalysis:
    """贵金属分析类"""

    # COMEX 合约代码
    GOLD_CODE = "GC00Y"  # COMEX黄金主力
    SILVER_CODE = "SI00Y"  # COMEX白银主力

    @staticmethod
    @cached("precious:gold_silver", ttl=300, stale_ttl=600)
    def get_gold_silver_ratio() -> Dict[str, Any]:
        """
        获取金银比及价格

        Returns:
            dict: 包含黄金价格、白银价格、金银比等信息

        缓存: 5分钟 TTL + 10分钟 Stale
        """
        try:
            df = ak.futures_global_spot_em()
            if df.empty:
                return {}

            # 获取黄金数据
            gold_row = df[df["代码"] == PreciousMetalAnalysis.GOLD_CODE]
            silver_row = df[df["代码"] == PreciousMetalAnalysis.SILVER_CODE]

            if gold_row.empty or silver_row.empty:
                # 尝试备用代码
                gold_row = df[df["代码"].str.contains("GC26", na=False)].head(1)
                silver_row = df[df["代码"].str.contains("SI26", na=False)].head(1)

            if gold_row.empty or silver_row.empty:
                return {"error": "无法获取黄金或白银数据"}

            gold = gold_row.iloc[0]
            silver = silver_row.iloc[0]

            gold_price = float(gold["最新价"])
            silver_price = float(silver["最新价"])

            # 计算金银比
            ratio = gold_price / silver_price if silver_price > 0 else 0

            return {
                "gold": {
                    "name": "COMEX黄金",
                    "price": gold_price,
                    "change": float(gold["涨跌额"]) if gold["涨跌额"] else 0,
                    "change_pct": float(gold["涨跌幅"]) if gold["涨跌幅"] else 0,
                    "unit": "美元/盎司",
                },
                "silver": {
                    "name": "COMEX白银",
                    "price": silver_price,
                    "change": float(silver["涨跌额"]) if silver["涨跌额"] else 0,
                    "change_pct": float(silver["涨跌幅"]) if silver["涨跌幅"] else 0,
                    "unit": "美元/盎司",
                },
                "ratio": round(ratio, 2),
                "ratio_interpretation": PreciousMetalAnalysis._interpret_ratio(ratio),
            }
        except Exception as e:
            print(f"获取金银比失败: {e}")
            return {"error": str(e)}

    @staticmethod
    def _interpret_ratio(ratio: float) -> str:
        """
        解读金银比

        历史参考:
        - < 40: 白银相对昂贵 (历史低位)
        - 40-60: 正常区间
        - 60-80: 白银相对便宜
        - > 80: 极端值，白银可能被低估
        """
        if ratio < 40:
            return "白银相对昂贵"
        elif ratio < 60:
            return "正常区间"
        elif ratio < 80:
            return "白银相对便宜"
        else:
            return "白银可能被低估"


if __name__ == "__main__":
    # 测试
    data = PreciousMetalAnalysis.get_gold_silver_ratio()
    if "error" not in data:
        print("=== 金银比分析 ===")
        print(
            f"🥇 黄金: ${data['gold']['price']:.2f} ({data['gold']['change_pct']:+.2f}%)"
        )
        print(
            f"🥈 白银: ${data['silver']['price']:.2f} ({data['silver']['change_pct']:+.2f}%)"
        )
        print(f"📊 金银比: {data['ratio']:.2f} ({data['ratio_interpretation']})")
    else:
        print(f"错误: {data['error']}")
