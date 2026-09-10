"""
ETF 热力图模块
获取 A 股市场精选 ETF 实时行情，生成结构化热力图数据
"""

from typing import Dict, Any, List
import pandas as pd
import akshare as ak

from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger

# 排行榜返回的最大条目数
TOP_N = 10

# 静态结构化白名单配置 (精选 56 只各赛道最具代表性与流动性的核心标的)
STATIC_CATEGORIES: Dict[str, Dict[str, str]] = {
    "核心宽基": {
        "510300": "沪深300",
        "510050": "上证50",
        "563360": "中证A500",
        "159593": "中证A50",
        "510500": "中证500",
        "512100": "中证1000",
        "159531": "中证2000",
        "159915": "创业板指",
        "159949": "创业板50",
        "588000": "科创50",
        "588030": "科创100",
    },
    "芯片半导体": {
        "588200": "科创芯片",
        "159516": "半导体设备",
        "588170": "科创半导体",
        "512480": "半导体",
        "513310": "中韩半导体",
    },
    "TMT数字科技": {
        "159819": "人工智能",
        "515880": "通信ETF",
        "515230": "软件ETF",
        "562500": "机器人",
        "512980": "传媒ETF",
        "516010": "游戏ETF",
    },
    "风格红利": {
        "510880": "红利ETF",
        "512890": "红利低波",
        "510090": "央企红利",
        "515100": "红利低波100",
    },
    "大金融": {
        "512880": "证券ETF",
        "512000": "券商ETF",
        "512800": "银行ETF",
        "513090": "香港证券",
    },
    "消费与医药": {
        "512690": "酒ETF",
        "515170": "食品饮料",
        "159996": "家电ETF",
        "159992": "创新药",
        "513120": "港股创新药",
        "512170": "医疗ETF",
    },
    "高端制造与新能源": {
        "516180": "光伏ETF",
        "515030": "新能源车",
        "159755": "电池ETF",
        "159611": "电力ETF",
        "512710": "军工龙头",
        "159227": "航空航天",
    },
    "周期与大宗商品": {
        "515220": "煤炭ETF",
        "512400": "有色金属",
        "159870": "化工ETF",
        "518880": "黄金ETF",
        "159985": "豆粕ETF",
        "159981": "能源化工",
    },
    "跨境互联与海外": {
        "513050": "中概互联",
        "513180": "恒生科技",
        "159792": "港股通互联",
        "159509": "纳指科技",
        "513100": "纳指100",
        "513500": "标普500",
        "513880": "日经225",
        "159329": "沙特ETF",
    },
}

# 扁平化映射，方便快速查找
ETF_CODE_TO_NAME: Dict[str, str] = {}
ETF_CODE_TO_CATEGORY: Dict[str, str] = {}
for category, etf_map in STATIC_CATEGORIES.items():
    for code, name in etf_map.items():
        ETF_CODE_TO_NAME[code] = name
        ETF_CODE_TO_CATEGORY[code] = category


