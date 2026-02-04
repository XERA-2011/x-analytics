"""
贵金属基本面数据模块
获取 SPDR GLD ETF 持仓和 COMEX 库存数据
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, Optional
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import get_beijing_time, akshare_call_with_retry, safe_float
from ...core.logger import logger


class MetalFundamentals:
    """贵金属基本面数据获取器"""

    # 趋势计算窗口
    TREND_WINDOW_DAYS = 7

    @staticmethod
    @cached(
        "metals:spdr_gold_holdings_v1",
        ttl=settings.CACHE_TTL["metals"],
        stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO
    )
    def get_spdr_gold_holdings() -> Dict[str, Any]:
        """
        获取 SPDR GLD ETF 持仓数据
        
        Returns:
            Dict containing current holdings, 7d trend, and score
        """
        try:
            df = akshare_call_with_retry(ak.macro_cons_gold)
            
            if df.empty or len(df) < MetalFundamentals.TREND_WINDOW_DAYS:
                return {"error": "无法获取足够的 SPDR GLD 持仓数据", "available": False}
            
            # 数据列: 日期, SPDR Gold Trust 持仓量 (吨), ...
            # 确保按日期升序排列
            if "日期" in df.columns:
                df = df.sort_values(by="日期")
            
            # 获取持仓量列 (尝试多种可能的列名)
            holdings_col = None
            for col in df.columns:
                if "持仓" in col or "holdings" in col.lower():
                    holdings_col = col
                    break
            
            if holdings_col is None:
                # 如果没找到，假设第二列是持仓量
                holdings_col = df.columns[1]
            
            # 提取最近数据
            recent = df.tail(MetalFundamentals.TREND_WINDOW_DAYS)
            current_holdings = safe_float(recent.iloc[-1][holdings_col])
            prev_holdings = safe_float(recent.iloc[0][holdings_col])
            
            if current_holdings is None or prev_holdings is None:
                return {"error": "持仓数据解析失败", "available": False}
            
            # 计算 7 日变化率
            change_pct = ((current_holdings - prev_holdings) / prev_holdings) * 100 if prev_holdings > 0 else 0
            
            # 趋势判断
            if change_pct > 1.0:
                trend = "increasing"
                trend_label = "增持"
            elif change_pct < -1.0:
                trend = "decreasing"
                trend_label = "减持"
            else:
                trend = "stable"
                trend_label = "持平"
            
            return {
                "available": True,
                "current_holdings": round(current_holdings, 2),
                "prev_holdings": round(prev_holdings, 2),
                "change_pct": round(change_pct, 2),
                "trend": trend,
                "trend_label": trend_label,
                "window_days": MetalFundamentals.TREND_WINDOW_DAYS,
                "unit": "吨",
                "source": "SPDR Gold Trust",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
        except Exception as e:
            logger.error(f"❌ 获取 SPDR GLD 持仓失败: {e}")
            return {"error": str(e), "available": False}

    @staticmethod
    @cached(
        "metals:comex_gold_inventory_v1",
        ttl=settings.CACHE_TTL["metals"],
        stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO
    )
    def get_comex_gold_inventory() -> Dict[str, Any]:
        """
        获取 COMEX 黄金库存数据
        
        Returns:
            Dict containing current inventory, 7d trend, and score
        """
        return MetalFundamentals._get_comex_inventory("黄金")

    @staticmethod
    @cached(
        "metals:comex_silver_inventory_v1",
        ttl=settings.CACHE_TTL["metals"],
        stale_ttl=settings.CACHE_TTL["metals"] * settings.STALE_TTL_RATIO
    )
    def get_comex_silver_inventory() -> Dict[str, Any]:
        """
        获取 COMEX 白银库存数据
        
        Returns:
            Dict containing current inventory, 7d trend, and score
        """
        return MetalFundamentals._get_comex_inventory("白银")

    @staticmethod
    def _get_comex_inventory(symbol: str) -> Dict[str, Any]:
        """
        获取 COMEX 库存数据的通用方法
        
        Args:
            symbol: "黄金" 或 "白银"
        """
        try:
            df = akshare_call_with_retry(ak.futures_comex_inventory, symbol=symbol)
            
            if df.empty or len(df) < MetalFundamentals.TREND_WINDOW_DAYS:
                return {"error": f"无法获取足够的 COMEX {symbol}库存数据", "available": False}
            
            # 按日期升序排列
            if "日期" in df.columns:
                df = df.sort_values(by="日期")
            
            # 获取库存量列 (吨)
            inventory_col = None
            for col in df.columns:
                if "吨" in col and "库存" in col:
                    inventory_col = col
                    break
            
            if inventory_col is None:
                # 尝试查找包含 "库存" 的列
                for col in df.columns:
                    if "库存" in col:
                        inventory_col = col
                        break
            
            if inventory_col is None:
                return {"error": "无法识别库存数据列", "available": False}
            
            # 提取最近数据
            recent = df.tail(MetalFundamentals.TREND_WINDOW_DAYS)
            current_inventory = safe_float(recent.iloc[-1][inventory_col])
            prev_inventory = safe_float(recent.iloc[0][inventory_col])
            
            if current_inventory is None or prev_inventory is None:
                return {"error": "库存数据解析失败", "available": False}
            
            # 计算 7 日变化率
            change_pct = ((current_inventory - prev_inventory) / prev_inventory) * 100 if prev_inventory > 0 else 0
            
            # 趋势判断 (库存减少 = 需求强 = 利多)
            if change_pct < -1.0:
                trend = "decreasing"
                trend_label = "库存下降"
            elif change_pct > 1.0:
                trend = "increasing"
                trend_label = "库存上升"
            else:
                trend = "stable"
                trend_label = "持平"
            
            return {
                "available": True,
                "current_inventory": round(current_inventory, 2),
                "prev_inventory": round(prev_inventory, 2),
                "change_pct": round(change_pct, 2),
                "trend": trend,
                "trend_label": trend_label,
                "window_days": MetalFundamentals.TREND_WINDOW_DAYS,
                "unit": "吨",
                "source": f"COMEX {symbol}",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
        except Exception as e:
            logger.error(f"❌ 获取 COMEX {symbol}库存失败: {e}")
            return {"error": str(e), "available": False}

    @staticmethod
    def calculate_etf_holdings_score(holdings_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        根据 ETF 持仓趋势计算情绪分数
        
        Logic:
        - 持仓增加 (机构买入) -> 贪婪 -> 高分
        - 持仓减少 (机构卖出) -> 恐慌 -> 低分
        
        Returns:
            Dict with score (0-100) and metadata, or None if data unavailable
        """
        if not holdings_data.get("available"):
            return None
        
        change_pct = holdings_data.get("change_pct", 0)
        
        # 线性映射: -5% -> 0分, 0% -> 50分, +5% -> 100分
        score = 50 + change_pct * 10
        score = min(100, max(0, score))
        
        return {
            "value": change_pct,
            "score": round(score, 1),
            "weight": settings.FEAR_GREED_CONFIG.get("metals", {}).get("weights", {}).get("etf_holdings", 0.15),
            "name": "ETF 持仓趋势",
            "description": f"SPDR GLD {holdings_data.get('trend_label', '')} ({change_pct:+.2f}%)"
        }

    @staticmethod
    def calculate_inventory_score(inventory_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        根据 COMEX 库存趋势计算情绪分数
        
        Logic:
        - 库存减少 (实物需求强) -> 贪婪 -> 高分
        - 库存增加 (需求弱) -> 恐慌 -> 低分
        
        Returns:
            Dict with score (0-100) and metadata, or None if data unavailable
        """
        if not inventory_data.get("available"):
            return None
        
        change_pct = inventory_data.get("change_pct", 0)
        
        # 反向映射: 库存减少是利多
        # +5% -> 0分, 0% -> 50分, -5% -> 100分
        score = 50 - change_pct * 10
        score = min(100, max(0, score))
        
        return {
            "value": change_pct,
            "score": round(score, 1),
            "weight": settings.FEAR_GREED_CONFIG.get("metals", {}).get("weights", {}).get("comex_inventory", 0.15),
            "name": "COMEX 库存趋势",
            "description": f"{inventory_data.get('source', 'COMEX')} {inventory_data.get('trend_label', '')} ({change_pct:+.2f}%)"
        }
