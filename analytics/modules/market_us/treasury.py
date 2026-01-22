#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/20
Desc: 美债收益率分析
"""

import akshare as ak
import pandas as pd
from typing import List, Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.logger import logger


class USTreasury:
    """美债收益率分析"""

    @staticmethod
    @cached(
        "market_us:bond_yields",
        ttl=settings.CACHE_TTL.get("market_overview", 3600),
        stale_ttl=settings.CACHE_TTL.get("market_overview", 3600) * settings.STALE_TTL_RATIO,
    )
    def get_us_bond_yields() -> List[Dict[str, Any]]:
        """
        获取美债收益率
        关注: 2年期, 10年期, 30年期, 10Y-2Y倒挂
        """
        try:
            df = ak.bond_zh_us_rate(start_date="20240101")

            # 过滤无效数据: 确保10年期收益率存在
            if not df.empty and "美国国债收益率10年" in df.columns:
                df = df.dropna(subset=["美国国债收益率10年"])

            if df.empty:
                return []

            latest = df.iloc[-1]

            # 提取数据
            us_2y = (
                float(latest["美国国债收益率2年"])
                if "美国国债收益率2年" in latest
                and pd.notna(latest["美国国债收益率2年"])
                else 0
            )
            us_10y = (
                float(latest["美国国债收益率10年"])
                if "美国国债收益率10年" in latest
                and pd.notna(latest["美国国债收益率10年"])
                else 0
            )
            us_30y = (
                float(latest["美国国债收益率30年"])
                if "美国国债收益率30年" in latest
                and pd.notna(latest["美国国债收益率30年"])
                else 0
            )

            # 计算利差 (倒挂)
            inversion = us_10y - us_2y

            return [
                {"name": "2年期美债", "value": us_2y, "suffix": "%"},
                {"name": "10年期美债", "value": us_10y, "suffix": "%"},
                {"name": "30年期美债", "value": us_30y, "suffix": "%"},
                {
                    "name": "10Y-2Y利差",
                    "value": round(inversion, 3),
                    "suffix": "%",
                    "is_spread": True,
                },
            ]

        except Exception as e:
            logger.error(f"获取美债收益率失败: {e}")
            return []
