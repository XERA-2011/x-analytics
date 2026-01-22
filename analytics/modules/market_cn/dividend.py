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
                pe = safe_float(row.get("市盈率-动态"))
                pb = safe_float(row.get("市净率"))
                
                # 计算 ROE 和 盈利收益率
                roe = (pb / pe * 100) if pe and pe > 0 and pb else 0
                earnings_yield = (100 / pe) if pe and pe > 0 else 0
                
                code = str(row["代码"]).zfill(6)
                stock = {
                    "code": code,
                    "name": str(row["名称"]),
                    "weight": safe_float(row.get("权重", 0)),
                    "price": safe_float(row.get("最新价")),
                    "change_pct": safe_float(row.get("涨跌幅")),
                    "pe_ratio": pe,
                    "pb_ratio": pb,
                    "roe": round(roe, 2),
                    "earnings_yield": round(earnings_yield, 2),
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
            # 计算加权指标 (Weighted Metrics)
            total_weight = sum(s.get("weight", 0) for s in stocks)
            if total_weight == 0:
                total_weight = 1  # 避免除以零

            # 加权 PE
            weighted_pe = sum(s.get("pe_ratio", 0) * s.get("weight", 0) for s in stocks if s.get("pe_ratio")) / total_weight
            
            # 加权 ROE
            weighted_roe = sum(s.get("roe", 0) * s.get("weight", 0) for s in stocks if s.get("roe")) / total_weight
            
            # 加权 盈利收益率 (这是股息率的上限代理)
            weighted_ey = sum(s.get("earnings_yield", 0) * s.get("weight", 0) for s in stocks if s.get("earnings_yield")) / total_weight
            
            # 银行股权重占比
            bank_weight = sum(s.get("weight", 0) for s in stocks if "银行" in s.get("name", ""))
            
            # 信号系统 (Signal System)
            # 阈值参考: 激进 PE<=7 或 EY>=5.8%; 保守 PE>=8.2 或 EY<4.0%
            signal = "NEUTRAL"
            signal_color = "#E6A23C" # Orange/Yellow
            signal_text = "观察 / 定投"
            
            if weighted_pe > 0 and weighted_pe <= 7.0:
                signal = "OPPORTUNITY"
                signal_color = "#67C23A" # Green/Success
                signal_text = "极低估 / 机会"
            elif weighted_ey >= 5.8:
                 signal = "OPPORTUNITY"
                 signal_color = "#67C23A"
                 signal_text = "高股息 / 机会"
            elif weighted_pe >= 8.2 or (weighted_ey > 0 and weighted_ey < 4.0):
                signal = "CAUTION"
                signal_color = "#F56C6C" # Red/Danger
                signal_text = "偏高估 / 谨慎"

            # 计算涨跌统计
            changes = [s["change_pct"] for s in stocks if s.get("change_pct") is not None]
            up_count = len([c for c in changes if c > 0])
            down_count = len([c for c in changes if c < 0])
            avg_change = sum(changes) / len(changes) if changes else 0
            
            # 权重TOP5
            top_weights = sorted(stocks, key=lambda x: x.get("weight", 0), reverse=True)[:5]
            total_weight_top5 = sum(s.get("weight", 0) for s in top_weights)
            
            return {
                "avg_pe_ratio": round(weighted_pe, 2), # 使用加权替换简单平均
                "avg_roe": round(weighted_roe, 2),
                "avg_earnings_yield": round(weighted_ey, 2),
                "bank_weight": round(bank_weight, 2),
                "signal": {
                    "type": signal,
                    "color": signal_color,
                    "text": signal_text
                },
                "avg_change_pct": round(avg_change, 2),
                "up_count": up_count,
                "down_count": down_count,
                "top5_weight": round(total_weight_top5, 2),
                "low_volatility_count": len(stocks),
            }

        except Exception as e:
            print(f"⚠️ 计算策略统计失败: {e}")
            return {}

    @staticmethod
    def _get_strategy_description() -> str:
        """获取策略说明"""
        return """
中证红利低波动指数 (H30269) 深度分析：
• 选股逻辑：高股息 + 低波动 = "稳健复利"
• 价值特征：适合在低利率环境下替代债券，具有类债属性
• 历史表现：在震荡市和熊市中通常跑赢大盘，牛市中弹性较弱
• 核心指标：关注 ROE (净资产收益率) 和 PB (市净率) 的匹配度

信号系统参考：
• 🟢 极低估/机会：PE ≤ 7.0 或 股息率 ≥ 5.8%
• 🟡 观察/定投：介于两者之间
• 🔴 偏高估/谨慎：PE ≥ 8.2 或 股息率 < 4.0%
        """.strip()
