"""QDII 被动基金模块 (纳斯达克100 & 标普500 场外 A类基金)

此模块提供中国国内跟踪纳斯达克100与标普500的被动 QDII 场外基金数据（仅收录 A类主份额）。
包含：排名、基金代码、基金名称、综合费率、近一年收益、跟踪指数、跟踪偏离度、成立时间。
数据按 24 小时 (86400秒) 缓存一次。
"""

from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import requests
import re
import bs4
import pandas as pd
import akshare as ak
from ..core.cache import cached
from ..core.utils import akshare_call_with_retry, safe_float, fetch_url_via_proxy

# 目标 QDII 基金基础元数据注册表 (纳斯达克100 与 标普500 场外 A类基金，提供基准行情与后备数据)
QDII_FUND_METADATA: List[Dict[str, Any]] = [
    # --- 纳斯达克 100 场外 QDII (A类) ---
    {
        "code": "040046",
        "name": "华安纳斯达克100ETF联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.80%",
        "tracking_error": "0.35%",
        "inception_date": "2013-08-02",
        "default_return_1y": 15.79,
        "default_nav": 7.9540,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 91.18, "cash_pct": 8.82, "bond_pct": 0.0},
    },
    {
        "code": "019172",
        "name": "摩根纳斯达克100指数(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.60%",
        "tracking_error": "0.30%",
        "inception_date": "2023-09-06",
        "default_return_1y": 15.76,
        "default_nav": 1.6955,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 90.03, "cash_pct": 9.29, "bond_pct": 0.0},
    },
    {
        "code": "019547",
        "name": "招商纳斯达克100ETF发起式联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.65%",
        "tracking_error": "0.28%",
        "inception_date": "2023-11-15",
        "default_return_1y": 15.35,
        "default_nav": 1.5223,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 93.39, "cash_pct": 6.50, "bond_pct": 0.11},
    },
    {
        "code": "539001",
        "name": "建信纳斯达克100指数(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "1.00%",
        "tracking_error": "0.33%",
        "inception_date": "2021-09-29",
        "default_return_1y": 15.33,
        "default_nav": 3.3468,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 89.10, "cash_pct": 8.86, "bond_pct": 0.0},
    },
    {
        "code": "270042",
        "name": "广发纳斯达克100ETF联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "1.00%",
        "tracking_error": "0.32%",
        "inception_date": "2012-08-15",
        "default_return_1y": 15.27,
        "default_nav": 7.9076,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 90.96, "cash_pct": 9.04, "bond_pct": 0.0},
    },
    {
        "code": "019441",
        "name": "万家纳斯达克100指数发起式(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.65%",
        "tracking_error": "0.29%",
        "inception_date": "2023-10-25",
        "default_return_1y": 15.23,
        "default_nav": 1.6285,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 92.56, "cash_pct": 5.37, "bond_pct": 0.0},
    },
    {
        "code": "019736",
        "name": "宝盈纳斯达克100指数发起(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.65%",
        "tracking_error": "0.31%",
        "inception_date": "2023-11-28",
        "default_return_1y": 15.19,
        "default_nav": 1.4426,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 93.15, "cash_pct": 7.26, "bond_pct": 0.0},
    },
    {
        "code": "000834",
        "name": "大成纳斯达克100ETF联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "1.00%",
        "tracking_error": "0.38%",
        "inception_date": "2014-11-13",
        "default_return_1y": 15.15,
        "default_nav": 6.1081,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 90.09, "cash_pct": 9.91, "bond_pct": 0.0},
    },
    {
        "code": "016452",
        "name": "南方纳斯达克100指数发起(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.65%",
        "tracking_error": "0.27%",
        "inception_date": "2023-03-08",
        "default_return_1y": 15.01,
        "default_nav": 2.2147,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 87.41, "cash_pct": 7.99, "bond_pct": 0.0},
    },
    {
        "code": "019524",
        "name": "华泰柏瑞纳斯达克100ETF发起式联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.65%",
        "tracking_error": "0.26%",
        "inception_date": "2023-12-19",
        "default_return_1y": 14.82,
        "default_nav": 1.5972,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 90.89, "cash_pct": 9.11, "bond_pct": 0.0},
    },
    {
        "code": "160213",
        "name": "国泰纳斯达克100(QDII-LOF)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "1.00%",
        "tracking_error": "0.35%",
        "inception_date": "2010-04-29",
        "default_return_1y": 15.50,
        "default_nav": 7.4210,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 79.63, "cash_pct": 18.10, "bond_pct": 0.0},
    },
    {
        "code": "161130",
        "name": "易方达纳斯达克100(QDII-LOF)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.60%",
        "tracking_error": "0.32%",
        "inception_date": "2017-06-21",
        "default_return_1y": 15.45,
        "default_nav": 4.0846,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 93.25, "cash_pct": 3.69, "bond_pct": 3.06},
    },
    {
        "code": "018966",
        "name": "汇添富纳斯达克100ETF发起式联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.65%",
        "tracking_error": "0.30%",
        "inception_date": "2023-08-22",
        "default_return_1y": 13.72,
        "default_nav": 1.5921,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 89.44, "cash_pct": 9.92, "bond_pct": 0.64},
    },

    # --- 标普 500 场外 QDII (A类) ---
    {
        "code": "161125",
        "name": "易方达标普500指数(QDII-LOF)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "1.00%",
        "tracking_error": "0.30%",
        "inception_date": "2016-12-02",
        "default_return_1y": 11.10,
        "default_nav": 3.1377,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 89.10, "cash_pct": 1.28, "bond_pct": 7.93},
    },
    {
        "code": "050025",
        "name": "博时标普500ETF联接(QDII)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "0.80%",
        "tracking_error": "0.30%",
        "inception_date": "2012-04-25",
        "default_return_1y": 11.20,
        "default_nav": 5.5649,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 92.49, "cash_pct": 7.51, "bond_pct": 0.0},
    },
    {
        "code": "017641",
        "name": "摩根标普500指数(QDII)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "0.65%",
        "tracking_error": "0.28%",
        "inception_date": "2023-01-18",
        "default_return_1y": 10.70,
        "default_nav": 1.6496,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 94.03, "cash_pct": 6.90, "bond_pct": 0.0},
    },
    {
        "code": "007308",
        "name": "汇添富标普500指数(QDII)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "1.40%",
        "tracking_error": "0.35%",
        "inception_date": "2019-06-25",
        "default_return_1y": 10.85,
        "default_nav": 1.8540,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 91.89, "cash_pct": 8.71, "bond_pct": 0.0},
    },
    {
        "code": "018043",
        "name": "天弘纳斯达克100指数发起(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.60%",
        "tracking_error": "0.25%",
        "inception_date": "2023-04-18",
        "default_return_1y": 15.40,
        "default_nav": 1.8664,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 88.96, "cash_pct": 4.21, "bond_pct": 2.77},
    },
    {
        "code": "016055",
        "name": "博时纳斯达克100ETF发起式联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.65%",
        "tracking_error": "0.26%",
        "inception_date": "2022-08-17",
        "default_return_1y": 15.20,
        "default_nav": 1.8130,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 93.24, "cash_pct": 6.76, "bond_pct": 0.0},
    },
    {
        "code": "009975",
        "name": "工银标普500ETF联接(QDII)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "1.60%",
        "tracking_error": "0.32%",
        "inception_date": "2020-08-19",
        "default_return_1y": 10.90,
        "default_nav": 2.1250,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 94.63, "cash_pct": 7.15, "bond_pct": 0.0},
    },
    {
        "code": "017056",
        "name": "景顺长城标普500ETF发起联接(QDII)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "0.60%",
        "tracking_error": "0.26%",
        "inception_date": "2023-06-06",
        "default_return_1y": 11.35,
        "default_nav": 1.5120,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 92.80, "cash_pct": 7.20, "bond_pct": 0.0},
    },
    {
        "code": "018703",
        "name": "华夏标普500ETF发起式联接(QDII)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "0.50%",
        "tracking_error": "0.24%",
        "inception_date": "2023-09-08",
        "default_return_1y": 11.40,
        "default_nav": 1.4980,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 94.20, "cash_pct": 5.80, "bond_pct": 0.0},
    },

    # --- 主动型 QDII 精选 (参考 DCA HUB 推荐列表) ---
    {
        "code": "019043",
        "name": "华泰柏瑞中韩半导体发起联接(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "0.60%",
        "tracking_error": "--",
        "inception_date": "2023-09-05",
        "default_return_1y": 38.50,
        "default_nav": 1.0314,
        "default_nav_date": "2026-07-27",
        "default_asset_allocation": {"stock_pct": 90.0, "stock_cn_pct": 50.0, "stock_other_pct": 40.0, "cash_pct": 10.0, "bond_pct": 0.0},
    },
    {
        "code": "270023",
        "name": "广发全球精选股票(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2010-08-18",
        "default_return_1y": 45.95,
        "default_nav": 6.224,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 93.8, "stock_us_pct": 66.4, "stock_hk_pct": 21.4, "stock_cn_pct": 6.0, "cash_pct": 6.2, "bond_pct": 0.0},
    },
    {
        "code": "000043",
        "name": "嘉实美国成长股票(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2013-06-14",
        "default_return_1y": 15.62,
        "default_nav": 6.048,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 91.66, "stock_us_pct": 91.66, "stock_hk_pct": 0.0, "cash_pct": 8.34, "bond_pct": 0.0},
    },
    {
        "code": "017436",
        "name": "华宝纳斯达克精选股票发起(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2023-03-02",
        "default_return_1y": 6.4,
        "default_nav": 2.1777,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 92.5, "stock_us_pct": 92.5, "stock_hk_pct": 0.0, "cash_pct": 7.5, "bond_pct": 0.0},
    },
    {
        "code": "012920",
        "name": "易方达全球成长精选混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2022-01-11",
        "default_return_1y": 34.2,
        "default_nav": 4.3588,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 88.5, "stock_us_pct": 65.2, "stock_hk_pct": 23.3, "cash_pct": 11.5, "bond_pct": 0.0},
    },
    {
        "code": "005698",
        "name": "华夏全球科技先锋混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2018-04-17",
        "default_return_1y": 43.83,
        "default_nav": 2.7838,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 88.5, "stock_us_pct": 76.2, "stock_hk_pct": 12.3, "cash_pct": 11.5, "bond_pct": 0.0},
    },
    {
        "code": "006373",
        "name": "国富全球科技互联混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2018-11-20",
        "default_return_1y": 72.5,
        "default_nav": 6.7334,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 88.61, "stock_us_pct": 65.3, "stock_hk_pct": 23.31, "cash_pct": 11.39, "bond_pct": 0.0},
    },
    {
        "code": "001668",
        "name": "汇添富全球移动互联混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2017-01-25",
        "default_return_1y": 20.45,
        "default_nav": 5.039,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 88.2, "stock_us_pct": 61.4, "stock_hk_pct": 26.8, "cash_pct": 11.8, "bond_pct": 0.0},
    },

    {
        "code": "539002",
        "name": "建信新兴市场混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2011-06-21",
        "default_return_1y": 96.26,
        "default_nav": 2.312,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 80.24, "stock_us_pct": 52.4, "stock_hk_pct": 20.0, "stock_other_pct": 7.84, "cash_pct": 19.76, "bond_pct": 0.0},
    },
    {
        "code": "020565",
        "name": "路博迈全球智能科技股票发起(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "0.40%",
        "tracking_error": "--",
        "inception_date": "2024-01-29",
        "default_return_1y": 17.67,
        "default_nav": 1.1767,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 90.2, "stock_us_pct": 82.5, "stock_hk_pct": 7.7, "cash_pct": 9.8, "bond_pct": 0.0},
    },
    {
        "code": "501226",
        "name": "长城全球新能源车股票发起(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2023-05-18",
        "default_return_1y": 55.42,
        "default_nav": 2.6025,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 86.4, "stock_us_pct": 48.2, "stock_hk_pct": 38.2, "cash_pct": 13.6, "bond_pct": 0.0},
    },
    {
        "code": "017730",
        "name": "嘉实全球产业升级股票发起(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2023-02-14",
        "default_return_1y": 113.55,
        "default_nav": 4.0901,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 79.68, "stock_us_pct": 72.4, "stock_hk_pct": 7.28, "cash_pct": 10.34, "bond_pct": 0.0},
    },
    {
        "code": "100055",
        "name": "富国全球科技互联网股票(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2018-07-25",
        "default_return_1y": 68.04,
        "default_nav": 5.2659,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 89.18, "stock_us_pct": 71.1, "stock_hk_pct": 18.08, "cash_pct": 10.82, "bond_pct": 0.0},
    },
    {
        "code": "501312",
        "name": "华宝海外科技股票(QDII-LOF)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.20%",
        "tracking_error": "--",
        "inception_date": "2023-04-11",
        "default_return_1y": 16.7,
        "default_nav": 2.1592,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 92.1, "stock_us_pct": 85.3, "stock_hk_pct": 6.8, "cash_pct": 7.9, "bond_pct": 0.0},
    },
    {
        "code": "002891",
        "name": "华夏移动互联混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2016-12-14",
        "default_return_1y": 89.09,
        "default_nav": 2.564,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 91.58, "stock_us_pct": 48.6, "stock_hk_pct": 34.5, "stock_cn_pct": 8.48, "cash_pct": 8.42, "bond_pct": 0.0},
    },
    {
        "code": "457001",
        "name": "国富亚洲机会股票(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2012-02-01",
        "default_return_1y": 89.9,
        "default_nav": 2.7733,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 77.35, "stock_us_pct": 25.1, "stock_hk_pct": 52.25, "cash_pct": 12.82, "bond_pct": 0.0},
    },
    {
        "code": "016664",
        "name": "天弘全球高端制造混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2022-11-29",
        "default_return_1y": 107.84,
        "default_nav": 2.7855,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 77.38, "stock_us_pct": 60.1, "stock_hk_pct": 7.28, "stock_cn_pct": 10.0, "cash_pct": 8.33, "bond_pct": 0.0},
    },
    {
        "code": "008253",
        "name": "华宝致远混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2019-12-25",
        "default_return_1y": 52.33,
        "default_nav": 1.7685,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 87.2, "stock_us_pct": 62.4, "stock_hk_pct": 24.8, "cash_pct": 12.8, "bond_pct": 0.0},
    },
    {
        "code": "017144",
        "name": "华宝海外新能源汽车股票发起(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2023-06-30",
        "default_return_1y": -9.56,
        "default_nav": 1.4902,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 85.2, "stock_us_pct": 45.1, "stock_hk_pct": 40.1, "cash_pct": 14.8, "bond_pct": 0.0},
    },
    {
        "code": "018229",
        "name": "易方达全球优质企业混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2023-04-12",
        "default_return_1y": 64.18,
        "default_nav": 2.1056,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 74.55, "stock_us_pct": 52.1, "stock_hk_pct": 22.45, "cash_pct": 25.45, "bond_pct": 0.0},
    },
    {
        "code": "519696",
        "name": "交银环球精选混合(QDII)A",
        "index_code": "ACTIVE",
        "index_name": "主动管理型",
        "type": "active",
        "fee_rate": "1.40%",
        "tracking_error": "--",
        "inception_date": "2008-06-19",
        "default_return_1y": 10.13,
        "default_nav": 2.8848,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 84.3, "stock_us_pct": 51.1, "stock_hk_pct": 33.2, "cash_pct": 15.7, "bond_pct": 0.0},
    },
]


