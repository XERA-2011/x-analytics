"""
中国市场领涨领跌股票
获取实时涨跌幅排行榜
"""

from typing import Dict, Any, List, Optional
import threading
import time
import json
from pathlib import Path
import pandas as pd
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.data_provider import data_provider
from ...core.logger import logger


class CNMarketLeaders:
    """中国市场领涨领跌股票"""

    MIN_PRIMARY_SECTOR_COUNT = 20
    SECTOR_MEMBERS_FILE = Path(settings.BASE_DIR) / "analytics" / "data" / "cn_primary_sector_members.json"
    SECTOR_MEMBERS_CACHE_TTL = 6 * 3600
    _sector_members_cache: Dict[str, List[Dict[str, str]]] = {}
    _sector_members_cache_ts: float = 0.0
    _sector_members_source: str = "uninitialized"
    _sector_members_lock = threading.Lock()

    # 申万一级行业白名单。
    # 东方财富行业接口会混入一级/二级/三级行业，热力图只保留一级行业。
    PRIMARY_SECTOR_NAMES = {
        "农林牧渔",
        "基础化工",
        "钢铁",
        "有色金属",
        "电子",
        "家用电器",
        "食品饮料",
        "纺织服饰",
        "轻工制造",
        "医药生物",
        "公用事业",
        "交通运输",
        "房地产",
        "商贸零售",
        "社会服务",
        "综合",
        "建筑材料",
        "建筑装饰",
        "电力设备",
        "国防军工",
        "计算机",
        "通信",
        "银行",
        "非银金融",
        "传媒",
        "机械设备",
        "汽车",
        "美容护理",
        "环保",
        "石油石化",
        "煤炭",
    }

    @staticmethod
    def _filter_primary_sectors(df):
        """仅保留一级行业。"""
        if "板块名称" not in df.columns:
            return df

        filtered_df = df[df["板块名称"].astype(str).isin(CNMarketLeaders.PRIMARY_SECTOR_NAMES)]

        # 上游名称口径变化时，命中过少说明白名单已失效，退回原始数据。
        if len(filtered_df) >= CNMarketLeaders.MIN_PRIMARY_SECTOR_COUNT:
            return filtered_df

        logger.warning(
            "一级行业白名单命中过少，回退原始行业列表: matched=%s total=%s",
            len(filtered_df),
            len(df),
        )
        return df

    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """按候选名称查找列。"""
        for col in candidates:
            if col in df.columns:
                return col
        return None

    @staticmethod
    def _get_primary_sector_names() -> List[str]:
        """获取一级行业名称（长期方案使用本地白名单）。"""
        return sorted(CNMarketLeaders.PRIMARY_SECTOR_NAMES)

    @staticmethod
    def _load_sector_members_from_file() -> Dict[str, List[Dict[str, str]]]:
        """从本地文件读取行业成分股映射。"""
        path = CNMarketLeaders.SECTOR_MEMBERS_FILE
        if not path.exists():
            return {}

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            sectors = payload.get("sectors", {})
            if isinstance(sectors, dict):
                return {
                    str(sector): [
                        {"code": str(item.get("code", "")).strip(), "name": str(item.get("name", "")).strip()}
                        for item in members
                        if str(item.get("code", "")).strip()
                    ]
                    for sector, members in sectors.items()
                    if isinstance(members, list)
                }
        except Exception as e:
            logger.warning("读取本地行业映射失败 [%s]: %s", path, e)
        return {}

    @staticmethod
    def _save_sector_members_to_file(sector_members: Dict[str, List[Dict[str, str]]]) -> None:
        """保存行业成分股映射到本地文件。"""
        path = CNMarketLeaders.SECTOR_MEMBERS_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            "sector_count": len(sector_members),
            "sectors": sector_members,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _fetch_sector_members_from_upstream() -> Dict[str, List[Dict[str, str]]]:
        """一次性从上游刷新行业成分股映射。"""
        sector_members: Dict[str, List[Dict[str, str]]] = {}
        for sector_name in CNMarketLeaders._get_primary_sector_names():
            try:
                cons_df = data_provider.get_sector_constituents(sector_name)
                if cons_df.empty:
                    continue

                code_col = CNMarketLeaders._find_column(cons_df, ["代码", "证券代码"])
                name_col = CNMarketLeaders._find_column(cons_df, ["名称", "证券简称"])
                if not code_col:
                    continue

                members: List[Dict[str, str]] = []
                for _, row in cons_df.iterrows():
                    code = str(row.get(code_col, "")).strip()
                    if not code:
                        continue
                    members.append({
                        "code": code,
                        "name": str(row.get(name_col, "")).strip() if name_col else "",
                    })

                if members:
                    sector_members[sector_name] = members
            except Exception as e:
                logger.warning("刷新行业成分股失败 [%s]: %s", sector_name, e)

        if len(sector_members) >= CNMarketLeaders.MIN_PRIMARY_SECTOR_COUNT:
            CNMarketLeaders._save_sector_members_to_file(sector_members)

        return sector_members

    @staticmethod
    def _get_sector_members_map(force_refresh: bool = False) -> Dict[str, List[Dict[str, str]]]:
        """获取行业 -> 成分股映射。

        运行时只读取本地文件 / 内存缓存。
        只有显式 force_refresh 时，才会访问上游刷新映射，避免热力图主链路依赖在线行业接口。
        """
        now = time.time()
        with CNMarketLeaders._sector_members_lock:
            if (
                not force_refresh
                and CNMarketLeaders._sector_members_cache
                and now - CNMarketLeaders._sector_members_cache_ts < CNMarketLeaders.SECTOR_MEMBERS_CACHE_TTL
            ):
                CNMarketLeaders._sector_members_source = "memory_cache"
                return CNMarketLeaders._sector_members_cache

            sector_members = {} if force_refresh else CNMarketLeaders._load_sector_members_from_file()
            if sector_members and not force_refresh:
                CNMarketLeaders._sector_members_source = "local_file"
            elif force_refresh:
                sector_members = CNMarketLeaders._fetch_sector_members_from_upstream()
                if sector_members:
                    CNMarketLeaders._sector_members_source = "upstream_refresh"

            if sector_members:
                CNMarketLeaders._sector_members_cache = sector_members
                CNMarketLeaders._sector_members_cache_ts = now
            else:
                CNMarketLeaders._sector_members_source = "missing_local_file" if not force_refresh else "unavailable"

            return CNMarketLeaders._sector_members_cache

    @staticmethod
    def _build_sector_heatmap_from_stocks() -> Optional[Dict[str, Any]]:
        """基于全市场个股实时数据聚合行业热力图。"""
        sector_members = CNMarketLeaders._get_sector_members_map()
        if not sector_members:
            return None

        try:
            spot_df = data_provider.get_stock_zh_a_spot()
            if spot_df.empty:
                return None
        except Exception as e:
            logger.warning("获取全市场个股实时行情失败，聚合热力图不可用，将尝试回退板块接口: %s", e)
            return None

        code_col = CNMarketLeaders._find_column(spot_df, ["代码", "证券代码"])
        name_col = CNMarketLeaders._find_column(spot_df, ["名称", "证券简称"])
        change_col = CNMarketLeaders._find_column(spot_df, ["涨跌幅"])
        turnover_col = CNMarketLeaders._find_column(spot_df, ["换手率"])
        market_cap_col = CNMarketLeaders._find_column(spot_df, ["总市值", "流通市值"])
        price_col = CNMarketLeaders._find_column(spot_df, ["最新价", "现价", "收盘价"])

        if not code_col or not change_col:
            return None

        df = spot_df.copy()
        df[code_col] = df[code_col].astype(str).str.strip()
        for col in [change_col, turnover_col, market_cap_col, price_col]:
            if col:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        sector_rows = []
        for sector_name, members in sector_members.items():
            member_df = pd.DataFrame(members)
            merged = member_df.merge(df, left_on="code", right_on=code_col, how="inner")
            if merged.empty:
                continue

            valid_change = merged[change_col].dropna()
            if valid_change.empty:
                continue

            stock_count = int(len(merged))
            total_market_cap = 0.0
            weighted_change = None

            if market_cap_col and merged[market_cap_col].notna().any():
                cap_series = merged[market_cap_col].fillna(0.0)
                total_market_cap = float(cap_series.sum())
                valid_weights = cap_series > 0
                if valid_weights.any():
                    weighted_change = float(
                        (merged.loc[valid_weights, change_col] * cap_series.loc[valid_weights]).sum()
                        / cap_series.loc[valid_weights].sum()
                    )

            if weighted_change is None:
                weighted_change = float(valid_change.mean())

            turnover = 0.0
            if turnover_col and merged[turnover_col].notna().any():
                turnover = float(merged[turnover_col].fillna(0.0).mean())

            child_stocks = []
            for _, stock in merged.iterrows():
                stock_change = safe_float(stock.get(change_col), 0.0)
                stock_cap = safe_float(stock.get(market_cap_col), 0.0) if market_cap_col else 0.0
                stock_turnover = safe_float(stock.get(turnover_col), 0.0) if turnover_col else 0.0
                stock_price = safe_float(stock.get(price_col), 0.0) if price_col else 0.0
                child_stocks.append({
                    "name": str(stock.get(name_col, stock.get("name", ""))) if name_col else str(stock.get("name", "")),
                    "code": str(stock.get(code_col, "")),
                    "value": stock_cap if stock_cap > 0 else 1.0,
                    "change_pct": round(stock_change, 2),
                    "turnover": round(stock_turnover, 2),
                    "price": round(stock_price, 2),
                })

            child_stocks.sort(key=lambda item: item["value"], reverse=True)

            leader_idx = merged[change_col].fillna(float("-inf")).idxmax()
            leader_name = ""
            if name_col and leader_idx in merged.index:
                leader_name = str(merged.loc[leader_idx, name_col])

            lagger_idx = merged[change_col].fillna(float("inf")).idxmin()
            lagger_name = ""
            if name_col and lagger_idx in merged.index:
                lagger_name = str(merged.loc[lagger_idx, name_col])

            sector_rows.append({
                "name": sector_name,
                "value": total_market_cap if total_market_cap > 0 else float(stock_count),
                "change_pct": round(weighted_change, 2),
                "stock_count": stock_count,
                "turnover": round(turnover, 2),
                "leading_stock": leader_name,
                "lagging_stock": lagger_name,
                "children": child_stocks,
            })

        if len(sector_rows) < CNMarketLeaders.MIN_PRIMARY_SECTOR_COUNT:
            logger.warning("个股聚合行业数据过少，回退板块接口: count=%s", len(sector_rows))
            return None

        sector_rows.sort(key=lambda item: item["value"], reverse=True)
        return {
            "sectors": sector_rows,
            "count": len(sector_rows),
            "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            "market_status": CNMarketLeaders._get_market_status(),
            "source": "stock_aggregated",
            "mapping_source": CNMarketLeaders._sector_members_source,
        }

    @staticmethod
    def _build_sector_heatmap_from_board() -> Dict[str, Any]:
        """使用板块接口构建热力图（回退方案）。"""
        df = data_provider.get_board_industry_name()
        if df.empty:
            raise ValueError("无法获取行业板块数据")
        df = CNMarketLeaders._filter_primary_sectors(df)

        sectors = []
        for _, row in df.iterrows():
            total_companies = safe_float(row.get("上涨家数", 0)) + safe_float(
                row.get("下跌家数", 0)
            )
            sectors.append({
                "name": str(row["板块名称"]),
                "value": safe_float(row.get("总市值", 0)),
                "change_pct": safe_float(row["涨跌幅"]),
                "stock_count": int(total_companies),
                "turnover": safe_float(row.get("换手率", 0)),
                "leading_stock": str(row.get("领涨股票", "")),
                "lagging_stock": "",
            })

        return {
            "sectors": sectors,
            "count": len(sectors),
            "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            "market_status": CNMarketLeaders._get_market_status(),
            "source": "board_snapshot",
            "mapping_source": CNMarketLeaders._sector_members_source,
        }







    @staticmethod
    @cached(
        "market_cn:sectors:all", ttl=settings.CACHE_TTL["leaders"], stale_ttl=settings.CACHE_TTL["leaders"] * settings.STALE_TTL_RATIO
    )
    def get_all_sectors() -> Dict[str, Any]:
        """
        获取所有行业板块数据 (用于热力图)
        """
        try:
            stock_aggregated = CNMarketLeaders._build_sector_heatmap_from_stocks()
            if stock_aggregated:
                return stock_aggregated

            if CNMarketLeaders._sector_members_source == "missing_local_file":
                return {
                    "error": "本地一级行业映射缺失，请先执行 scripts/refresh_cn_primary_sector_members.py 初始化映射",
                    "sectors": [],
                    "source": "mapping_uninitialized",
                    "mapping_source": CNMarketLeaders._sector_members_source,
                }

            return CNMarketLeaders._build_sector_heatmap_from_board()

        except Exception as e:
            logger.error(f"获取所有板块数据失败: {e}")
            return {"error": str(e), "sectors": []}

    @staticmethod
    def _get_market_status() -> str:
        """获取市场状态"""
        from ...core.utils import is_trading_hours

        if is_trading_hours("market_cn"):
            return "交易中"
        else:
            return "休市"
