import requests
import random
from typing import List, Dict, Optional
from .utils import safe_float
from .logger import logger

def get_us_spot_direct(symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """
    获取美股/指数的实时极速行情，主要用于盘中替代 Akshare 的滞后日线。
    参数 symbols 为代码列表，如 [".IXIC", ".INX", ".DJI", "QQQ", "XLK"]
    """
    mapping = {
        ".IXIC": "100.NDX",  # 纳斯达克100
        ".INX": "100.SPX",   # 标普500
        ".DJI": "100.DJIA",  # 道琼斯
        ".VIX": "100.VIX",
    }
    
    secids = []
    reverse_map = {}
    for sym in symbols:
        if sym in mapping:
            secid = mapping[sym]
            secids.append(secid)
            reverse_map[secid.split(".")[1]] = sym
        else:
            for prefix in ["105", "106", "107"]:
                secids.append(f"{prefix}.{sym}")
            reverse_map[sym] = sym
            
    subdomains = ["push2", "17.push2", "82.push2"]
    random.shuffle(subdomains)

    params = {
        "secids": ",".join(secids),
        "fields": "f2,f3,f12",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }

    result = {}
    for sub in subdomains:
        url = f"http://{sub}.eastmoney.com/api/qt/ulist.np/get"
        try:
            r = requests.get(url, params=params, headers=headers, timeout=5)
            data = r.json()
            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    code = str(item.get("f12", ""))
                    # 东方财富美股 f2 是放大 100 倍, f3 是放大 100 倍
                    raw_price = safe_float(item.get("f2"))
                    raw_change = safe_float(item.get("f3"))
                    
                    if raw_price is not None and raw_change is not None:
                        price = raw_price / 100.0
                        change_pct = raw_change / 100.0
                        
                        sym = reverse_map.get(code, code)
                        result[sym] = {
                            "price": price,
                            "change_pct": change_pct
                        }
                return result
        except Exception:
            continue
            
    return result
