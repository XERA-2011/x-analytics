#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/21
Desc: 主流金属价格 (国际现货 + COMEX 期货主力)
"""

import re
import requests
import akshare as ak
from typing import List, Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, akshare_call_with_retry
from ...core.logger import logger


class MetalSpotPrice:
    """主流金属价格分析 (国际现货 + COMEX 期货主力)"""

    # 主流期货金属合约配置 (COMEX/NYMEX)
    FUTURES_METALS = [
        {
            "code": "GC00Y",
            "name": "COMEX 黄金",
            "unit": "USD/oz",
            "category": "futures",
            "badge": "期货主力",
            "desc": "含远月升水 · 主力连续",
            "source": "COMEX",
        },
        {
            "code": "SI00Y",
            "name": "COMEX 白银",
            "unit": "USD/oz",
            "category": "futures",
            "badge": "期货主力",
            "desc": "COMEX主力连续",
            "source": "COMEX",
        },
        {
            "code": "HG00Y",
            "name": "COMEX 铜",
            "unit": "USD/lb",
            "category": "futures",
            "badge": "期货主力",
            "desc": "COMEX主力连续",
            "source": "COMEX",
        },
        {
            "code": "PL00Y",
            "name": "NYMEX 铂金",
            "unit": "USD/oz",
            "category": "futures",
            "badge": "期货",
            "desc": "NYMEX连续",
            "source": "NYMEX",
        },
        {
            "code": "PA00Y",
            "name": "NYMEX 钯金",
            "unit": "USD/oz",
            "category": "futures",
            "badge": "期货",
            "desc": "NYMEX连续",
            "source": "NYMEX",
        },
    ]

    @staticmethod
    def _fetch_sina_spot_metals() -> List[Dict[str, Any]]:
        """获取新浪国际现货金属即时行情 (伦敦金 XAU, 伦敦银 XAG)"""
        results = []
        try:
            url = "https://hq.sinajs.cn/list=hf_XAU,hf_XAG"
            headers = {"Referer": "https://finance.sina.com.cn"}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                for line in r.text.strip().split("\n"):
                    m = re.match(r'var hq_str_([a-zA-Z0-9_]+)="(.*)";', line)
                    if not m:
                        continue
                    code, content = m.group(1), m.group(2)
                    parts = content.split(",")
                    if len(parts) >= 14:
                        price = safe_float(parts[0])
                        pre_close = safe_float(parts[7]) or safe_float(parts[1])
                        if price and price > 0:
                            change_pct = (
                                round((price - pre_close) / pre_close * 100, 2)
                                if (pre_close and pre_close > 0)
                                else 0.0
                            )
                            if code == "hf_XAU":
                                results.append({
                                    "name": "现货黄金 (伦敦金)",
                                    "code": "XAU",
                                    "price": round(price, 2),
                                    "change_pct": change_pct,
                                    "unit": "USD/oz",
                                    "source": "伦敦金现",
                                    "category": "spot",
                                    "badge": "现货",
                                    "desc": "国际现货基准 · 即期交割",
                                })
                            elif code == "hf_XAG":
                                results.append({
                                    "name": "现货白银 (伦敦银)",
                                    "code": "XAG",
                                    "price": round(price, 2),
                                    "change_pct": change_pct,
                                    "unit": "USD/oz",
                                    "source": "伦敦银现",
                                    "category": "spot",
                                    "badge": "现货",
                                    "desc": "国际现货基准 · 即期交割",
                                })
        except Exception as e:
            logger.warning(f"获取新浪国际现货金属失败: {e}")
        return results

    @staticmethod
    @cached(
        "metals:spot_price_v2",
        ttl=settings.CACHE_TTL.get("metals", 300),
        stale_ttl=settings.CACHE_TTL.get("metals", 300) * settings.STALE_TTL_RATIO,
        sync_on_cold=True,
    )
    def get_spot_prices() -> List[Dict[str, Any]]:
        """
        获取主流金属价格 (国际现货 + COMEX 期货主力对照)
        """
        # 1. 获取国际现货行情 (伦敦金 XAU, 伦敦银 XAG)
        spot_results = MetalSpotPrice._fetch_sina_spot_metals()

        # 2. 获取 COMEX / NYMEX 期货主力行情
        futures_results = []
        try:
            df = akshare_call_with_retry(ak.futures_global_spot_em)
            if not df.empty:
                for metal in MetalSpotPrice.FUTURES_METALS:
                    try:
                        code = metal["code"]
                        row = df[df["代码"] == code]
                        if row.empty:
                            prefix = code[:2]
                            row = df[df["代码"].str.startswith(prefix, na=False)].head(1)

                        if not row.empty:
                            data = row.iloc[0]
                            price = safe_float(data["最新价"])
                            change_pct = safe_float(data["涨跌幅"])
                            futures_results.append({
                                "name": metal["name"],
                                "code": code,
                                "price": round(price, 2) if price else 0.0,
                                "change_pct": round(change_pct, 2) if change_pct else 0.0,
                                "unit": metal["unit"],
                                "source": metal["source"],
                                "category": metal["category"],
                                "badge": metal["badge"],
                                "desc": metal["desc"],
                            })
                    except Exception as e_inner:
                        logger.warning(f"解析 {metal['name']} 失败: {e_inner}")
        except Exception as e:
            logger.error(f"获取 COMEX 期货金属价格失败: {e}")

        # 3. 组织最终列表：现货与期货成对排列对照
        final_list = []
        gold_spot = [x for x in spot_results if x["code"] == "XAU"]
        gold_fut = [x for x in futures_results if x["code"] == "GC00Y"]
        silver_spot = [x for x in spot_results if x["code"] == "XAG"]
        silver_fut = [x for x in futures_results if x["code"] == "SI00Y"]
        other_fut = [x for x in futures_results if x["code"] not in ["GC00Y", "SI00Y"]]

        if gold_spot:
            final_list.extend(gold_spot)
        if gold_fut:
            final_list.extend(gold_fut)
        if silver_spot:
            final_list.extend(silver_spot)
        if silver_fut:
            final_list.extend(silver_fut)
        final_list.extend(other_fut)

        return final_list

