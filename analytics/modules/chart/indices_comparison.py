"""
全球主要国家与市场指数对比模块
支持多国核心大盘指数的历史日线收盘价获取、多周期收益率计算、百分比归一化对比
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pytz
import numpy as np
import pandas as pd
import akshare as ak

from ...core.cache import cached
from ...core.utils import safe_float, akshare_call_with_retry
from ...core.logger import logger

# 14 大核心指数元数据配置
INDEX_CONFIGS = [
    {
        "code": "NDX",
        "name": "纳指100",
        "full_name": "纳斯达克100",
        "region": "US",
        "flag": "🇺🇸",
        "color": "#3B82F6",  # 科技蓝
        "default_selected": True,
        "type": "us",
        "symbol": ".NDX",
    },
    {
        "code": "SP500",
        "name": "标普500",
        "full_name": "标普500",
        "region": "US",
        "flag": "🇺🇸",
        "color": "#6366F1",  # 靛青紫
        "default_selected": True,
        "type": "us",
        "symbol": ".INX",
    },
    {
        "code": "DJI",
        "name": "道琼斯",
        "full_name": "道琼斯工业平均指数",
        "region": "US",
        "flag": "🇺🇸",
        "color": "#8B5CF6",  # 紫色
        "default_selected": False,
        "type": "us",
        "symbol": ".DJI",
    },
    {
        "code": "SH000300",
        "name": "沪深300",
        "full_name": "沪深300指数",
        "region": "CN",
        "flag": "🇨🇳",
        "color": "#EF4444",  # 中国红
        "default_selected": True,
        "type": "cn",
        "symbol": "sh000300",
    },
    {
        "code": "SH000001",
        "name": "上证指数",
        "full_name": "上证综合指数",
        "region": "CN",
        "flag": "🇨🇳",
        "color": "#F97316",  # 橙红
        "default_selected": False,
        "type": "cn",
        "symbol": "sh000001",
    },
    {
        "code": "SH000688",
        "name": "科创50",
        "full_name": "科创50指数",
        "region": "CN",
        "flag": "🇨🇳",
        "color": "#EC4899",  # 洋红
        "default_selected": False,
        "type": "cn",
        "symbol": "sh000688",
    },
    {
        "code": "HSI",
        "name": "恒生指数",
        "full_name": "香港恒生指数",
        "region": "HK",
        "flag": "🇭🇰",
        "color": "#10B981",  # 翡翠绿
        "default_selected": True,
        "type": "hk",
        "symbol": "HSI",
    },
    {
        "code": "HSTECH",
        "name": "恒生科技",
        "full_name": "恒生科技指数",
        "region": "HK",
        "flag": "🇭🇰",
        "color": "#14B8A6",  # 青绿
        "default_selected": False,
        "type": "hk",
        "symbol": "HSTECH",
    },
    {
        "code": "N225",
        "name": "日经225",
        "full_name": "日经225指数",
        "region": "JP",
        "flag": "🇯🇵",
        "color": "#F59E0B",  # 琥珀黄
        "default_selected": True,
        "type": "global",
        "symbol": "日经225指数",
    },
    {
        "code": "KOSPI",
        "name": "韩国综合",
        "full_name": "首尔综合指数",
        "region": "KR",
        "flag": "🇰🇷",
        "color": "#84CC16",  # 酸橙绿
        "default_selected": False,
        "type": "global",
        "symbol": "首尔综合指数",
    },
    {
        "code": "DAX",
        "name": "德国DAX",
        "full_name": "德国DAX30指数",
        "region": "DE",
        "flag": "🇩🇪",
        "color": "#06B6D4",  # 青蓝
        "default_selected": False,
        "type": "global",
        "symbol": "德国DAX 30种股价指数",
    },
    {
        "code": "FTSE",
        "name": "英国富时",
        "full_name": "英国富时100指数",
        "region": "UK",
        "flag": "🇬🇧",
        "color": "#64748B",  # 蓝灰
        "default_selected": False,
        "type": "global",
        "symbol": "英国富时100指数",
    },
    {
        "code": "CAC",
        "name": "法国CAC",
        "full_name": "法国CAC40指数",
        "region": "FR",
        "flag": "🇫🇷",
        "color": "#A855F7",  # 紫罗兰
        "default_selected": False,
        "type": "global",
        "symbol": "法CAC40指数",
    },
    {
        "code": "SENSEX",
        "name": "印度SENSEX",
        "full_name": "印度孟买SENSEX指数",
        "region": "IN",
        "flag": "🇮🇳",
        "color": "#D97706",  # 铜黄
        "default_selected": False,
        "type": "global",
        "symbol": "印度孟买SENSEX指数",
    },
]


def _calc_return_pct(current_val: float, base_val: float) -> Optional[float]:
    """计算百分比涨跌幅"""
    if base_val is None or base_val <= 0:
        return None
    return round((current_val - base_val) / base_val * 100, 2)


def fetch_single_index(cfg: Dict[str, Any], cutoff_date: str) -> Optional[Dict[str, Any]]:
    """
    抓取单个指数的历史数据并计算多周期收益率
    """
    code = cfg["code"]
    name = cfg["name"]
    source_type = cfg["type"]
    symbol = cfg["symbol"]

    try:
        df: Optional[pd.DataFrame] = None
        if source_type == "us":
            df = akshare_call_with_retry(
                ak.index_us_stock_sina, symbol=symbol, max_retries=2, use_throttle=False
            )
        elif source_type == "hk":
            df = akshare_call_with_retry(
                ak.stock_hk_index_daily_sina, symbol=symbol, max_retries=2, use_throttle=False
            )
        elif source_type == "global":
            df = akshare_call_with_retry(
                ak.index_global_hist_sina, symbol=symbol, max_retries=2, use_throttle=False
            )
        elif source_type == "cn":
            df = akshare_call_with_retry(
                ak.stock_zh_index_daily, symbol=symbol, max_retries=2, use_throttle=False
            )

        if df is None or df.empty:
            logger.warning(f"[IndicesComparison] 未能获取指数 {name} ({code}) 的数据")
            return None

        # 统一列名与清洗
        if "date" not in df.columns and "trade_date" in df.columns:
            df = df.rename(columns={"trade_date": "date"})

        df["date_str"] = df["date"].astype(str).str[:10]
        df["close_val"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna(subset=["date_str", "close_val"])
        df = df.sort_values("date_str").reset_index(drop=True)

        if df.empty:
            return None

        # 过滤 cutoff_date 之后的数据，但需保留足够的数据来计算 1Y/3Y/YTD
        # 因此我们在计算完指标之后再切片 history
        latest_row = df.iloc[-1]
        latest_date = latest_row["date_str"]
        latest_close = float(latest_row["close_val"])

        current_year = int(latest_date[:4])

        def find_base_close(target_date_str: str) -> Optional[float]:
            sub = df[df["date_str"] <= target_date_str]
            if len(sub) == 0:
                return None
            return float(sub.iloc[-1]["close_val"])

        # 1. 计算 1D
        ret_1d = (
            _calc_return_pct(latest_close, float(df.iloc[-2]["close_val"]))
            if len(df) >= 2
            else None
        )

        # 2. 计算各周期收益率
        latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")

        d_1w = (latest_dt - timedelta(days=7)).strftime("%Y-%m-%d")
        ret_1w = _calc_return_pct(latest_close, find_base_close(d_1w))

        d_1m = (latest_dt - timedelta(days=30)).strftime("%Y-%m-%d")
        ret_1m = _calc_return_pct(latest_close, find_base_close(d_1m))

        d_3m = (latest_dt - timedelta(days=90)).strftime("%Y-%m-%d")
        ret_3m = _calc_return_pct(latest_close, find_base_close(d_3m))

        d_6m = (latest_dt - timedelta(days=180)).strftime("%Y-%m-%d")
        ret_6m = _calc_return_pct(latest_close, find_base_close(d_6m))

        # YTD: 上一年最后一个交易日
        d_ytd = f"{current_year - 1}-12-31"
        ret_ytd = _calc_return_pct(latest_close, find_base_close(d_ytd))

        d_1y = (latest_dt - timedelta(days=365)).strftime("%Y-%m-%d")
        ret_1y = _calc_return_pct(latest_close, find_base_close(d_1y))

        d_3y = (latest_dt - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
        ret_3y = _calc_return_pct(latest_close, find_base_close(d_3y))

        # 3. 截取近 3 年历史用于前端动态渲染
        df_history = df[df["date_str"] >= cutoff_date]
        history: List[List[Any]] = [
            [row["date_str"], round(float(row["close_val"]), 2)]
            for _, row in df_history.iterrows()
        ]

        return {
            "code": cfg["code"],
            "name": cfg["name"],
            "full_name": cfg["full_name"],
            "region": cfg["region"],
            "flag": cfg["flag"],
            "color": cfg["color"],
            "default_selected": cfg["default_selected"],
            "latest_date": latest_date,
            "latest_close": round(latest_close, 2),
            "history": history,
            "returns": {
                "1D": ret_1d,
                "1W": ret_1w,
                "1M": ret_1m,
                "3M": ret_3m,
                "6M": ret_6m,
                "YTD": ret_ytd,
                "1Y": ret_1y,
                "3Y": ret_3y,
            },
        }
    except Exception as e:
        logger.error(f"[IndicesComparison] 获取指数 {name} ({code}) 失败: {e}")
        return None


@cached("chart:indices_comparison:v1", ttl=1800, stale_ttl=86400, sync_on_cold=True)
def get_indices_comparison() -> Dict[str, Any]:
    """
    并发抓取全球 14 大核心指数历史数据，并返回归一化比对所需数据源
    """
    # 截取近 3 年多一点 (3年 + 1个月缓冲)
    cutoff_date = (datetime.now() - timedelta(days=365 * 3 + 35)).strftime("%Y-%m-%d")

    ordered_indices: List[Dict[str, Any]] = []

    for cfg in INDEX_CONFIGS:
        try:
            res = fetch_single_index(cfg, cutoff_date)
            if res:
                ordered_indices.append(res)
        except Exception as e:
            logger.error(f"[IndicesComparison] 获取指数异常 {cfg['name']}: {e}")

    beijing_tz = pytz.timezone("Asia/Shanghai")
    now_str = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "indices": ordered_indices,
        "count": len(ordered_indices),
        "updated_at": now_str,
    }
