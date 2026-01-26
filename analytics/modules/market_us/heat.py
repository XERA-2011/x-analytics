#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 美国市场板块热度
"""

import akshare as ak
from typing import List, Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import akshare_call_with_retry
from ...core.logger import logger


class USMarketHeat:
    """美国市场板块热度分析"""

    @staticmethod
    @cached(
        "market_us:sector_performance",
        ttl=settings.CACHE_TTL.get("market_heat", 3600),
        stale_ttl=settings.CACHE_TTL.get("market_heat", 3600) * settings.STALE_TTL_RATIO,
    )
    def get_sector_performance() -> List[Dict[str, Any]]:
        """
        获取美国市场板块表现 (基于 SPDR Sector ETFs)
        """
        sectors = [
            {"symbol": "XLK", "name": "科技", "en_name": "Technology"},
            {"symbol": "XLF", "name": "金融", "en_name": "Financials"},
            {"symbol": "XLV", "name": "医疗", "en_name": "Health Care"},
            {"symbol": "XLY", "name": "可选消费", "en_name": "Cons. Disc."},
            {"symbol": "XLP", "name": "必选消费", "en_name": "Cons. Stap."},
            {"symbol": "XLE", "name": "能源", "en_name": "Energy"},
            {"symbol": "XLI", "name": "工业", "en_name": "Industrials"},
            {"symbol": "XLB", "name": "材料", "en_name": "Materials"},
            {"symbol": "XLRE", "name": "房地产", "en_name": "Real Estate"},
            {"symbol": "XLU", "name": "公用事业", "en_name": "Utilities"},
            {"symbol": "XLC", "name": "通讯", "en_name": "Comm. Svcs"},
        ]

        results = []

        try:
            for item in sectors:
                try:
                    # 获取单只美国市场股票历史数据 (日频)
                    df = akshare_call_with_retry(ak.stock_us_daily, symbol=item["symbol"], adjust="qfq")
                    if not df.empty:
                        latest = df.iloc[-1]
                        change_pct = 0.0
                        price = float(latest["close"])

                        if len(df) >= 2:
                            prev_close = float(df.iloc[-2]["close"])
                            if prev_close > 0:
                                change_pct = (price - prev_close) / prev_close * 100

                        results.append(
                            {
                                "name": item["name"],
                                "symbol": item["symbol"],
                                "change_pct": round(change_pct, 2),
                                "price": price,
                                "volume": float(latest["volume"]),
                            }
                        )
                except Exception as e_inner:
                    logger.warning(f"获取 {item['symbol']} 失败: {e_inner}")

            results.sort(key=lambda x: x.get("change_pct", 0.0), reverse=True)  # type: ignore
            return results

        except Exception as e:
            logger.error(f"获取美国市场板块数据失败: {e}")
            return []