class ETFHeatmap:
    """ETF 热力图数据"""

    @staticmethod
    @cached(
        "etf:heatmap:v5",  # 升级缓存键版本至 v5
        ttl=settings.CACHE_TTL["etf_heatmap"] if hasattr(settings, "CACHE_TTL") and "etf_heatmap" in settings.CACHE_TTL else 7200,
        stale_ttl=(settings.CACHE_TTL["etf_heatmap"] if hasattr(settings, "CACHE_TTL") and "etf_heatmap" in settings.CACHE_TTL else 7200) * settings.STALE_TTL_RATIO,
        sync_on_cold=True
    )
    def get_heatmap_data() -> Dict[str, Any]:
        """
        获取 ETF 热力图数据与全市场流动性排行榜

        Returns:
            包含分类 treemap 数据和全市场流动性涨跌排行榜
        """
        try:
            # 1. 获取全市场 ETF 数据
            df = akshare_call_with_retry(ak.fund_etf_spot_em)
            if df is None or df.empty:
                raise ValueError("获取全量 ETF 行情数据失败")
            
            # 2. 清洗数值列
            if "流通市值" in df.columns:
                df["流通市值"] = pd.to_numeric(df["流通市值"], errors="coerce").fillna(0.0)
            if "成交额" in df.columns:
                df["成交额"] = pd.to_numeric(df["成交额"], errors="coerce").fillna(0.0)
            if "最新价" in df.columns:
                df["最新价"] = pd.to_numeric(df["最新价"], errors="coerce")
            if "涨跌幅" in df.columns:
                df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")
            if "换手率" in df.columns:
                df["换手率"] = pd.to_numeric(df["换手率"], errors="coerce")

            # 3. 过滤并提取白名单 ETF (构建热力图)
            matched_etfs: List[Dict[str, Any]] = []
            
            for _, row in df.iterrows():
                code = str(row.get("代码", "")).strip().zfill(6)
                if code in ETF_CODE_TO_NAME:
                    amount = safe_float(row.get("成交额")) or 0.0
                    price = safe_float(row.get("最新价"))
                    change_pct = safe_float(row.get("涨跌幅"))
                    turnover = safe_float(row.get("换手率"))
                    
                    etf_item = {
                        "name": ETF_CODE_TO_NAME[code],  # 使用自定义精简名字
                        "code": code,
                        "value": amount if amount else 0.0,  # 面积为单只 ETF 的成交额
                        "change_pct": change_pct,
                        "price": price,
                        "amount": amount,
                        "turnover": turnover,
                        "category": ETF_CODE_TO_CATEGORY[code]
                    }
                    matched_etfs.append(etf_item)
            
            # 4. 构建 treemap 分类数据
            # 保持原始定义的分类顺序
            category_map: Dict[str, List[Dict[str, Any]]] = {
                cat: [] for cat in STATIC_CATEGORIES.keys()
            }
            
            for etf_dict in matched_etfs:
                cat_name = etf_dict["category"]
                
                # 清理分类临时字段
                clean_dict = etf_dict.copy()
                clean_dict.pop("category", None)
                
                category_map[cat_name].append(clean_dict)
                
            categories = []
            for cat_name, children in category_map.items():
                cat_total = sum(c["value"] for c in children) if children else 0.0
                categories.append({
                    "name": cat_name,
                    "value": cat_total,
                    "children": children
                })
                    
            # 5. 生成全市场流动性涨跌排行 (解耦白名单限制，真实反映市场热点)
            # 排除货币型与现金管理类 ETF
            money_pattern = "添益|日利|货币|理财|现金|金钱包|保证金"
            df_tradable = df[~df["名称"].astype(str).str.contains(money_pattern, na=False)].copy()

            # 成交额流动性门槛 (默认 >= 2000万元，早盘或极端低成交自动降至 500万元)
            min_amount = 20_000_000.0
            valid_etfs = df_tradable[
                (df_tradable["成交额"] >= min_amount) & 
                (df_tradable["涨跌幅"].notna())
            ]

            if len(valid_etfs) < 20:
                valid_etfs = df_tradable[
                    (df_tradable["成交额"] >= 5_000_000.0) & 
                    (df_tradable["涨跌幅"].notna())
                ]

            gainers_df = valid_etfs.sort_values(by="涨跌幅", ascending=False).head(TOP_N)
            losers_df = valid_etfs.sort_values(by="涨跌幅", ascending=True).head(TOP_N)

            def build_rank_item(r: pd.Series) -> Dict[str, Any]:
                c = str(r.get("代码", "")).strip().zfill(6)
                n = ETF_CODE_TO_NAME.get(c, str(r.get("名称", "")).strip())
                amt = safe_float(r.get("成交额")) or 0.0
                return {
                    "name": n,
                    "code": c,
                    "value": amt,
                    "change_pct": safe_float(r.get("涨跌幅")),
                    "price": safe_float(r.get("最新价")),
                    "amount": amt,
                    "turnover": safe_float(r.get("换手率")),
                }

            top_gainers = [build_rank_item(row) for _, row in gainers_df.iterrows()]
            top_losers = [build_rank_item(row) for _, row in losers_df.iterrows()]

            matched_count = len(matched_etfs)
            total_count = len(df)

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
