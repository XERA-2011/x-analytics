#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/21
Desc: 主流金属价格 (COMEX 期货)
"""

import akshare as ak
from typing import List, Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger


class MetalSpotPrice:
    """主流金属价格分析 (COMEX)"""

    # 主流金属合约代码 (COMEX/NYMEX)
    METALS = [
        {"code": "GC00Y", "name": "黄金", "unit": "USD/oz"},
        {"code": "SI00Y", "name": "白银", "unit": "USD/oz"},
        {"code": "HG00Y", "name": "铜", "unit": "USD/lb"},
        {"code": "PL00Y", "name": "铂金", "unit": "USD/oz"},
        {"code": "PA00Y", "name": "钯金", "unit": "USD/oz"},
    ]

    @staticmethod
    @cached(
        "metals:spot_price", ttl=settings.CACHE_TTL.get("metals", 300), stale_ttl=settings.CACHE_TTL.get("metals", 300) * settings.STALE_TTL_RATIO
    )
    def get_spot_prices() -> List[Dict[str, Any]]:
        """
        获取主流金属价格 (COMEX 期货)
        """
        results = []
        try:
            # 使用带重试的 API 调用
            df = akshare_call_with_retry(ak.futures_global_spot_em)

            if df.empty:
                logger.info("❌ 无法获取期货数据")
                return []

            for metal in MetalSpotPrice.METALS:
                try:
                    code = metal["code"]
                    name = metal["name"]
                    unit = metal["unit"]

                    # 查找合约
                    row = df[df["代码"] == code]

                    # 备用: 尝试模糊匹配
                    if row.empty:
                        prefix = code[:2]  # GC, SI, HG, PL, PA
                        row = df[df["代码"].str.startswith(prefix, na=False)].head(1)

                    if row.empty:
                        logger.warning(f" 未找到 {name} ({code})")
                        continue

                    data = row.iloc[0]
                    price = safe_float(data["最新价"])
                    change_pct = safe_float(data["涨跌幅"])

                    results.append({
                        "name": name,
                        "code": code,
                        "price": round(price, 2),
                        "change_pct": round(change_pct, 2),
                        "unit": unit,
                        "source": "COMEX",
                    })

                except Exception as e_inner:
                    logger.warning(f"获取 {metal['name']} 失败: {e_inner}")

            return results

        except Exception as e:
            logger.error(f" 获取金属价格失败: {e}")
            return []

