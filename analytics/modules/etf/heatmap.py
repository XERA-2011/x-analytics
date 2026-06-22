"""
ETF 热力图模块
动态获取 A 股市场全量 ETF 实时行情，提取流通市值前 50 的独立 ETF，并通过正则智能分类生成热力图数据
"""

import re
from typing import Dict, Any, List
import pandas as pd
import akshare as ak

from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger

# 排行榜返回的最大条目数
TOP_N = 10

class ETFHeatmap:
    """ETF 热力图数据"""

    @staticmethod
    def _categorize_etf(name: str) -> str:
        """根据 ETF 名称自动分类"""
        if re.search(r'(300|500|1000|2000|A50|A500|50ETF|创业板|科创|深100|中证100)', name):
            return "宽基指数"
        elif re.search(r'(恒生|纳指|标普|日经|港|跨境|道琼斯)', name):
            return "跨境"
        elif re.search(r'(金|银|豆粕|债)', name):
            return "商品债券"
        else:
            return "行业主题"

    @staticmethod
    def _get_base_name(name: str) -> str:
        """提取 ETF 核心名，去掉基金公司后缀"""
        name = name.replace("A500ETF", "中证A500ETF")
        name = name.replace("券商ETF", "证券ETF")
        
        if "ETF" in name:
            return name.split("ETF")[0] + "ETF"
        return name

    @staticmethod
    @cached(
        "etf:heatmap",
        ttl=settings.CACHE_TTL["market"],
        stale_ttl=settings.CACHE_TTL["market"] * settings.STALE_TTL_RATIO
    )
    def get_heatmap_data() -> Dict[str, Any]:
        """
        获取 ETF 热力图数据 (动态合并同类项，保留前 50 独立题材)

        Returns:
            包含分类 treemap 数据和涨跌排行榜
        """
        try:
            # 1. 获取全市场 ETF 数据
            df = akshare_call_with_retry(ak.fund_etf_spot_em)
            if df is None or df.empty:
                raise ValueError("获取全量 ETF 行情数据失败")
            
            # 2. 清洗数值列
            if "流通市值" in df.columns:
                df["流通市值"] = pd.to_numeric(df["流通市值"], errors="coerce").fillna(0)
            if "成交额" in df.columns:
                df["成交额"] = pd.to_numeric(df["成交额"], errors="coerce").fillna(0)
            
            # 3. 按底层资产分组并选拔龙头
            groups_dict: Dict[str, List[pd.Series]] = {}
            for _, row in df.iterrows():
                name = str(row.get("名称", ""))
                base_name = ETFHeatmap._get_base_name(name)
                
                # 过滤无波动的货币基金
                if base_name in ["华宝添益ETF", "银华日利ETF"]:
                    continue
                    
                if base_name not in groups_dict:
                    groups_dict[base_name] = []
                groups_dict[base_name].append(row)
                
            base_leaders = []
            for base_name, rows in groups_dict.items():
                # 按成交额降序，挑出组内当天交投最活跃的 ETF 作为展示代表
                rows_sorted_by_amount = sorted(rows, key=lambda x: safe_float(x.get("成交额")) or 0.0, reverse=True)
                volume_leader = rows_sorted_by_amount[0]
                
                # 提取该板块最大的流通市值，用于评价该题材是否有资格进入 Top 50
                max_market_cap = max((safe_float(r.get("流通市值")) or 0.0) for r in rows)
                
                base_leaders.append({
                    "leader_row": volume_leader,
                    "max_market_cap": max_market_cap,
                    "base_name": base_name
                })
                
            # 4. 根据流通市值排行榜，截取最核心的前 50 大板块
            base_leaders.sort(key=lambda x: x["max_market_cap"], reverse=True)
            top50_groups = base_leaders[:50]
            
            # 构建最终展示数据列表
            all_etfs: List[Dict[str, Any]] = []
            for group in top50_groups:
                row = group["leader_row"]
                base_name = group["base_name"]
                
                amount = safe_float(row.get("成交额")) or 0.0
                price = safe_float(row.get("最新价"))
                change_pct = safe_float(row.get("涨跌幅"))
                turnover = safe_float(row.get("换手率"))
                
                etf_item = {
                    "name": str(row.get("名称", "")),
                    "code": str(row.get("代码", "")),
                    "value": amount if amount else 0,  # 面积严格对应这只 ETF 自己的单只成交额
                    "change_pct": change_pct,
                    "price": price,
                    "amount": amount,
                    "turnover": turnover,
                    "base_name": base_name
                }
                all_etfs.append(etf_item)
            
            # 5. 构建 treemap 分类数据
            category_map: Dict[str, List[Dict[str, Any]]] = {
                "宽基指数": [],
                "跨境": [],
                "商品债券": [],
                "行业主题": []
            }
            
            for etf_dict in all_etfs:
                cat_name = ETFHeatmap._categorize_etf(etf_dict["base_name"])
                
                # 清理临时字段
                clean_dict = etf_dict.copy()
                clean_dict.pop("base_name", None)
                
                category_map[cat_name].append(clean_dict)
                
            categories = []
            for cat_name, children in category_map.items():
                if children:
                    cat_total = sum(c["value"] for c in children)
                    categories.append({
                        "name": cat_name,
                        "value": cat_total,
                        "children": children
                    })
                    
            # 6. 生成涨跌排行
            sorted_by_change = sorted(
                [e for e in all_etfs if e["change_pct"] is not None],
                key=lambda x: x["change_pct"],
                reverse=True
            )

            top_gainers = sorted_by_change[:TOP_N]
            top_losers = sorted_by_change[-TOP_N:][::-1]

            matched_count = len(all_etfs)
            total_count = len(df)

            return {
                "categories": categories,
                "top_gainers": top_gainers,
                "top_losers": top_losers,
                "matched": matched_count,
                "total": total_count,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"获取 ETF 热力图数据失败: {e}")
            return {
                "error": str(e),
                "categories": [],
                "top_gainers": [],
                "top_losers": [],
                "status": "error",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }
