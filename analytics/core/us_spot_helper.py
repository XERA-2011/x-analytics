import requests
from typing import List, Dict
from .utils import safe_float
from .logger import logger

def get_us_spot_direct(symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """
    获取美股/指数的实时极速行情，主要用于盘中替代 Akshare 的滞后日线。
    采用腾讯接口，避免东方财富对云服务器的 IP 封锁。
    参数 symbols 为代码列表，如 [".IXIC", ".INX", ".DJI", "QQQ", "XLK"]
    """
    if not symbols:
        return {}

    tencent_symbols = []
    reverse_map = {}
    
    for sym in symbols:
        tsym = f"us{sym}"
        tencent_symbols.append(tsym)
        reverse_map[tsym.lower()] = sym
        reverse_map[tsym] = sym

    # 腾讯支持批量获取，直接拼接
    url = "http://qt.gtimg.cn/q=" + ",".join(tencent_symbols)
    
    result = {}
    try:
        r = requests.get(url, timeout=5)
        for line in r.text.split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue
                
            key_part, data_part = line.split("=", 1)
            tsym = key_part.replace("v_", "")
            
            data_str = data_part.strip('"')
            parts = data_str.split("~")
            
            if len(parts) >= 33 and parts[0] == "200":
                price = safe_float(parts[3])
                change_pct = safe_float(parts[32])
                
                if price is not None and change_pct is not None:
                    # 腾讯返回的键名可能大小写不同
                    sym = reverse_map.get(tsym, tsym)
                    result[sym] = {
                        "price": price,
                        "change_pct": change_pct
                    }
    except Exception as e:
        logger.error(f"Tencent spot fetch error: {e}")
        
    return result
