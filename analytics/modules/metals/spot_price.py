#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 有色金属现货价格
"""

import akshare as ak
from typing import List, Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float


class MetalSpotPrice:
    """金属现货价格分析"""

    @staticmethod
    @cached(
        "metals:spot_price", ttl=settings.CACHE_TTL.get("metals", 3600), stale_ttl=7200
    )
    def get_spot_prices() -> List[Dict[str, Any]]:
        """
        获取金属现货价格 (以上海黄金交易所 SGE 为主)
        """
        results = []
        try:
            # SGE 黄金/白银 T+D
            # 接口: ak.spot_quotations_sge(symbol=...)
            targets = [
                {"symbol": "Au99.99", "name": "黄金9999", "unit": "元/克"},
                {"symbol": "Ag(T+D)", "name": "白银T+D", "unit": "元/千克"},
                {"symbol": "Au(T+D)", "name": "黄金T+D", "unit": "元/克"},
                {"symbol": "mAu(T+D)", "name": "迷你黄金T+D", "unit": "元/克"},
            ]

            for item in targets:
                try:
                    symbol = item["symbol"]
                    name = item["name"]
                    unit = item["unit"]

                    df = ak.spot_quotations_sge(symbol=symbol)

                    if not df.empty:
                        # 获取最新一行
                        latest = df.iloc[-1]
                        current_price = safe_float(latest["现价"])

                        # 估算涨跌幅 (因接口无直接涨跌幅，尝试用第一笔数据作为参考开盘价)
                        # 注意：这只是日内涨跌幅的近似
                        change_pct = 0.0
                        if len(df) > 0:
                            first = df.iloc[0]
                            open_price = safe_float(first["现价"])
                            if open_price > 0:
                                change_pct = (
                                    (current_price - open_price) / open_price * 100
                                )

                        results.append(
                            {
                                "name": name,
                                "symbol": symbol,
                                "price": current_price,
                                "change_pct": round(change_pct, 2),
                                "unit": unit,
                                "source": "SGE",
                                "update_time": str(latest.get("更新时间", "")),
                            }
                        )
                except Exception as e_inner:
                    print(f"获取 {item['symbol']} 失败: {e_inner}")

            return results

        except Exception as e:
            print(f"获取金属现货价格失败: {e}")
            return []
