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
import time
from datetime import datetime
import pandas as pd
import akshare as ak
from ..core.cache import cached, cache
from ..core.config import settings
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
    {
        "code": "001092",
        "name": "广发纳斯达克生物科技指数(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.80%",
        "tracking_error": "0.33%",
        "inception_date": "2015-03-30",
        "default_return_1y": 8.50,
        "default_nav": 1.5720,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 85.00, "cash_pct": 15.00, "bond_pct": 0.0},
        "tag": "生物科技",
    },
    {
        "code": "017894",
        "name": "汇添富纳斯达克生物科技ETF发起式联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.50%",
        "tracking_error": "0.30%",
        "inception_date": "2023-03-14",
        "default_return_1y": 11.50,
        "default_nav": 1.4740,
        "default_nav_date": "2026-08-03",
        "default_asset_allocation": {"stock_pct": 90.00, "cash_pct": 10.00, "bond_pct": 0.0},
        "tag": "生物科技",
    },
    {
        "code": "017436",
        "name": "华宝纳斯达克精选股票发起式(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "1.20%",
        "tracking_error": "0.40%",
        "inception_date": "2023-03-02",
        "default_return_1y": 35.20,
        "default_nav": 2.3255,
        "default_nav_date": "2026-08-04",
        "default_asset_allocation": {"stock_pct": 88.42, "cash_pct": 11.58, "bond_pct": 0.0},
        "tag": "风味纳指",
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
        "code": "018064",
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
    },    {
        "code": "016532",
        "name": "嘉实纳斯达克100ETF发起联接(QDII)A人民币",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.60%",
        "tracking_error": "0.32%",
        "inception_date": "2022-11-18",
        "default_return_1y": 18.44,
        "default_nav": 2.1243,
        "default_nav_date": "2026-08-03",
        "default_asset_allocation": {"stock_pct": 91.04, "cash_pct": 8.96, "bond_pct": 0.0},
    },
    {
        "code": "015299",
        "name": "华夏纳斯达克100ETF发起式联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳斯达克100",
        "fee_rate": "0.80%",
        "tracking_error": "0.29%",
        "inception_date": "2022-09-20",
        "default_return_1y": 18.10,
        "default_nav": 1.9916,
        "default_nav_date": "2026-08-03",
        "default_asset_allocation": {"stock_pct": 96.02, "cash_pct": 3.98, "bond_pct": 0.0},
    },
    {
        "code": "017091",
        "name": "景顺长城纳斯达克科技ETF联接(QDII)A",
        "index_code": "NDX",
        "index_name": "纳指科技",
        "fee_rate": "1.00%",
        "tracking_error": "--",
        "inception_date": "2023-08-31",
        "default_return_1y": 31.28,
        "default_nav": 2.8137,
        "default_nav_date": "2026-08-03",
        "default_asset_allocation": {"stock_pct": 93.46, "cash_pct": 6.54, "bond_pct": 0.0},
        "tag": "纳指科技",
    },
    {
        "code": "007721",
        "name": "天弘标普500发起(QDII-FOF)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "0.80%",
        "tracking_error": "0.28%",
        "inception_date": "2019-09-24",
        "default_return_1y": 14.51,
        "default_nav": 2.2380,
        "default_nav_date": "2026-08-03",
        "default_asset_allocation": {"stock_pct": 96.18, "cash_pct": 3.82, "bond_pct": 0.0},
    },
    {
        "code": "017028",
        "name": "国泰标普500ETF发起联接(QDII)A人民币",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "0.75%",
        "tracking_error": "0.27%",
        "inception_date": "2023-03-01",
        "default_return_1y": 14.94,
        "default_nav": 1.7096,
        "default_nav_date": "2026-08-03",
        "default_asset_allocation": {"stock_pct": 95.89, "cash_pct": 4.11, "bond_pct": 0.0},
    },
    {
        "code": "096001",
        "name": "大成标普500等权重指数(QDII)A",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "1.00%",
        "tracking_error": "0.35%",
        "inception_date": "2011-03-23",
        "default_return_1y": 12.50,
        "default_nav": 2.8280,
        "default_nav_date": "2026-08-03",
        "default_asset_allocation": {"stock_pct": 94.50, "cash_pct": 5.50, "bond_pct": 0.0},
        "tag": "等权重",
    },
    {
        "code": "159529",
        "name": "景顺长城标普消费精选ETF(QDII)",
        "index_code": "SPX",
        "index_name": "标普500",
        "fee_rate": "0.50%",
        "tracking_error": "0.20%",
        "inception_date": "2024-01-24",
        "default_return_1y": 14.20,
        "default_nav": 1.2869,
        "default_nav_date": "2026-08-04",
        "default_asset_allocation": {"stock_pct": 95.00, "cash_pct": 5.00, "bond_pct": 0.0},
        "tag": "消费精选",
    },

    # --- 主动型 QDII 精选 (参考 DCA HUB 推荐列表) ---
    {
        "code": "019454",
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
        "default_asset_allocation": {"stock_pct": 90.0, "stock_cn_pct": 51.3, "stock_other_pct": 41.0, "cash_pct": 7.7, "bond_pct": 0.0},
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
        "default_asset_allocation": {"stock_pct": 87.53, "stock_us_pct": 46.65, "stock_hk_pct": 12.81, "stock_cn_pct": 17.43, "stock_other_pct": 10.64, "cash_pct": 12.28, "bond_pct": 0.0},
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
        "default_asset_allocation": {"stock_pct": 88.42, "stock_us_pct": 88.42, "cash_pct": 11.72, "bond_pct": 0.0},
        "tag": "风味纳指",
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
        "default_asset_allocation": {"stock_pct": 91.74, "stock_us_pct": 42.76, "stock_hk_pct": 8.03, "stock_cn_pct": 28.54, "stock_other_pct": 12.41, "cash_pct": 8.90, "bond_pct": 0.0},
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
        "default_asset_allocation": {"stock_pct": 76.44, "stock_us_pct": 16.66, "stock_hk_pct": 23.17, "stock_cn_pct": 36.61, "cash_pct": 14.61, "bond_pct": 0.0},
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
        "default_asset_allocation": {"stock_pct": 85.30, "stock_us_pct": 71.95, "stock_hk_pct": 3.47, "stock_cn_pct": 1.14, "stock_other_pct": 8.74, "cash_pct": 11.39, "bond_pct": 0.0},
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
        "default_asset_allocation": {"stock_pct": 94.54, "stock_us_pct": 92.77, "stock_hk_pct": 1.77, "cash_pct": 6.22, "bond_pct": 0.0},
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
        "allocation_estimated": True,
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
        "default_asset_allocation": {"stock_pct": 88.27, "stock_us_pct": 74.62, "stock_cn_pct": 8.47, "stock_other_pct": 5.17, "cash_pct": 12.27, "bond_pct": 0.0},
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
        "default_asset_allocation": {"stock_pct": 85.21, "stock_us_pct": 32.63, "stock_hk_pct": 8.42, "stock_cn_pct": 42.56, "stock_other_pct": 1.59, "cash_pct": 10.34, "bond_pct": 0.0},
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
        "default_asset_allocation": {"stock_pct": 92.25, "stock_us_pct": 17.85, "stock_hk_pct": 50.31, "stock_cn_pct": 10.31, "stock_other_pct": 13.78, "cash_pct": 10.82, "bond_pct": 0.0},
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
        "allocation_estimated": True,
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
        "default_asset_allocation": {"stock_pct": 87.56, "stock_us_pct": 84.10, "stock_hk_pct": 5.04, "cash_pct": 8.42, "bond_pct": 0.0},
        "allocation_estimated": True,
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
        "default_nav": 2.456,
        "default_nav_date": "2026-07-23",
        "default_asset_allocation": {"stock_pct": 78.90, "stock_us_pct": 14.90, "stock_hk_pct": 18.44, "stock_other_pct": 45.56, "cash_pct": 12.82, "bond_pct": 0.0},
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
        "default_asset_allocation": {"stock_pct": 81.03, "stock_us_pct": 24.23, "stock_hk_pct": 8.59, "stock_cn_pct": 38.93, "stock_other_pct": 9.29, "cash_pct": 8.33, "bond_pct": 0.0},
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
        "allocation_estimated": True,
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
        "allocation_estimated": True,
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
        "default_asset_allocation": {"stock_pct": 74.55, "stock_us_pct": 43.6, "stock_hk_pct": 22.45, "stock_cn_pct": 8.5, "cash_pct": 25.45, "bond_pct": 0.0},
        "allocation_estimated": True,
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
        "default_asset_allocation": {"stock_pct": 82.92, "stock_us_pct": 65.90, "stock_hk_pct": 20.37, "cash_pct": 15.66, "bond_pct": 0.0},
    },
]


