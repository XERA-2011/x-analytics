"""
ETF 热力图模块
获取 A 股市场精选 ETF 实时行情，按四大分类分组，生成热力图数据
"""

from typing import Dict, Any, List, Optional
import akshare as ak

from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger


# ============================================================================
# ETF 白名单 — 按分类组织
# 格式: { "分类名": { "代码": "简称", ... }, ... }
# ============================================================================

ETF_WATCHLIST: Dict[str, Dict[str, str]] = {
    "宽基指数": {
        "510300": "沪深300 ETF",
        "510050": "上证50 ETF",
        "159338": "中证A500 ETF",
        "510500": "中证500 ETF",
        "512100": "中证1000 ETF",
        "563300": "中证2000 ETF",
        "159915": "创业板 ETF",
        "588000": "科创50 ETF",
    },
    "行业主题": {
        "512880": "证券 ETF",
        "512800": "银行 ETF",
        "512480": "半导体 ETF",
        "515070": "人工智能 ETF",
        "159941": "纳指 ETF",
        "512760": "芯片 ETF",
        "515880": "通信 ETF",
        "512690": "酒 ETF",
        "512010": "医药 ETF",
        "159992": "创新药 ETF",
        "515030": "新能源车 ETF",
        "515790": "光伏 ETF",
        "512400": "有色金属 ETF",
        "515220": "煤炭 ETF",
        "512660": "军工 ETF",
        "512890": "红利低波 ETF",
    },
    "跨境": {
        "513180": "恒生科技 ETF",
        "513330": "恒生互联网 ETF",
        "159691": "港股红利 ETF",
        "513100": "纳斯达克 ETF",
        "513500": "标普500 ETF",
        "513880": "日经 ETF",
    },
    "商品债券": {
        "518880": "黄金 ETF",
        "159985": "豆粕 ETF",
        "511090": "30年国债 ETF",
        "511260": "十年国债 ETF",
    },
}

# 所有白名单代码的扁平集合，用于快速过滤
_ALL_CODES = set()
for _cat_codes in ETF_WATCHLIST.values():
    _ALL_CODES.update(_cat_codes.keys())

# 代码 → 分类 反查表
_CODE_TO_CATEGORY: Dict[str, str] = {}
for _cat_name, _cat_codes in ETF_WATCHLIST.items():
    for _code in _cat_codes:
        _CODE_TO_CATEGORY[_code] = _cat_name

# 排行榜返回的最大条目数
TOP_N = 10


class ETFHeatmap:
    """ETF 热力图数据"""

    @staticmethod
    @cached(
        "etf:heatmap",
        ttl=settings.CACHE_TTL["market"],
        stale_ttl=settings.CACHE_TTL["market"] * settings.STALE_TTL_RATIO
    )
    def get_heatmap_data() -> Dict[str, Any]:
        """
        获取 ETF 热力图数据

        Returns:
            包含分类 treemap 数据和涨跌排行榜
        """
        import requests
        import re
        
        try:
            # 1. 构建 Sina API 请求
            sina_codes = []
            for code in _ALL_CODES:
                prefix = "sh" if code.startswith("5") else "sz"
                sina_codes.append(f"{prefix}{code}")
                
            url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
            headers = {"Referer": "http://finance.sina.com.cn/"}
            
            # 2. 获取数据
            res = requests.get(url, headers=headers, timeout=5)
            lines = res.text.strip().split('\n')
            
            if not lines or 'var hq_str_' not in lines[0]:
                raise ValueError("获取新浪行情数据失败")
                
            # 3. 解析数据
            etf_data = {}
            for line in lines:
                if not line: continue
                # 格式: var hq_str_sh510300="沪深300ETF华泰柏瑞,4.909,4.926,4.833,...";
                match = re.match(r'var hq_str_(?:sh|sz)(\d+)="([^"]+)";', line)
                if match:
                    code = match.group(1)
                    fields = match.group(2).split(",")
                    if len(fields) > 10:
                        yest_close = safe_float(fields[2])
                        price = safe_float(fields[3])
                        amount = safe_float(fields[9])
                        
                        change_pct = None
                        if yest_close and price:
                            change_pct = ((price - yest_close) / yest_close) * 100
                            
                        etf_data[code] = {
                            "price": price,
                            "change_pct": change_pct,
                            "amount": amount,
                            "turnover": None  # 新浪接口无直接换手率
                        }

            if not etf_data:
                raise ValueError("未能解析出任何有效的 ETF 行情")

            # 4. 构建 treemap 数据 (按分类分组)
            categories = []
            all_etfs: List[Dict[str, Any]] = []

            for cat_name, cat_codes in ETF_WATCHLIST.items():
                children = []
                for code, display_name in cat_codes.items():
                    if code not in etf_data:
                        continue
                        
                    data_row = etf_data[code]
                    amount = data_row["amount"]

                    etf_item = {
                        "name": display_name,
                        "code": code,
                        "value": amount if amount else 0,  # treemap 面积 = 成交额
                        "change_pct": data_row["change_pct"],
                        "price": data_row["price"],
                        "amount": amount,
                        "turnover": data_row["turnover"],
                    }
                    children.append(etf_item)
                    all_etfs.append(etf_item)

                if children:
                    # 分类总成交额作为该分类的 value
                    cat_total = sum(c["value"] for c in children)
                    categories.append({
                        "name": cat_name,
                        "value": cat_total,
                        "children": children,
                    })

            # 5. 生成涨跌排行
            sorted_by_change = sorted(
                [e for e in all_etfs if e["change_pct"] is not None],
                key=lambda x: x["change_pct"],
                reverse=True
            )

            top_gainers = sorted_by_change[:TOP_N]
            top_losers = sorted_by_change[-TOP_N:][::-1]  # 跌幅最大的在前

            matched_count = len(all_etfs)
            total_count = len(_ALL_CODES)

            return {
                "categories": categories,
                "top_gainers": top_gainers,
                "top_losers": top_losers,
                "matched": matched_count,
                "total": total_count,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"获取 ETF 热力图数据失败: {e}")
            return {
                "error": str(e),
                "categories": [],
                "top_gainers": [],
                "top_losers": [],
                "status": "error",
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }
