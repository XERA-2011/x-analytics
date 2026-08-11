"""
指数估值模块
获取沪深300、恒生科技、纳斯达克100、标普500等指数的历史 PE 和收盘价，并计算当前估值百分位及评估等级。
"""

from typing import Dict, Any, List
import requests
import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime
import pytz

from ..core.cache import cached
from ..core.utils import safe_float, akshare_call_with_retry
from ..core.logger import logger

INDEX_MAPPING = {
    "SH000300": {
        "name": "沪深300",
        "dj_code": "SH000300",
        "price_symbol": "sh000300"
    },
    "HSI": {
        "name": "恒生指数",
        "dj_code": "HKHSI",
        "price_symbol": "HSI"
    },
    "NDX": {
        "name": "纳斯达克100",
        "dj_code": "NDX",
        "price_symbol": ".NDX"
    },
    "SP500": {
        "name": "标普500",
        "dj_code": "SP500",
        "price_symbol": ".INX"
    },
    "SH000015": {
        "name": "中证红利",
        "dj_code": "SH000015",
        "price_symbol": "sh000015"
    }
}

@cached("index_valuation:v4", ttl=14400)
def get_index_valuation(index_code: str) -> Dict[str, Any]:
    """
    获取指定指数的估值及价格历史数据
    
    Args:
        index_code: 指数代码 (SH000300, HSI, NDX, SP500, SH000015)
        
    Returns:
        包含当前PE、百分位、评级以及历史PE、价格序列的字典
    """
    code_upper = index_code.upper()
    if code_upper not in INDEX_MAPPING:
        raise ValueError(f"Unsupported index code: {index_code}. Supported codes: {list(INDEX_MAPPING.keys())}")
        
    cfg = INDEX_MAPPING[code_upper]
    name = cfg["name"]
    dj_code = cfg["dj_code"]
    price_symbol = cfg["price_symbol"]
    
    # 1. 抓取 Danjuan 历史 PE TTM 数据
    pe_url = f"https://danjuanfunds.com/djapi/index_eva/pe_history/{dj_code}?day=all"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        logger.info(f"Fetching Danjuan PE history for {name} ({dj_code})")
        r = requests.get(pe_url, headers=headers, proxies={'http': None, 'https': None}, timeout=15)
        r.raise_for_status()
        res_json = r.json()
    except Exception as e:
        logger.error(f"Failed to fetch Danjuan PE data for {dj_code}: {e}")
        raise RuntimeError(f"Failed to fetch Danjuan PE data for {dj_code}: {e}")
        
    growths = res_json.get("data", {}).get("index_eva_pe_growths", [])
    if not growths:
        logger.error(f"No PE data returned from Danjuan for {dj_code}")
        raise ValueError(f"No PE data returned from Danjuan for {dj_code}")
        
    beijing_tz = pytz.timezone("Asia/Shanghai")
    pe_series: List[List[Any]] = []
    for item in growths:
        pe_val = item.get("pe")
        ts = item.get("ts")
        if pe_val is not None and ts is not None:
            ts_seconds = float(ts) / 1000.0 if float(ts) > 1e11 else float(ts)
            date_str = datetime.fromtimestamp(ts_seconds, beijing_tz).strftime('%Y-%m-%d')
            pe_series.append([date_str, safe_float(pe_val)])
            
    pe_series.sort(key=lambda x: x[0])
    
    # 2. 抓取历史收盘价格序列数据
    price_series: List[List[Any]] = []
    
    try:
        # 沪深A股指数/ETF 从新浪 K 线 API 获取
        is_china_a = price_symbol.startswith("sh") or price_symbol.startswith("sz")
        if is_china_a:
            logger.info(f"Fetching Sina KLine price data for {name} ({price_symbol})")
            sina_url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={price_symbol}&scale=240&ma=no&datalen=3000"
            r_price = requests.get(sina_url, headers=headers, proxies={'http': None, 'https': None}, timeout=15)
            r_price.raise_for_status()
            price_data = r_price.json()
            
            for item in price_data:
                day_val = item.get("day")
                close_val = item.get("close")
                if day_val is not None and close_val is not None:
                    # Clean date format
                    date_str = day_val.split()[0]
                    price_series.append([date_str, safe_float(close_val)])
        else:
            # 其他指数使用 akshare
            logger.info(f"Fetching AkShare price data for {name} ({price_symbol})")
            if code_upper == "HSI":
                df = akshare_call_with_retry(ak.stock_hk_index_daily_sina, symbol=price_symbol)
            else: # NDX, SP500
                df = akshare_call_with_retry(ak.index_us_stock_sina, symbol=price_symbol)
                
            if df is not None and not df.empty:
                if "date" not in df.columns and df.index.name == "date":
                    df = df.reset_index()
                elif "date" not in df.columns and "trade_date" in df.columns:
                    df = df.rename(columns={"trade_date": "date"})
                
                if "date" in df.columns:
                    df = df.sort_values("date")
                
                for _, row in df.iterrows():
                    d_val = row.get("date")
                    c_val = row.get("close")
                    if d_val is not None and c_val is not None:
                        if hasattr(d_val, "strftime"):
                            date_str = d_val.strftime("%Y-%m-%d")
                        else:
                            date_str = str(d_val)[:10]
                        price_series.append([date_str, safe_float(c_val)])
    except Exception as e:
        logger.error(f"Failed to fetch price data for {code_upper}: {e}")
        raise RuntimeError(f"Failed to fetch price data for {code_upper}: {e}")
        
    price_series.sort(key=lambda x: x[0])
    
    # 限制收盘价点位仅随 PE 更新（不超过 PE 最新数据截止日期）
    if pe_series:
        latest_pe_date = pe_series[-1][0]
        price_series = [item for item in price_series if item[0] <= latest_pe_date]
    
    # 3. 计算估值指标
    pe_list = [val for _, val in pe_series if val is not None]
    if not pe_list:
        raise ValueError(f"No valid PE values found for index {name}")
        
    latest_pe = pe_series[-1][1]
    latest_date_str = pe_series[-1][0]
    
    # 当前百分位：低于或等于当前 PE 的历史天数比例
    current_percentile = sum(1 for pe in pe_list if pe <= latest_pe) / len(pe_list)
    current_percentile = round(current_percentile, 4)
    
    # 计算 20%, 50%, 80% 百分位线
    p20, p50, p80 = np.percentile(pe_list, [20, 50, 80])
    p20_val = round(float(p20), 2)
    p50_val = round(float(p50), 2)
    p80_val = round(float(p80), 2)
    
    # 评级
    if current_percentile < 0.2:
        eval_level = "low"
    elif current_percentile < 0.8:
        eval_level = "medium"
    else:
        eval_level = "high"
        
    return {
        "name": name,
        "index_code": code_upper,
        "current_pe": latest_pe,
        "percentile": current_percentile,
        "eval_level": eval_level,
        "percentile_lines": {
            "p20": p20_val,
            "p50": p50_val,
            "p80": p80_val
        },
        "pe_series": pe_series,
        "price_series": price_series,
        "data_date": latest_date_str
    }