def fetch_sina_fund_navs(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """使用新浪财经 API 极速批量获取基金最新净值 (毫秒级响应，防封禁)"""
    res: Dict[str, Dict[str, Any]] = {}
    try:
        # 同时查询 fu_ (QDII类) 和 f_ (普通开放式类) 两种前缀，确保新发行或不同分类基金均有数据
        query_items = []
        for c in codes:
            query_items.append(f"fu_{c}")
            query_items.append(f"f_{c}")
        query = ",".join(query_items)
        url = f"http://hq.sinajs.cn/list={query}"
        headers = {"Referer": "http://finance.sina.com.cn"}
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            for line in r.text.strip().split("\n"):
                if "=" in line and '""' not in line:
                    parts = line.split("=")
                    var_name = parts[0].strip()
                    is_fu = "hq_str_fu_" in var_name
                    code = var_name.replace("var hq_str_fu_", "").replace("var hq_str_f_", "")
                    content = parts[1].strip('";').split(",")
                    
                    try:
                        if is_fu:
                            if len(content) >= 8 and content[2]:
                                nav_val = float(content[2])
                                date_str = content[7]
                            else:
                                continue
                        else:
                            if len(content) >= 5 and content[1]:
                                nav_val = float(content[1])
                                date_str = content[4]
                            else:
                                continue
                                
                        # 如果是新数据，或者日期更新，则进行覆盖/保存
                        if code not in res or date_str > res[code]["nav_date"]:
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



def _is_quarterly_report_window() -> bool:
    """判断当前是否处于公募基金季报集中披露窗口期（每季末后15天~40天左右）"""
    today = datetime.now()
    month, day = today.month, today.day
    # 季报披露集中期：1/15~2/5, 4/15~5/5, 7/15~8/5, 10/15~11/5
    windows = [(1, 15, 2, 5), (4, 15, 5, 5), (7, 15, 8, 5), (10, 15, 11, 5)]
    for sm, sd, em, ed in windows:
        if (month == sm and day >= sd) or (month == em and day <= ed):
            return True
    return False


def fetch_fund_asset_allocation(session: requests.Session, code: str) -> Optional[Dict[str, Any]]:
    """获取指定 QDII 场外联接/被动基金的最新真实资产/持仓配置（股票/权益 %、现金/货币 %）"""
    cache_key = f"{settings.CACHE_PREFIX}:qdii:asset_alloc_v2:{code}"
    try:
        cached_val = cache.get(cache_key)
        if cached_val is not None:
            # 智能判断：如果不处于季报发布窗口期，直接返回缓存
            if not _is_quarterly_report_window():
                return cached_val
            # 如果处于窗口期，检查已有的 report_date 是不是就是最新的目标季度报告
            report_date = cached_val.get("report_date", "")
            if report_date:
                today = datetime.now()
                # 季报截止日预测映射：4-5月最新为 3-31；7-8月为 6-30；10-11月为 9-30；1-2月为上年 12-31
                expected_quarters = {
                    1: f"{today.year-1}-12-31", 2: f"{today.year-1}-12-31",
                    4: f"{today.year}-03-31", 5: f"{today.year}-03-31",
                    7: f"{today.year}-06-30", 8: f"{today.year}-06-30",
                    10: f"{today.year}-09-30", 11: f"{today.year}-09-30"
                }
                expected_date = expected_quarters.get(today.month)
                if expected_date and report_date == expected_date:
                    return cached_val
    except Exception:
        pass
    try:
        time.sleep(0.2)  # 延时分散并发请求，防代理超时
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

        # 东方财富资产配置表列：报告期(0) | 股票占比(1) | 债券占比(2) | 现金占比(3) | 其他(4)
        # 使用各列真实数据，而非 100%-现金 推算，以保留未披露/其他资产的真实比例
        stock_val = parse_pct(selected_row[1]) if len(selected_row) > 1 else 0.0
        bond_val = parse_pct(selected_row[2]) if len(selected_row) > 2 else 0.0
        cash_val = parse_pct(selected_row[3]) if len(selected_row) > 3 else 0.0

        result = {
            "stock_pct": stock_val,
            "cash_pct": cash_val,
            "bond_pct": bond_val,
            "report_date": selected_row[0]
        }
        try:
            cache.set(cache_key, result, ttl=86400 * 50)  # 资产配置缓存 50 天
        except Exception:
            pass
        return result
    except Exception as e:
        print(f"⚠️ 资产配置获取跳过 [{code}]: {e}")
        return None


def fetch_fund_fee_rate(session: requests.Session, code: str) -> Optional[str]:
    """获取指定基金的最新综合运营费率（管理费率 + 托管费率 + 销售服务费率）"""
    cache_key = f"{settings.CACHE_PREFIX}:qdii:fee_rate:{code}"
    try:
        cached_val = cache.get(cache_key)
        if cached_val is not None:
            return cached_val
    except Exception:
        pass
    try:
        time.sleep(0.2)  # 延时分散并发请求，防代理超时
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
            result = f"{total:.2f}%"
            try:
                cache.set(cache_key, result, ttl=86400 * 90)  # 费率缓存 90 天
            except Exception:
                pass
            return result
        return None
    except Exception as e:
        print(f"⚠️ 费率获取跳过 [{code}]: {e}")
        return None


def _generate_active_fund_tag(item: Dict[str, Any], total_count: int, top10_concentration: float) -> Optional[str]:
    """根据持仓数量、持仓风格与资产配置动态计算主动基金风格标签"""
    if item.get("tag"):
        return item["tag"]
    name = item.get("name", "")
    code = item.get("code", "")
    alloc = item.get("default_asset_allocation", {})
    if "新能源" in name or "车" in name:
        return "新能源车"
    if "半导体" in name or "芯片" in name or code == "019454":
        return "中韩芯片"
    if "新兴市场" in name or code == "539002":
        return "全球芯片"
    if total_count >= 150:
        return "广泛分散"
    stock_pct = alloc.get("stock_pct", 0.0)
    if stock_pct > 0:
        stock_us_pct = alloc.get("stock_us_pct", 0.0)
        stock_hk_pct = alloc.get("stock_hk_pct", 0.0)
        stock_cn_pct = alloc.get("stock_cn_pct", 0.0)
        us_ratio = stock_us_pct / stock_pct
        hk_ratio = stock_hk_pct / stock_pct
        if us_ratio >= 0.8:
            if any(k in name for k in ["科技", "互联", "移动", "纳斯达克", "智能"]):
                return "美股科技"
            return "美股精选"
        if hk_ratio >= 0.6:
            if any(k in name for k in ["科技", "互联", "移动"]):
                return "港股科技"
            return "港股精选"
        if hk_ratio >= 0.4 and any(k in name for k in ["科技", "互联"]):
            return "港股互联网"
        if stock_us_pct > 0 and (stock_cn_pct > 0 or stock_hk_pct > 0):
            if any(k in name for k in ["科技", "互联", "移动"]):
                return "全球科技"
            return "全球配置"
        if us_ratio >= 0.2 and hk_ratio >= 0.2:
            if any(k in name for k in ["科技", "互联", "移动"]):
                return "全球科技"
            return "全球配置"
    if total_count > 0 and total_count <= 40:
        return "集中重仓"
    return "均衡配置"


@cached("qdii:passive_funds_v29", ttl=86400)
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

    # 2. 尝试 雪球 并发获取每个基金的真实近1年收益率 (复权净值计算，精确剔除分拆与折算误差)
    try:
        def fetch_xq_return(code):
            try:
                df = ak.fund_individual_achievement_xq(symbol=code)
                if df is not None and not df.empty:
                    row = df[(df["业绩类型"] == "阶段业绩") & (df["周期"] == "近1年")]
                    if not row.empty:
                        return code, float(row.iloc[0]["本产品区间收益"])
            except Exception as e:
                print(f"⚠️ 雪球获取收益率失败 [{code}]: {e}")
            return code, None

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_xq_return, target_codes)
            for c, r_val in results:
                if r_val is not None:
                    if c not in rank_map:
                        rank_map[c] = {}
                    rank_map[c]["return_1y"] = r_val
    except Exception as err:
        print(f"⚠️ 雪球并发获取收益率总入口报错: {err}")

    # 3. 并发获取所有 QDII 基金的真实资产配置仓位与动态费率
    alloc_map: Dict[str, Dict[str, Any]] = {}
    fee_map: Dict[str, str] = {}
    try:
        session = requests.Session()
        with ThreadPoolExecutor(max_workers=4) as executor:  # 降到 4 线程并发，保证代理接口稳定性
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

    # 4. 获取所有注册基金的场外日常申购限额状态 (开放申购/限大额/暂停申购)
    status_map: Dict[str, str] = {}
    try:
        df_daily = ak.fund_open_fund_daily_em()
        if df_daily is not None and not df_daily.empty:
            for _, row in df_daily.iterrows():
                code = row.get("基金代码")
                if code in target_codes:
                    status = row.get("申购状态")
                    if status:
                        status_map[code] = status
    except Exception as err:
        print(f"⚠️ 天天基金获取每日申购状态报错: {err}")

    # 5. 获取原生指数收益对标基准
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
        buy_status = status_map.get(code) or "开放申购"

        # 针对主动型基金动态计算其风格标签
        fund_tag = item.get("tag")
        if item.get("type") == "active":
            try:
                holdings_res = get_qdii_top_holdings(code)
                h_data = holdings_res.get("data", {})
                total_count = h_data.get("total_count", 0)
                top10_concentration = h_data.get("top10_concentration", 0.0)
            except Exception:
                total_count = 0
                top10_concentration = 0.0
            fund_tag = _generate_active_fund_tag(item, total_count, top10_concentration)

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
            "allocation_estimated": item.get("allocation_estimated", False),
            "tag": fund_tag,
            "buy_status": buy_status,
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


def _fetch_full_holdings_count(session: requests.Session, fetch_code: str, default_count: int) -> int:
    """尝试从历史半年报及年报中获取全量持仓只数（用于主动管理型基金在季报仅披露前十重仓时的总持仓数兜底）"""
    if default_count >= 30:
        return default_count
    
    current_year = datetime.now().year
    years_to_check = [current_year - 1, current_year - 2]
    months_to_check = [12, 6]
    
    for y in years_to_check:
        for m in months_to_check:
            url_full = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fetch_code}&topline=1000&year={y}&month={m}"
            res = fetch_url_via_proxy(url_full, session=session, timeout=4)
            if res and res.status_code == 200:
                match = re.search(r'content:\"(.*?)\"', res.text, re.DOTALL)
                if match:
                    soup = bs4.BeautifulSoup(match.group(1), "html.parser")
                    table = soup.find("table", class_="tzxq")
                    if table:
                        cnt = len(table.find_all("tr")) - 1
                        if cnt > default_count:
                            return cnt
    return default_count


@cached("qdii:top_holdings_v10", ttl=86400 * 7, stale_ttl=86400 * 30, sync_on_cold=True)
def get_qdii_top_holdings(code: str) -> Dict[str, Any]:
    """获取 QDII 基金最新披露的重仓持仓股票列表（升级支持最大100只完整持仓）"""
    # 联接基金到目标 ETF 的映射，当联接基金本身无持仓披露时，自动穿透到目标 ETF 获取底层持仓
    FEEDER_TO_TARGET_ETF = {
        "019454": "513310",  # 华泰柏瑞中韩半导体联接A -> 华泰柏瑞中韩半导体ETF
        "017894": "513290",  # 汇添富纳斯达克生物科技联接A -> 纳斯达克生物科技ETF
        "019547": "513100",  # 招商纳斯达克100联接A -> 国泰纳斯达克100ETF
        "019441": "513100",  # 万家纳斯达克100联接A -> 国泰纳斯达克100ETF
        "016452": "513100",  # 南方纳斯达克100联接A -> 国泰纳斯达克100ETF
        "019524": "513100",  # 华泰柏瑞纳斯达克100联接A -> 国泰纳斯达克100ETF
        "018966": "513100",  # 汇添富纳斯达克100联接A -> 国泰纳斯达克100ETF
        "015299": "513100",  # 华夏纳斯达克100联接A -> 国泰纳斯达克100ETF
        "050025": "513500",  # 博时标普500联接A -> 博时标普500ETF
        "007721": "513500",  # 天弘标普500 FOF -> 博时标普500ETF
        "017028": "513500",  # 国泰标普500联接A -> 博时标普500ETF
    }
    fetch_code = FEEDER_TO_TARGET_ETF.get(code, code)
    try:
        session = requests.Session()
        url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fetch_code}&topline=100"
        
        # 使用代理获取 (根据项目安全规范，严格禁止直连回退)
        res = fetch_url_via_proxy(url, session=session, timeout=6)
                
        if res is None:
            return {"status": "error", "error": True, "message": f"网络请求超时 (code: {code})", "holdings": []}
            
        if res.status_code == 404:
            # 404 表示该基金无相关持仓披露页面 (如某些联接基金或刚成立无数据)
            # 正常返回空持仓，让其进入缓存以避免持续报错请求
            return {
                "status": "ok",
                "code": code,
                "report_date": "暂无季报",
                "count": 0,
                "total_count": 0,
                "top10_concentration": 0.0,
                "is_penetrated": fetch_code != code,
                "target_code": fetch_code if fetch_code != code else None,
                "holdings": []
            }
            
        if res.status_code != 200:
            return {"status": "error", "error": True, "message": f"接口异常 HTTP {res.status_code} (code: {code})", "holdings": []}

        match = re.search(r'content:\"(.*?)\"', res.text, re.DOTALL)
        if not match:
            return {
                "status": "ok",
                "code": code,
                "report_date": "暂无季报",
                "count": 0,
                "total_count": 0,
                "top10_concentration": 0.0,
                "is_penetrated": fetch_code != code,
                "target_code": fetch_code if fetch_code != code else None,
                "holdings": []
            }

        html_content = match.group(1)
        soup = bs4.BeautifulSoup(html_content, "html.parser")
        date_font = soup.find("font", class_="px12")
        report_date = date_font.text.strip() if date_font else "最新季报"

        table = soup.find("table", class_="tzxq")
        if not table:
            return {
                "status": "ok",
                "code": code,
                "report_date": report_date,
                "count": 0,
                "total_count": 0,
                "top10_concentration": 0.0,
                "is_penetrated": fetch_code != code,
                "target_code": fetch_code if fetch_code != code else None,
                "holdings": []
            }

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

                # 判定持仓股类型
                stock_type = "其他"
                s_code_clean = stock_code.strip()
                s_name_clean = stock_name.strip()
                if "现金" in s_name_clean or "银行存款" in s_name_clean or "结算备付金" in s_name_clean:
                    stock_type = "现金"
                else:
                    # 优先利用 HTML 节点的跳转链接分析所属市场/交易板块以保证绝对准确
                    a_tag = tr.find("a")
                    href = a_tag.get("href", "") if a_tag else ""
                    match_href = re.search(r'/r/(\d+)\.', href)
                    if match_href:
                        market_id = match_href.group(1)
                        if market_id in ("0", "1", "2"):  # 深交所(0)、上交所(1)、北交所(2)
                            stock_type = "A股"
                        elif market_id in ("116", "117"):  # 港股通/港交所
                            stock_type = "港股"
                        elif market_id in ("105", "106", "107"):  # 纳斯达克/纽交所/美交所
                            stock_type = "美股"
                    else:
                        # 兜底匹配：在没有超链接跳转的情况下进行基础格式过滤
                        if re.match(r'^[a-zA-Z\.\-]+$', s_code_clean):
                            stock_type = "美股"
                        elif re.match(r'^\d{5}$', s_code_clean):
                            stock_type = "港股"
                        else:
                            # 韩国、日本、台湾等其他未被东财直接关联行情链接的跨境证券，统一归为“其他”
                            stock_type = "其他"

                holdings.append({
                    "rank": rank_str,
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "stock_type": stock_type,
                    "ratio_pct": ratio_pct_str,
                    "ratio_val": ratio_val,
                    "share_amount": share_amount,
                    "market_value": market_value
                })

        # 计算前十集中度与全量持仓只数
        top10_concentration = round(sum(h["ratio_val"] for h in holdings[:10]), 2)
        total_count = _fetch_full_holdings_count(session, fetch_code, len(holdings))

        return {
            "status": "ok",
            "code": code,
            "report_date": report_date,
            "count": len(holdings),
            "total_count": total_count,
            "top10_concentration": top10_concentration,
            "is_penetrated": fetch_code != code,
            "target_code": fetch_code if fetch_code != code else None,
            "holdings": holdings
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "holdings": []}

