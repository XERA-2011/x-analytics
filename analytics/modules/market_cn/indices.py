"""
中国市场主要指数模块
获取上证指数、深证成指、创业板指等核心指数数据
"""

from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger
import akshare as ak  # type: ignore

class CNIndices:
    """中国市场主要指数"""
    
    # 关注的核心指数
    CORE_INDICES = {
        "sh000001": "上证指数",
        "sz399001": "深证成指", 
        "sz399006": "创业板指",
        "sh000688": "科创50",
    }

    # 指定排序顺序
    DISPLAY_ORDER = ["sh000001", "sz399001", "sz399006", "sh000688"]

    @staticmethod
    @cached(
        "market_cn:indices",
        ttl=settings.CACHE_TTL["market"], 
        stale_ttl=settings.CACHE_TTL["market"] * settings.STALE_TTL_RATIO
    )
    def get_indices() -> Dict[str, Any]:
        """
        获取主要指数实时行情
        
        Returns:
            指数列表数据
        """
        try:
            # 优先使用新浪接口获取实时指数行情（响应快，包含核心数据）
            #备选: stock_zh_index_spot_em (东方财富, 容易被封禁)
            df = akshare_call_with_retry(
                ak.stock_zh_index_spot_sina,
                max_retries=3
            )
            
            if df.empty:
                raise ValueError("获取指数数据为空")

            # 过滤出核心指数
            indices_data = []
            
            # 创建更高效的查找字典
            df_map = df.set_index("代码").to_dict(orient="index")
            
            for code in CNIndices.DISPLAY_ORDER:
                if code in df_map:
                    row = df_map[code]
                    indices_data.append({
                        "symbol": code,
                        "name": CNIndices.CORE_INDICES[code],
                        "price": safe_float(row["最新价"]),
                        "change_amount": safe_float(row["涨跌额"]),
                        "change_pct": safe_float(row["涨跌幅"]),
                        "volume": safe_float(row["成交量"]),
                        "amount": safe_float(row["成交额"]),
                    })

            if len(indices_data) != len(CNIndices.DISPLAY_ORDER):
                missing = [code for code in CNIndices.DISPLAY_ORDER if code not in df_map]
                raise ValueError(f"核心指数数据不完整: missing={missing}")
            
            return {
                "indices": indices_data,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"获取中国市场指数失败: {e}")
            return {
                "error": str(e),
                "indices": [],
                "status": "error",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            }
