"""
亚洲市场主要指数模块
获取沪深300、恒生指数、日经225、韩国KOSPI等核心指数数据
"""

from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.data_provider import data_provider
from ...core.logger import logger

class CNIndices:
    """亚洲市场核心指数 (中港日韩)"""
    
    # 关注的核心指数
    CORE_INDICES = {
        "000300": "沪深300",
        "HSI": "恒生指数", 
        "HSTECH": "恒生科技",
        "HSCEI": "国企指数",
        "HSCCI": "红筹指数",
        "N225": "日经225",
        "KS11": "韩国KOSPI",
    }

    # 指定排序顺序
    DISPLAY_ORDER = ["000300", "HSI", "HSTECH", "HSCEI", "HSCCI", "N225", "KS11"]

    @staticmethod
    @cached(
        "market_cn:indices",
        ttl=settings.CACHE_TTL["market"], 
        stale_ttl=settings.CACHE_TTL["market"] * settings.STALE_TTL_RATIO
    )
    def get_indices() -> Dict[str, Any]:
        """
        获取主要亚洲指数实时行情 (合并全球和港股数据源)
        
        Returns:
            指数列表数据
        """
        try:
            # 1. 获取全球和港股指数数据
            df_em = data_provider.get_global_indices_spot()
            em_map = df_em.set_index("代码").to_dict(orient="index") if not df_em.empty else {}

            df_hk = data_provider.get_hk_indices_spot()
            hk_map = df_hk.set_index("代码").to_dict(orient="index") if not df_hk.empty else {}

            # 合并映射以便按顺序查找
            df_map = {**em_map, **hk_map}

            # 过滤出核心指数
            indices_data = []
            
            for code in CNIndices.DISPLAY_ORDER:
                if code in df_map:
                    row = df_map[code]
                    indices_data.append({
                        "symbol": code,
                        "name": CNIndices.CORE_INDICES[code],
                        "price": safe_float(row["最新价"]),
                        "change_amount": safe_float(row["涨跌额"]),
                        "change_pct": safe_float(row["涨跌幅"]),
                        "volume": 0.0,
                        "amount": 0.0,
                    })

            if len(indices_data) != len(CNIndices.DISPLAY_ORDER):
                missing = [code for code in CNIndices.DISPLAY_ORDER if code not in df_map]
                raise ValueError(f"核心亚洲指数数据不完整: missing={missing}")
            
            return {
                "indices": indices_data,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"获取亚洲市场指数失败: {e}")
            return {
                "error": str(e),
                "indices": [],
                "status": "error",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            }

