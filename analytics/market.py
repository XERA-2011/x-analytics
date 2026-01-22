#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/01/15
Desc: 市场概览分析工具
提供市场整体情况的快速分析
"""

import akshare as ak
from datetime import datetime
from typing import Dict, Any, List

from .core.cache import cached
from .core.config import settings
from .core.data_provider import data_provider
from .core.utils import akshare_call_with_retry


class MarketAnalysis:
    """市场概览分析类"""

    @staticmethod
    def get_market_summary() -> Dict[str, Any]:
        """
        获取市场概览 (指数 + 成交量)
        """
        summary: Dict[str, Any] = {
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "indices": [],
            "volume": {"total": 0, "desc": "未知"},
        }

        indices_list: List[Dict[str, Any]] = []
        summary["indices"] = indices_list

        # 1. 获取主要指数
        try:
            # 获取主要指数的最新涨跌幅
            # indices = list(MAJOR_INDICES.values()) # This line seems to be part of an incomplete change
            # indices.append("上证指数")  # 确保包含上证
            indices_map = {
                "sh000001": "上证指数",
                "sz399001": "深证成指",
                "sz399006": "创业板指",
            }

            for code, name in indices_map.items():
                df = ak.stock_zh_index_daily(symbol=code)
                if df.empty:
                    continue

                latest = df.iloc[-1]
                prev = df.iloc[-2]

                change_pct = (latest["close"] / prev["close"] - 1) * 100
                # volume = latest["volume"]  # 手/股
                amount = latest.get("amount", 0)  # 如果有成交额

                # 如果 amount 是 nan 或者 0，尝试用 volume 估算（不准确，尽量找有 amount 的接口）
                # 注意：akshare 不同接口返回单位可能不同，这里假设 index_daily 返回的是标准单位

                indices_list.append(
                    {
                        "name": name,
                        "code": code,
                        "price": round(latest["close"], 2),
                        "change": round(change_pct, 2),
                        "amount": amount,
                    }
                )

            # 由于指数数据可能延迟，获取两市成交额建议用 spot 接口聚合
            # 这里简化处理：直接获取实时成交额（如果有专用接口）
            # 或者通过板块接口汇总是更准确的

        except Exception as e:
            print(f"获取指数失败: {e}")

        return summary

    @staticmethod
    @cached(
        "market:overview",
        ttl=settings.CACHE_TTL["market_overview"],
        stale_ttl=settings.CACHE_TTL["market_overview"] * settings.STALE_TTL_RATIO,
    )
    def get_market_overview_v2() -> Dict[str, Any]:
        """
        获取市场综合概览 (API 专用)
        包含：主要指数、上涨下跌家数、两市成交额

        缓存: 30分钟 TTL + 60分钟 Stale
        """
        result: Dict[str, Any] = {
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "indices": [],
            "stats": {},
            "volume_str": "--",
        }

        indices_list_v2: List[Dict[str, Any]] = []
        result["indices"] = indices_list_v2

        try:
            # 1. 指数行情
            # 使用 stock_zh_index_spot_em 获取实时行情
            spot_df = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
            # 筛选三大指数
            targets = ["上证指数", "深证成指", "创业板指"]
            target_df = spot_df[spot_df["名称"].isin(targets)]

            for _, row in target_df.iterrows():
                indices_list_v2.append(
                    {
                        "name": row["名称"],
                        "price": row["最新价"],
                        "change": row["涨跌幅"],
                        "amount": row["成交额"],
                    }
                )

            # 2. 市场广度 (涨跌家数)
            up_down = ak.stock_zh_a_spot_em()
            up = len(up_down[up_down["涨跌幅"] > 0])
            down = len(up_down[up_down["涨跌幅"] < 0])
            flat = len(up_down[up_down["涨跌幅"] == 0])

            result["stats"] = {"up": up, "down": down, "flat": flat}

            # 3. 两市成交额
            # total_amount = target_df["成交额"].sum()  # 粗略计算，实际上应该用专门的接口
            # 或者直接累加所有 A 股成交额
            total_amount_all = up_down["成交额"].sum()
            result["volume_str"] = f"{total_amount_all / 100000000:.0f}亿"

        except Exception as e:
            print(f"获取市场概览失败: {e}")
            result["error"] = str(e)

        return result

    @staticmethod
    @cached(
        "market:sector_top",
        ttl=settings.CACHE_TTL["sector_top"],
        stale_ttl=settings.CACHE_TTL["sector_top"] * settings.STALE_TTL_RATIO,
    )
    def get_sector_top(n: int = 5) -> List[Dict]:
        """
        获取领涨行业

        缓存: 60分钟 TTL + 120分钟 Stale
        """
        try:
            # 使用共享数据提供层（带重试和节流）
            df = data_provider.get_board_industry_name()
            if "涨跌幅" in df.columns:
                df = df.sort_values("涨跌幅", ascending=False).head(n)

            return df[["板块名称", "涨跌幅", "领涨股票", "领涨股票-涨跌幅"]].to_dict(
                "records"
            )
        except Exception:
            return []

    @staticmethod
    @cached(
        "market:board_cons",
        ttl=settings.CACHE_TTL["board_cons"],
        stale_ttl=settings.CACHE_TTL["board_cons"] * settings.STALE_TTL_RATIO,
    )
    def _get_board_cons(board_code: str) -> List[Dict]:
        """获取板块成分股（带缓存）"""
        try:
            # 使用带重试的调用
            cons = akshare_call_with_retry(ak.stock_board_industry_cons_em, symbol=board_code)
            if not cons.empty and "涨跌幅" in cons.columns:
                return cons[["名称", "涨跌幅"]].to_dict(orient="records")
        except Exception as e:
            print(f"获取板块成分股失败 [{board_code}]: {e}")
        return []

    @staticmethod
    @cached(
        "market:sector_bottom",
        ttl=settings.CACHE_TTL["sector_bottom"],
        stale_ttl=settings.CACHE_TTL["sector_bottom"] * settings.STALE_TTL_RATIO,
    )
    def get_sector_bottom(n: int = 5) -> List[Dict]:
        """
        获取领跌行业 (并获取该行业内跌幅最大的股票)

        缓存: 60分钟 TTL + 120分钟 Stale
        """
        try:
            # 使用共享数据提供层（带重试和节流）
            df = data_provider.get_board_industry_name()
            if "涨跌幅" in df.columns:
                # 获取跌幅榜前 N
                df_bottom = df.sort_values("涨跌幅", ascending=True).head(n)

                results = []
                for _, row in df_bottom.iterrows():
                    item = {
                        "板块名称": row["板块名称"],
                        "涨跌幅": row["涨跌幅"],
                        # 默认先用领涨的垫底（万一获取成分股失败）
                        "领涨股票": row["领涨股票"],
                        "领涨股票-涨跌幅": row["领涨股票-涨跌幅"],
                    }

                    # 尝试获取该板块成分股以找到领跌股
                    try:
                        board_code = row["板块代码"]
                        # 获取板块成分股 (使用缓存方法)
                        # cons = ak.stock_board_industry_cons_em(symbol=board_code)
                        cons_list = MarketAnalysis._get_board_cons(board_code)

                        if cons_list:
                            # 找跌得最惨的 (在内存中排序)
                            cons_list.sort(key=lambda x: x["涨跌幅"])
                            worst_stock = cons_list[0]
                            item["领涨股票"] = worst_stock["名称"]
                            item["领涨股票-涨跌幅"] = worst_stock["涨跌幅"]
                    except Exception as e:
                        print(f"处理板块成分股失败 [{row['板块名称']}]: {e}")
                    results.append(item)

                return results

            return []
        except Exception as e:
            print(f"获取领跌行业失败: {e}")
            return []


if __name__ == "__main__":
    print(MarketAnalysis.get_market_overview_v2())
