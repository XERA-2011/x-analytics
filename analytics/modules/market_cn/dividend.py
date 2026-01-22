"""
中证红利低波动指数 (H30269)
获取指数成分股及实时行情
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, List, Optional
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.data_provider import data_provider


# 中证红利低波动指数代码
INDEX_CODE = "H30269"
INDEX_NAME = "中证红利低波动"


class CNDividendStrategy:
    """中证红利低波动指数分析"""

    @staticmethod
    @cached("market_cn:dividend", ttl=settings.CACHE_TTL["dividend"], stale_ttl=settings.CACHE_TTL["dividend"] * settings.STALE_TTL_RATIO)
    def get_dividend_stocks(limit: int = 20) -> Dict[str, Any]:
        """
        获取中证红利低波动指数成分股

        Args:
            limit: 返回股票数量

        Returns:
            成分股数据（含实时行情）
        """
        try:
            # 1. 获取指数成分股和权重
            print(f"📊 获取{INDEX_NAME}指数成分股...")
            cons_df = ak.index_stock_cons_weight_csindex(symbol=INDEX_CODE)
            
            if cons_df.empty:
                raise ValueError(f"无法获取{INDEX_NAME}成分股数据")
            
            # 提取成分股代码和权重
            cons_codes = cons_df["成分券代码"].tolist()
            cons_weights = dict(zip(cons_df["成分券代码"], cons_df["权重"]))
            cons_names = dict(zip(cons_df["成分券代码"], cons_df["成分券名称"]))
            
            print(f"✅ 获取到 {len(cons_codes)} 只成分股")
            
            # 2. 尝试获取 A 股实时行情数据（可能因限流失败）
            try:
                spot_df = data_provider.get_stock_zh_a_spot()
                if spot_df.empty:
                    spot_df = None
            except Exception as e:
                print(f"⚠️ 获取实时行情失败，使用基础数据: {e}")
                spot_df = None
            
            # 如果无法获取行情，返回基础成分股信息
            if spot_df is None:
                print("⚠️ 无法获取实时行情，返回基础成分股信息")
                stocks = []
                for code in cons_codes[:limit]:
                    code_str = str(code).zfill(6)
                    stocks.append({
                        "code": code_str,
                        "name": cons_names.get(code, cons_names.get(code_str, "--")),
                        "weight": safe_float(cons_weights.get(code, cons_weights.get(code_str, 0))),
                        "price": None,
                        "change_pct": None,
                    })
                return {
                    "index_code": INDEX_CODE,
                    "index_name": INDEX_NAME,
                    "stocks": stocks,
                    "count": len(stocks),
                    "total_constituents": len(cons_codes),
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                    "note": "实时行情暂不可用，仅显示成分股基础信息",
                }
            
            # 3. 筛选成分股行情
            # 转换代码格式 (AKShare 返回的是纯数字，spot_df 的代码也是纯数字字符串)
            spot_df["代码_clean"] = spot_df["代码"].astype(str).str.zfill(6)
            cons_codes_clean = [str(c).zfill(6) for c in cons_codes]
            
            filtered_df = spot_df[spot_df["代码_clean"].isin(cons_codes_clean)].copy()
            
            if filtered_df.empty:
                # 如果匹配失败，返回基础信息
                print("⚠️ 无法匹配实时行情，返回基础成分股信息")
                stocks = []
                for code in cons_codes[:limit]:
                    code_str = str(code).zfill(6)
                    stocks.append({
                        "code": code_str,
                        "name": cons_names.get(code, cons_names.get(code_str, "--")),
                        "weight": safe_float(cons_weights.get(code, cons_weights.get(code_str, 0))),
                        "price": None,
                        "change_pct": None,
                    })
                return {
                    "index_code": INDEX_CODE,
                    "index_name": INDEX_NAME,
                    "stocks": stocks,
                    "count": len(stocks),
                    "total_constituents": len(cons_codes),
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                }
            
            # 4. 添加权重列
            filtered_df["权重"] = filtered_df["代码_clean"].map(
                lambda x: safe_float(cons_weights.get(x, cons_weights.get(x.lstrip("0"), 0)))
            )
            
            # 按权重排序
            filtered_df = filtered_df.sort_values("权重", ascending=False)
            
            # 5. 格式化数据
            stocks: List[Dict[str, Any]] = []
            for _, row in filtered_df.head(limit).iterrows():
                code = str(row["代码"]).zfill(6)
                stock = {
                    "code": code,
                    "name": str(row["名称"]),
                    "weight": safe_float(row.get("权重", 0)),
                    "price": safe_float(row.get("最新价")),
                    "change_pct": safe_float(row.get("涨跌幅")),
                    "pe_ratio": safe_float(row.get("市盈率-动态")),
                    "pb_ratio": safe_float(row.get("市净率")),
                    "market_cap": safe_float(row.get("总市值", 0)),
                    "turnover": safe_float(row.get("成交额", 0)),
                }
                stocks.append(stock)
            
            # 6. 计算统计数据
            strategy_stats = CNDividendStrategy._calculate_strategy_stats(stocks, filtered_df)
            
            return {
                "index_code": INDEX_CODE,
                "index_name": INDEX_NAME,
                "stocks": stocks,
                "count": len(stocks),
                "total_constituents": len(cons_codes),
                "strategy_stats": strategy_stats,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "description": CNDividendStrategy._get_strategy_description(),
            }

        except Exception as e:
            print(f"❌ 获取{INDEX_NAME}成分股失败: {e}")
            return {
                "error": str(e),
                "index_code": INDEX_CODE,
                "index_name": INDEX_NAME,
                "stocks": [],
                "count": 0,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    @cached(
        "market_cn:dividend_etf", ttl=settings.CACHE_TTL["dividend"], stale_ttl=settings.CACHE_TTL["dividend"] * settings.STALE_TTL_RATIO
    )
    def get_dividend_etfs() -> Dict[str, Any]:
        """
        获取红利相关ETF

        Returns:
            红利ETF数据
        """
        try:
            # 红利相关ETF代码列表
            dividend_etfs = [
                {"code": "515180", "name": "红利低波ETF", "index": "中证红利低波动"},
                {"code": "512890", "name": "红利低波50ETF", "index": "红利低波动50"},
                {"code": "510880", "name": "红利ETF", "index": "上证红利指数"},
                {"code": "515450", "name": "红利低波100ETF", "index": "红利低波动100"},
                {"code": "159905", "name": "深红利ETF", "index": "深证红利指数"},
            ]

            return {
                "etfs": dividend_etfs,
                "count": len(dividend_etfs),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "note": "跟踪红利低波相关指数的ETF",
            }

        except Exception as e:
            print(f"❌ 获取红利ETF失败: {e}")
            return {
                "error": str(e),
                "etfs": [],
                "count": 0,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def _calculate_strategy_stats(stocks: List[Dict[str, Any]], df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """计算策略统计数据"""
        if not stocks:
            return {}

        try:
            # 计算平均指标
            pe_values = [s["pe_ratio"] for s in stocks if s.get("pe_ratio") and s["pe_ratio"] > 0]
            avg_pe_ratio = sum(pe_values) / len(pe_values) if pe_values else 0
            
            # 计算涨跌统计
            changes = [s["change_pct"] for s in stocks if s.get("change_pct") is not None]
            up_count = len([c for c in changes if c > 0])
            down_count = len([c for c in changes if c < 0])
            avg_change = sum(changes) / len(changes) if changes else 0
            
            # 权重TOP5
            top_weights = sorted(stocks, key=lambda x: x.get("weight", 0), reverse=True)[:5]
            total_weight_top5 = sum(s.get("weight", 0) for s in top_weights)
            
            return {
                "avg_pe_ratio": round(avg_pe_ratio, 2),
                "avg_change_pct": round(avg_change, 2),
                "up_count": up_count,
                "down_count": down_count,
                "top5_weight": round(total_weight_top5, 2),
                "low_volatility_count": len(stocks),  # 指数成分股本身就是低波动筛选后的
            }

        except Exception as e:
            print(f"⚠️ 计算策略统计失败: {e}")
            return {}

    @staticmethod
    def _get_strategy_description() -> str:
        """获取策略说明"""
        return """
中证红利低波动指数 (H30269) 说明：
• 编制机构：中证指数有限公司
• 成分股数量：50 只
• 选样方法：从沪深市场中选取股息率高、波动率低的股票
• 加权方式：股息率加权
• 调整频率：每年 12 月调整一次
• 投资价值：适合追求稳定分红收益、偏好低波动的长期投资者
        """.strip()