def fetch_sina_fund_navs(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """使用新浪财经 API 极速批量获取基金最新净值 (毫秒级响应，防封禁)"""
    res: Dict[str, Dict[str, Any]] = {}
    try:
        query = ",".join([f"fu_{c}" for c in codes])
        url = f"http://hq.sinajs.cn/list={query}"
        headers = {"Referer": "http://finance.sina.com.cn"}
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            for line in r.text.strip().split("\n"):
                if "=" in line and '""' not in line:
                    parts = line.split("=")
                    code = parts[0].strip().replace("var hq_str_fu_", "")
                    content = parts[1].strip('";').split(",")
                    if len(content) >= 8 and content[2]:
                        try:
                            nav_val = float(content[2])
                            date_str = content[7]
                            res[code] = {
                                "nav": nav_val,
                                "nav_date": date_str
                            }
                        except (ValueError, IndexError):
                            pass
    except Exception as e:
        print(f"⚠️ 新浪基金行情抓取跳过: {e}")
    return res


def fetch_us_index_returns() -> Dict[str, Dict[str, Any]]:
    """获取美股两大原生指数 (纳斯达克100 & 标普500) 近1年收益率"""
    benchmarks = {
        "NDX": {"name": "纳斯达克100 原生指数", "return_1y": 21.14},
        "SPX": {"name": "标普500 原生指数", "return_1y": 16.48},
    }
    try:
        df_ndx = akshare_call_with_retry(ak.index_us_stock_sina, symbol=".NDX")
        if df_ndx is not None and len(df_ndx) >= 252:
            c = float(df_ndx.iloc[-1]["close"])
            prev = float(df_ndx.iloc[-252]["close"])
            benchmarks["NDX"]["return_1y"] = round(((c - prev) / prev) * 100, 2)
    except Exception as e:
        print(f"⚠️ NDX 1Y Return fetch fallback: {e}")

    try:
        df_spx = akshare_call_with_retry(ak.index_us_stock_sina, symbol=".INX")
        if df_spx is not None and len(df_spx) >= 252:
            c = float(df_spx.iloc[-1]["close"])
            prev = float(df_spx.iloc[-252]["close"])
            benchmarks["SPX"]["return_1y"] = round(((c - prev) / prev) * 100, 2)
    except Exception as e:
        print(f"⚠️ SPX 1Y Return fetch fallback: {e}")

    return benchmarks


def fetch_fund_asset_allocation(session: requests.Session, code: str) -> Optional[Dict[str, Any]]:
    """获取指定 QDII 场外联接/被动基金的最新真实资产/持仓配置（股票/权益 %、现金/货币 %）"""
    try:
        url = f"https://fundf10.eastmoney.com/zcpz_{code}.html"
        res = fetch_url_via_proxy(url, session=session, timeout=6)
        if not res or res.status_code != 200:
            return None
        soup = bs4.BeautifulSoup(res.content.decode("utf-8", errors="ignore"), "html.parser")
        table = soup.find("table", class_="tzxq")
        if not table:
            return None
        rows = table.find_all("tr")
        if len(rows) < 2:
            return None

        def parse_pct(val: str) -> float:
            try:
                return float(val.replace("%", "").strip())
            except (ValueError, AttributeError):
                return 0.0

        # 筛选最新的定期季报 (避开基金成立建仓期的临时公告 99% 现金数据)
        selected_row = None
        for tr in rows[1:]:
            cells = [td.text.strip() for td in tr.find_all(["td", "th"])]
            if len(cells) >= 4:
                date_str = cells[0]
                cash = parse_pct(cells[3])
                if re.search(r"(03-31|06-30|09-30|12-31)$", date_str) and cash < 50.0:
                    selected_row = cells
                    break
        if not selected_row:
            selected_row = [td.text.strip() for td in rows[1].find_all(["td", "th"])]

        cash_val = parse_pct(selected_row[3])
        # 被动 QDII 权益/股票/目标ETF持仓 = 100% - 现金货币比例
        equity_val = max(0.0, round(100.0 - cash_val, 2))

        return {
            "stock_pct": equity_val,
            "cash_pct": cash_val,
            "bond_pct": 0.0,
            "report_date": selected_row[0]
        }
    except Exception as e:
        print(f"⚠️ 资产配置获取跳过 [{code}]: {e}")
        return None


def fetch_fund_fee_rate(session: requests.Session, code: str) -> Optional[str]:
    """获取指定基金的最新综合运营费率（管理费率 + 托管费率 + 销售服务费率）"""
    try:
        url = f"https://fundf10.eastmoney.com/jjfl_{code}.html"
        res = fetch_url_via_proxy(url, session=session, timeout=6)
        if not res or res.status_code != 200:
            return None
        soup = bs4.BeautifulSoup(res.content.decode("utf-8", errors="ignore"), "html.parser")

        def parse_fee(text: str, keyword: str) -> float:
            m = re.search(keyword + r"[^\d]*(\d+\.\d+)%", text)
            return float(m.group(1)) if m else 0.0

        m_val, c_val, s_val = 0.0, 0.0, 0.0
        for box in soup.find_all("div", class_="box"):
            txt = box.text
            if "运作费用" in txt:
                m_val = parse_fee(txt, "管理费率")
                c_val = parse_fee(txt, "托管费率")
                s_val = parse_fee(txt, "销售服务费率")
                break
        total = round(m_val + c_val + s_val, 2)
        if total > 0:
            return f"{total:.2f}%"
        return None
    except Exception as e:
        print(f"⚠️ 费率获取跳过 [{code}]: {e}")
        return None


@cached("qdii:passive_funds_v19", ttl=86400)
def get_qdii_passive_funds() -> Dict[str, Any]:
    """获取国内纳斯达克100 & 标普500 场外被动 QDII A类基金数据列表

    数据一天刷新一次 (86400s)。包含标的指数原生收益率对标、实时排行、净值、综合费率与真实资产配置仓位。
    """
    rank_map: Dict[str, Dict[str, Any]] = {}
    target_codes = [item["code"] for item in QDII_FUND_METADATA]

    # 1. 尝试新浪行情极速获取实时净值
    sina_nav_map = fetch_sina_fund_navs(target_codes)
    for c, info in sina_nav_map.items():
        rank_map[c] = {
            "nav": info.get("nav"),
            "nav_date": info.get("nav_date"),
        }

    # 2. 尝试 AKShare / 东方财富获取实时近1年收益率
    try:
        df_rank = akshare_call_with_retry(ak.fund_open_fund_rank_em, symbol="QDII")
        if df_rank is not None and not df_rank.empty:
            for _, row in df_rank.iterrows():
                code = str(row.get("基金代码", "")).zfill(6)
                r_1y = safe_float(row.get("近1年"), default=None)
                nav = safe_float(row.get("单位净值"), default=None)
                date_str = str(row.get("日期", ""))

                if code not in rank_map:
                    rank_map[code] = {}
                if r_1y is not None:
                    rank_map[code]["return_1y"] = r_1y
                if nav is not None and "nav" not in rank_map[code]:
                    rank_map[code]["nav"] = nav
                    rank_map[code]["nav_date"] = date_str
    except Exception as err:
        print(f"⚠️ 东财实时排行获取跳过 (已使用高质量基准/新浪行情): {err}")

    # 3. 并发获取所有 QDII 基金的真实资产配置仓位与动态费率
    alloc_map: Dict[str, Dict[str, Any]] = {}
    fee_map: Dict[str, str] = {}
    try:
        session = requests.Session()
        with ThreadPoolExecutor(max_workers=12) as executor:
            alloc_futures = {executor.submit(fetch_fund_asset_allocation, session, code): code for code in target_codes}
            fee_futures = {executor.submit(fetch_fund_fee_rate, session, code): code for code in target_codes}
            
            for future in alloc_futures:
                c = alloc_futures[future]
                try:
                    res = future.result()
                    if res:
                        alloc_map[c] = res
                except Exception:
                    pass

            for future in fee_futures:
                c = fee_futures[future]
                try:
                    res = future.result()
                    if res:
                        fee_map[c] = res
                except Exception:
                    pass
    except Exception as err:
        print(f"⚠️ 资产配置与费率并发抓取跳过: {err}")

    # 4. 获取原生指数收益对标基准
    benchmarks = fetch_us_index_returns()

    funds_list: List[Dict[str, Any]] = []

    for item in QDII_FUND_METADATA:
        code = item["code"]
        live_data = rank_map.get(code, {})

        r_1y = live_data.get("return_1y")
        nav_val = live_data.get("nav")
        nav_date = live_data.get("nav_date")

        final_r1y = r_1y if r_1y is not None else item["default_return_1y"]
        final_nav = nav_val if nav_val is not None else item["default_nav"]
        final_date = nav_date if nav_date else item["default_nav_date"]

        # 优先使用实时并发抓取的仓位配置与费率，若失败退回该基金真实的元数据配置
        default_alloc = item.get("default_asset_allocation", {})
        live_alloc = alloc_map.get(code)
        if live_alloc:
            asset_alloc = dict(live_alloc)
            if any(k in default_alloc for k in ["stock_us_pct", "stock_hk_pct", "stock_cn_pct", "stock_other_pct"]):
                def_total_stock = default_alloc.get("stock_pct", 0.0)
                if def_total_stock > 0 and live_alloc.get("stock_pct", 0) > 0:
                    live_stock = live_alloc["stock_pct"]
                    for k in ["stock_us_pct", "stock_hk_pct", "stock_cn_pct", "stock_other_pct"]:
                        if k in default_alloc:
                            asset_alloc[k] = round(live_stock * (default_alloc[k] / def_total_stock), 1)
                else:
                    for k in ["stock_us_pct", "stock_hk_pct", "stock_cn_pct", "stock_other_pct"]:
                        if k in default_alloc:
                            asset_alloc[k] = default_alloc[k]
        else:
            asset_alloc = default_alloc

        fee_rate = fee_map.get(code) or item["fee_rate"]

        funds_list.append({
            "code": code,
            "name": item["name"],
            "index_code": item["index_code"],
            "index_name": item["index_name"],
            "fee_rate": fee_rate,
            "tracking_error": item["tracking_error"],
            "inception_date": item["inception_date"],
            "nav": final_nav,
            "nav_date": final_date,
            "return_1y": final_r1y,
            "asset_allocation": asset_alloc,
        })

    # 按 近1年收益 (return_1y) 降序排序
    funds_list.sort(key=lambda x: x["return_1y"] if x["return_1y"] is not None else -999.0, reverse=True)

    for rank_idx, fund in enumerate(funds_list, start=1):
        fund["rank"] = rank_idx

    return {
        "status": "ok",
        "count": len(funds_list),
        "benchmarks": benchmarks,
        "funds": funds_list,
        "update_strategy": "daily (24h cache)"
    }


@cached("qdii:top_holdings_v3", ttl=86400 * 7, stale_ttl=86400 * 30)
def get_qdii_top_holdings(code: str) -> Dict[str, Any]:
    """获取 QDII 基金最新披露的前十大重仓股票列表"""
    try:
        session = requests.Session()
        url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=10"
        
        # 优先使用代理获取
        res = fetch_url_via_proxy(url, session=session, timeout=6)
        
        # 代理失败或超时，降级尝试直连
        if res is None:
            try:
                res = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            except Exception:
                pass
                
        if res is None:
            return {"status": "error", "error": True, "message": f"网络请求超时 (code: {code})", "holdings": []}
            
        if res.status_code == 404:
            # 404 表示该基金无相关持仓披露页面 (如某些联接基金或刚成立无数据)
            # 正常返回空持仓，让其进入缓存以避免持续报错请求
            return {"status": "ok", "code": code, "report_date": "暂无季报", "count": 0, "holdings": []}
            
        if res.status_code != 200:
            return {"status": "error", "error": True, "message": f"接口异常 HTTP {res.status_code} (code: {code})", "holdings": []}

        match = re.search(r'content:\"(.*?)\"', res.text, re.DOTALL)
        if not match:
            return {"status": "ok", "code": code, "report_date": "暂无季报", "count": 0, "holdings": []}

        html_content = match.group(1)
        soup = bs4.BeautifulSoup(html_content, "html.parser")
        date_font = soup.find("font", class_="px12")
        report_date = date_font.text.strip() if date_font else "最新季报"

        table = soup.find("table", class_="tzxq")
        if not table:
            return {"status": "ok", "code": code, "report_date": report_date, "count": 0, "holdings": []}

        holdings = []
        for tr in table.find_all("tr")[1:]:
            cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
            if len(cols) >= 7:
                rank_str = cols[0]
                stock_code = cols[1]
                stock_name = cols[2]
                ratio_pct_str = cols[6]
                share_amount = cols[7] if len(cols) > 7 else "--"
                market_value = cols[8] if len(cols) > 8 else "--"

                try:
                    ratio_val = float(ratio_pct_str.replace("%", "").strip())
                except ValueError:
                    ratio_val = 0.0

                holdings.append({
                    "rank": rank_str,
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "ratio_pct": ratio_pct_str,
                    "ratio_val": ratio_val,
                    "share_amount": share_amount,
                    "market_value": market_value
                })

        return {
            "status": "ok",
            "code": code,
            "report_date": report_date,
            "count": len(holdings),
            "holdings": holdings
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "holdings": []}

