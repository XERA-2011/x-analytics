"""
LPR 贷款市场报价利率追踪
"""

import akshare as ak
from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger


class LPRAnalysis:
    """LPR 利率分析"""

    @staticmethod
    @cached(
        "macro:lpr",
        ttl=settings.CACHE_TTL.get("lpr", 86400),
        stale_ttl=settings.CACHE_TTL.get("lpr", 86400) * settings.STALE_TTL_RATIO,
    )
    def get_lpr_rates() -> Dict[str, Any]:
        """
        获取 LPR 贷款市场报价利率

        Returns:
            LPR 利率数据（1年期、5年期）
        """
        try:
            logger.info("获取 LPR 利率数据...")
            df = akshare_call_with_retry(ak.macro_china_lpr, max_retries=3)

            if df.empty:
                raise ValueError("无法获取 LPR 数据")

            # 获取最新数据（最后一行有 LPR 值的）
            df = df.dropna(subset=["LPR1Y"])
            if df.empty:
                raise ValueError("LPR 数据为空")

            latest = df.iloc[-1]
            
            # 获取历史变化（最近 12 条记录）
            history: List[Dict[str, Any]] = []
            for _, row in df.tail(12).iloc[::-1].iterrows():
                history.append({
                    "date": str(row["TRADE_DATE"])[:10],
                    "lpr_1y": safe_float(row.get("LPR1Y")),
                    "lpr_5y": safe_float(row.get("LPR5Y")),
                })

            # 计算上一次变动
            prev = df.iloc[-2] if len(df) >= 2 else latest
            lpr_1y_change = safe_float(latest.get("LPR1Y")) - safe_float(prev.get("LPR1Y"))
            lpr_5y_change = safe_float(latest.get("LPR5Y")) - safe_float(prev.get("LPR5Y"))

            return {
                "current": {
                    "date": str(latest["TRADE_DATE"])[:10],
                    "lpr_1y": safe_float(latest.get("LPR1Y")),
                    "lpr_5y": safe_float(latest.get("LPR5Y")),
                    "lpr_1y_change": round(lpr_1y_change, 2) if lpr_1y_change != 0 else 0,
                    "lpr_5y_change": round(lpr_5y_change, 2) if lpr_5y_change != 0 else 0,
                },
                "history": history,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "description": "LPR 贷款市场报价利率，每月 20 日公布",
            }

        except Exception as e:
            logger.error(f"获取 LPR 利率失败: {e}")
            return {
                "error": str(e),
                "current": None,
                "history": [],
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }
