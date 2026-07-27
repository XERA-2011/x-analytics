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


@cached("qdii:passive_funds_v10", ttl=86400)
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
        asset_alloc = alloc_map.get(code) or item.get("default_asset_allocation")
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
