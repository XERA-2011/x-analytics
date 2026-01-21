"""
中国市场红利低波策略
筛选高股息、低波动率的优质股票
"""

import akshare as ak
import numpy as np
from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.data_provider import data_provider


class CNDividendStrategy:
    """红利低波策略"""

    @staticmethod
    @cached("market_cn:dividend", ttl=settings.CACHE_TTL["dividend"], stale_ttl=settings.CACHE_TTL["dividend"] * settings.STALE_TTL_RATIO)
    def get_dividend_stocks(limit: int = 20) -> Dict[str, Any]:
        """
        获取红利低波股票池

        Args:
            limit: 返回股票数量

        Returns:
            红利低波股票数据
        """
        try:
            # 使用共享数据提供层获取股票数据 (与 heat.py 共享)
            df = data_provider.get_stock_zh_a_spot()

            if df.empty:
                raise ValueError("无法获取股票数据")

            # 筛选条件
            filtered_df = df[
                (~df["名称"].str.contains("ST", na=False))  # 排除ST股票
                & (df["市盈率-动态"] > 0)  # 排除亏损股票
                & (df["市盈率-动态"] < 50)  # 排除高估值股票
                & (df["成交额"] > 10000000)  # 成交额大于1000万
            ].copy()

            # 计算股息率（简化处理，使用市盈率倒数估算）
            filtered_df["estimated_dividend_yield"] = (
                1 / filtered_df["市盈率-动态"] * 100
            )

            # 计算波动率（使用涨跌幅的绝对值作为简化指标）
            filtered_df["volatility_proxy"] = abs(filtered_df["涨跌幅"])

            # 计算综合评分
            # 股息率权重60%，低波动率权重40%
            filtered_df["dividend_score"] = (
                filtered_df["estimated_dividend_yield"] * 0.6
                - filtered_df["volatility_proxy"] * 0.4
            )

            # 按综合评分排序
            top_stocks = filtered_df.nlargest(limit, "dividend_score")

            # 格式化数据
            stocks = []
            for _, row in top_stocks.iterrows():
                stock = {
                    "code": str(row["代码"]),
                    "name": str(row["名称"]),
                    "price": safe_float(row["最新价"]),
                    "change_pct": safe_float(row["涨跌幅"]),
                    "pe_ratio": safe_float(row["市盈率-动态"]),
                    "pb_ratio": safe_float(row.get("市净率", 0)),
                    "estimated_dividend_yield": round(
                        safe_float(row["estimated_dividend_yield"]), 2
                    ),
                    "volatility_proxy": round(safe_float(row["volatility_proxy"]), 2),
                    "dividend_score": round(safe_float(row["dividend_score"]), 2),
                    "market_cap": safe_float(row.get("总市值", 0)),
                    "turnover": safe_float(row["成交额"]),
                }
                stocks.append(stock)

            # 计算策略统计
            strategy_stats = CNDividendStrategy._calculate_strategy_stats(stocks)

            return {
                "stocks": stocks,
                "count": len(stocks),
                "strategy_stats": strategy_stats,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "description": CNDividendStrategy._get_strategy_description(),
            }

        except Exception as e:
            print(f"❌ 获取红利低波股票失败: {e}")
            return {
                "error": str(e),
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
                {"code": "510880", "name": "红利ETF", "index": "上证红利指数"},
                {"code": "159915", "name": "创业板ETF", "index": "创业板指数"},
                {"code": "512090", "name": "MSCI易方达", "index": "MSCI中国A股"},
                {"code": "515450", "name": "高股息ETF", "index": "中证红利指数"},
                {"code": "515180", "name": "红利低波ETF", "index": "红利低波动指数"},
            ]

            # 获取ETF实时数据
            etf_data = []
            for etf in dividend_etfs:
                try:
                    # 这里简化处理，实际应该调用具体的ETF数据接口
                    etf_info = {
                        "code": etf["code"],
                        "name": etf["name"],
                        "index": etf["index"],
                        "price": 0,  # 实际应该获取实时价格
                        "change_pct": 0,  # 实际应该获取涨跌幅
                        "volume": 0,  # 实际应该获取成交量
                        "nav": 0,  # 实际应该获取净值
                        "premium_rate": 0,  # 实际应该获取溢价率
                    }
                    etf_data.append(etf_info)
                except Exception as e:
                    print(f"⚠️ 获取ETF {etf['code']} 数据失败: {e}")
                    continue

            return {
                "etfs": etf_data,
                "count": len(etf_data),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "note": "ETF数据为示例，实际使用需要接入具体数据源",
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
    def _calculate_strategy_stats(stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算策略统计数据"""
        if not stocks:
            return {}

        try:
            # 计算平均指标
            avg_dividend_yield = np.mean(
                [s["estimated_dividend_yield"] for s in stocks]
            )
            avg_pe_ratio = np.mean([s["pe_ratio"] for s in stocks if s["pe_ratio"] > 0])
            avg_volatility = np.mean([s["volatility_proxy"] for s in stocks])

            # 计算分布
            high_dividend_count = len(
                [s for s in stocks if s["estimated_dividend_yield"] > 3]
            )
            low_pe_count = len([s for s in stocks if s["pe_ratio"] < 15])
            low_volatility_count = len([s for s in stocks if s["volatility_proxy"] < 2])

            return {
                "avg_dividend_yield": round(avg_dividend_yield, 2),
                "avg_pe_ratio": round(avg_pe_ratio, 2),
                "avg_volatility": round(avg_volatility, 2),
                "high_dividend_count": high_dividend_count,
                "low_pe_count": low_pe_count,
                "low_volatility_count": low_volatility_count,
                "high_dividend_ratio": round(
                    high_dividend_count / len(stocks) * 100, 1
                ),
                "low_pe_ratio": round(low_pe_count / len(stocks) * 100, 1),
                "low_volatility_ratio": round(
                    low_volatility_count / len(stocks) * 100, 1
                ),
            }

        except Exception as e:
            print(f"⚠️ 计算策略统计失败: {e}")
            return {}

    @staticmethod
    def _get_strategy_description() -> str:
        """获取策略说明"""
        return """
红利低波策略说明：
• 筛选标准：高股息率(>3%) + 低波动率 + 合理估值(PE<50)
• 排除条件：ST股票、亏损股票、成交额过小股票
• 评分方法：股息率权重60% + 低波动率权重40%
• 投资理念：追求稳定的股息收入，降低组合波动率
• 适合投资者：风险偏好较低，追求稳定收益的长期投资者
• 注意事项：股息率为估算值，实际投资需参考公司分红政策
        """.strip()
