"""
共享数据提供层
避免多个模块重复请求相同的 API 数据
"""

import akshare as ak
import pandas as pd
import threading
import time
from typing import Optional, Callable, Any, Dict


class SharedDataProvider:
    """
    共享数据提供层

    功能:
    - 缓存常用的 AkShare API 调用结果
    - 短期内存缓存 (默认 30 秒)
    - 避免多个模块同时请求相同数据
    - 自动使用全局节流器
    """

    _instance: Optional["SharedDataProvider"] = None
    _lock = threading.Lock()

    def __init__(self, memory_cache_ttl: int = 300):
        """
        初始化数据提供层

        Args:
            memory_cache_ttl: 内存缓存过期时间 (秒)，默认5分钟以减少API调用频率
        """
        self.memory_cache_ttl = memory_cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SharedDataProvider":
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_cached(self, key: str) -> Optional[Any]:
        """获取内存缓存"""
        with self._cache_lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.memory_cache_ttl:
                    print(f"📦 使用内存缓存: {key}")
                    return entry["data"]
                else:
                    # 过期，删除
                    del self._cache[key]
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        """设置内存缓存"""
        with self._cache_lock:
            self._cache[key] = {
                "data": data,
                "timestamp": time.time(),
            }

    def _fetch_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """使用带重试和节流的机制获取数据"""
        from .utils import akshare_call_with_retry
        return akshare_call_with_retry(func, *args, **kwargs)

    # =========================================================================
    # 常用数据接口
    # =========================================================================

    def get_stock_zh_a_spot(self) -> pd.DataFrame:
        """
        获取 A 股实时行情数据

        多个模块共享:
        - heat.py (市场热度)
        - dividend.py (红利策略)
        - 其他需要全市场数据的模块
        """
        cache_key = "stock_zh_a_spot_em"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        print("🌐 请求 A 股实时行情...")
        try:
            # 使用带重试的调用
            df = self._fetch_with_retry(ak.stock_zh_a_spot_em)
        except Exception as e:
            print(f"⚠️ akshare A股实时行情调用失败: {e}, 使用直接 API 回退")
            df = self._fallback_stock_a_spot()
            
        self._set_cached(cache_key, df)
        return df

    def _fallback_stock_a_spot(self) -> pd.DataFrame:
        """
        直接请求东方财富 API 获取 A 股实时行情数据 (akshare 失败时的回退)
        """
        import requests
        import random

        subdomains = ["push2", "17.push2", "28.push2", "29.push2", "40.push2", "91.push2", "82.push2"]
        random.shuffle(subdomains)

        params = {
            "pn": "1",
            "pz": "10000",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
            "fields": "f12,f14,f2,f3,f8,f20,f21",
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/"
        }

        last_err = None
        for sub in subdomains:
            url = f"http://{sub}.eastmoney.com/api/qt/clist/get"
            try:
                r = requests.get(url, params=params, headers=headers, timeout=5)
                data = r.json()
                if data.get("data") and data["data"].get("diff"):
                    items = data["data"]["diff"]
                    rows = []
                    for item in items:
                        rows.append({
                            "代码": item.get("f12", ""),
                            "名称": item.get("f14", ""),
                            "最新价": item.get("f2"),
                            "涨跌幅": item.get("f3"),
                            "换手率": item.get("f8"),
                            "总市值": item.get("f20"),
                            "流通市值": item.get("f21"),
                        })
                    df = pd.DataFrame(rows)
                    for col in ["最新价", "涨跌幅", "换手率", "总市值", "流通市值"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    print(f"✅ 直接 API 回退成功 ({sub}), 获取 {len(df)} 只股票")
                    return df
            except Exception as e:
                last_err = e
                continue

        raise ValueError(f"所有东方财富 API 子域均不可用: {last_err}")

    def get_board_industry_name(self) -> pd.DataFrame:
        """
        获取行业板块数据

        多个模块共享:
        - leaders.py (领涨领跌)
        - market.py (板块分析)
        """
        cache_key = "stock_board_industry_name_em"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        print("🌐 请求行业板块数据...")
        try:
            df = self._fetch_with_retry(ak.stock_board_industry_name_em)
        except Exception as e:
            print(f"⚠️ akshare 调用失败: {e}, 使用直接 API 回退")
            df = self._fallback_board_industry()
        self._set_cached(cache_key, df)
        return df

    def _fallback_board_industry(self) -> pd.DataFrame:
        """
        直接请求东方财富 API 获取行业板块数据 (akshare 失败时的回退)
        """
        import requests
        import random

        subdomains = ["push2", "17.push2", "28.push2", "29.push2", "40.push2", "91.push2"]
        random.shuffle(subdomains)

        params = {
            "pn": "1",
            "pz": "2000",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:90 t:2 f:!50",
            "fields": "f3,f8,f12,f14,f20,f104,f105,f128,f140",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/"
        }

        last_err = None
        for sub in subdomains:
            url = f"http://{sub}.eastmoney.com/api/qt/clist/get"
            try:
                r = requests.get(url, params=params, headers=headers, timeout=10)
                data = r.json()
                if data.get("data") and data["data"].get("diff"):
                    items = data["data"]["diff"]
                    rows = []
                    for item in items:
                        rows.append({
                            "板块名称": item.get("f14", ""),
                            "板块代码": item.get("f12", ""),
                            "涨跌幅": item.get("f3"),
                            "换手率": item.get("f8"),
                            "总市值": item.get("f20"),
                            "上涨家数": item.get("f104"),
                            "下跌家数": item.get("f105"),
                            "领涨股票": item.get("f140", ""),
                        })
                    df = pd.DataFrame(rows)
                    for col in ["涨跌幅", "换手率", "总市值", "上涨家数", "下跌家数"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    print(f"✅ 直接 API 回退成功 ({sub}), 获取 {len(df)} 个板块")
                    return df
            except Exception as e:
                last_err = e
                continue

        raise ValueError(f"所有东方财富 API 子域均不可用: {last_err}")
    
    def get_sector_constituents(self, sector_name: str) -> pd.DataFrame:
        """
        获取板块成分股
        
        Args:
            sector_name: 板块名称 (e.g. "贵金属")
        """
        cache_key = f"stock_board_industry_cons_em:{sector_name}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        print(f"🌐 请求板块成分股: {sector_name}...")
        df = self._fetch_with_retry(ak.stock_board_industry_cons_em, symbol=sector_name)
        self._set_cached(cache_key, df)
        return df

    def get_index_spot(self, symbol: str = "沪深重要指数") -> pd.DataFrame:
        """
        获取指数实时行情

        Args:
            symbol: 指数类型
        """
        cache_key = f"stock_zh_index_spot_em:{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        print(f"🌐 请求指数行情: {symbol}...")
        df = self._fetch_with_retry(ak.stock_zh_index_spot_em, symbol=symbol)
        self._set_cached(cache_key, df)
        return df

    def clear_cache(self) -> int:
        """清除所有内存缓存"""
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._cache_lock:
            now = time.time()
            valid_count = sum(
                1
                for entry in self._cache.values()
                if now - entry["timestamp"] < self.memory_cache_ttl
            )
            return {
                "total_cached": len(self._cache),
                "valid_cached": valid_count,
                "memory_cache_ttl": self.memory_cache_ttl,
            }


# 全局数据提供层实例
data_provider = SharedDataProvider.get_instance()
