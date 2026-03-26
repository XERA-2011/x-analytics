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
from ...core.utils import akshare_call_with_retry
from ...core.logger import logger


class USTreasury:
    """美债收益率分析"""

    @staticmethod
    @cached(
        "market_us:bond_yields",
        ttl=settings.CACHE_TTL.get("market_overview", 3600),
        stale_ttl=settings.CACHE_TTL.get("market_overview", 3600) * settings.STALE_TTL_RATIO,
    )
    def get_us_bond_yields() -> Dict[str, Any]:
        """
        获取美债收益率
        关注: 2年期, 10年期, 30年期, 10Y-2Y倒挂
        """
        try:
            df = akshare_call_with_retry(ak.bond_zh_us_rate, start_date="20240101")

            if df.empty:
                return {"error": "无法获取美债收益率数据"}

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

            # 获取前一日数据计算变动
            prev_10y = 0.0
            prev_2y = 0.0
            prev_30y = 0.0
            
            if len(df) > 1:
                prev = df.iloc[-2]
                if "美国国债收益率10年" in prev and pd.notna(prev["美国国债收益率10年"]):
                    prev_10y = float(prev["美国国债收益率10年"])
                if "美国国债收益率2年" in prev and pd.notna(prev["美国国债收益率2年"]):
                    prev_2y = float(prev["美国国债收益率2年"])
                if "美国国债收益率30年" in prev and pd.notna(prev["美国国债收益率30年"]):
                    prev_30y = float(prev["美国国债收益率30年"])
            
            change_10y = us_10y - prev_10y if prev_10y > 0 else 0.0
            change_2y = us_2y - prev_2y if prev_2y > 0 else 0.0
            change_30y = us_30y - prev_30y if prev_30y > 0 else 0.0

            # 智能分析生成 - 针对每个指标分别分析
            
            def analyze_spread(val: float) -> Dict[str, Any]:
                if val < -0.5:
                    return {"text": "深度倒挂：强烈的衰退预警", "level": "danger"}
                elif val < 0:
                    return {"text": "曲线倒挂：经济衰退风险较高", "level": "warning"}
                elif val < 0.2:
                    return {"text": "利差收窄：经济前景趋弱", "level": "neutral"}
                else:
                    return {"text": "形态正常：经济增长预期稳健", "level": "good"}

            def analyze_2y(val: float, change: float) -> Dict[str, Any]:
                if val > 5.0:
                    return {"text": "紧缩高压：降息预期显著降温", "level": "warning"}
                elif change > 0.1:
                    return {"text": "短端承压：由于政策预期收紧", "level": "warning"}
                elif change < -0.1:
                    return {"text": "降息交易：市场押注政策转向", "level": "neutral"}
                else:
                    return {"text": "跟随政策利率波动", "level": "neutral"}

            def analyze_10y(val: float, change: float) -> Dict[str, Any]:
                if val > 4.5:
                    return {"text": "利率高企：压制全球资产估值", "level": "danger"}
                elif change > 0.1:
                    return {"text": "快速上行：通胀担忧重燃", "level": "warning"}
                elif val < 3.5:
                    return {"text": "处于舒适区：利好成长股", "level": "good"}
                else:
                    return {"text": "全球资产定价之锚", "level": "neutral"}

            def analyze_30y(val: float, diff_10y: float) -> Dict[str, Any]:
                if val > 4.8:
                    return {"text": "长期通胀预期脱锚风险", "level": "warning"}
                elif diff_10y > 0.5:
                    return {"text": "期限溢价走阔", "level": "neutral"}
                else:
                    return {"text": "反映长期经济增长预期", "level": "neutral"}

            metrics = [
                {
                    "name": "10Y-2Y利差",
                    "value": round(inversion, 3),
                    "suffix": "%",
                    "is_spread": True,
                    "analysis": analyze_spread(inversion)
                },
                {
                    "name": "2年期美债",
                    "value": us_2y,
                    "suffix": "%",
                    "change": round(change_2y, 2),
                    "analysis": analyze_2y(us_2y, change_2y)
                },
                {
                    "name": "10年期美债",
                    "value": us_10y,
                    "suffix": "%", 
                    "change": round(change_10y, 2),
                    "analysis": analyze_10y(us_10y, change_10y)
                },
                {
                    "name": "30年期美债",
                    "value": us_30y,
                    "suffix": "%",
                    "change": round(change_30y, 2),
                    "analysis": analyze_30y(us_30y, us_30y - us_10y)
                },
            ]

            return {
                "metrics": metrics,
                "timestamp": latest.get("日期", str(pd.Timestamp.now().date()))
            }

        except Exception as e:
            logger.error(f"获取美债收益率失败: {e}")
            return {"error": str(e)}
