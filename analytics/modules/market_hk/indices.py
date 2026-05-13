"""
香港市场指数与板块模块
"""

from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger
import akshare as ak  # type: ignore

class HKIndices:
    """香港市场指数与板块"""
    MIN_SECTOR_INDEX_COUNT = 5
    
    # 核心指数
    CORE_INDICES = {
        "HSI": "恒生指数",
        "HSTECH": "恒生科技",
        "HSCEI": "国企指数",
        "HSCCI": "红筹指数",
    }
    
    # 板块/行业指数 (从sina接口中筛选)
    SECTOR_INDICES = {
        "HSMBI": "内地银行",
        "HSMPI": "内地地产",
        "HSMOGI": "石油天然气",
        "CESG10": "博彩业",
        "CSHK100": "HK 100",
        "GEM": "创业板",
        "HSTECH": "科技", # 重复利用作为板块
    }

    DISPLAY_ORDER = ["HSI", "HSTECH", "HSCEI", "HSCCI"]

    @staticmethod
    @cached(
        "market_hk:indices",
        ttl=settings.CACHE_TTL["market"], 
        stale_ttl=settings.CACHE_TTL["market"] * settings.STALE_TTL_RATIO
    )
    def get_market_data() -> Dict[str, Any]:
        """
        获取港股市场数据（指数 + 伪板块）
        由于无法高效获取全个股数据，使用指数作为概览
        """
        try:
            # 获取新浪港股指数列表
            df = akshare_call_with_retry(
                ak.stock_hk_index_spot_sina,
                max_retries=3
            )
            
            if df.empty:
                raise ValueError("获取港股指数数据为空")

            # 转换数据以便查找
            df_map = df.set_index("代码").to_dict(orient="index")
            
            # 1. 核心指数
            indices_data = []
            for code in HKIndices.DISPLAY_ORDER:
                if code in df_map:
                    row = df_map[code]
                    indices_data.append({
                        "symbol": code,
                        "name": HKIndices.CORE_INDICES[code],
                        "price": safe_float(row["最新价"]),
                        "change_amount": safe_float(row["涨跌额"]),
                        "change_pct": safe_float(row["涨跌幅"]),
                        # 港股指数接口没有直接的成交量/额字段标准统一，有时是 null
                        # Sina 返回的 '成交额' 往往是指数成分股总额
                        "amount": safe_float(row.get("成交额", 0)), 
                    })

            if len(indices_data) != len(HKIndices.DISPLAY_ORDER):
                missing = [code for code in HKIndices.DISPLAY_ORDER if code not in df_map]
                raise ValueError(f"港股核心指数数据不完整: missing={missing}")
            
            # 2. 板块指数 (用于模拟领涨领跌)
            sectors_data = []
            for code, name in HKIndices.SECTOR_INDICES.items():
                if code in df_map:
                    row = df_map[code]
                    sectors_data.append({
                        "code": code,
                        "name": name,
                        "price": safe_float(row["最新价"]),
                        "change_pct": safe_float(row["涨跌幅"]),
                        "amount": safe_float(row.get("成交额", 0)),
                    })

            if len(sectors_data) < HKIndices.MIN_SECTOR_INDEX_COUNT:
                raise ValueError(
                    f"港股板块指数数据不完整: expected>={HKIndices.MIN_SECTOR_INDEX_COUNT}, actual={len(sectors_data)}"
                )
            
            # 排序板块
            sectors_data.sort(key=lambda x: x["change_pct"], reverse=True)
            
            top_gainers = sectors_data[:4] # 取前4
            top_losers = sorted(sectors_data, key=lambda x: x["change_pct"])[:4] # 取倒数4

            return {
                "indices": indices_data,
                "sectors": {
                    "gainers": top_gainers,
                    "losers": top_losers,
                    "all": sectors_data
                },
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"获取港股数据失败: {e}")
            return {
                "error": str(e),
                "indices": [],
                "sectors": {"gainers": [], "losers": []},
                "status": "error"
            }
