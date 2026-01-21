"""
共享数据提供层
避免多个模块重复请求相同的 API 数据
"""

import akshare as ak
import pandas as pd
import threading
import time
from typing import Optional, Callable, Any, Dict
from .throttler import throttler


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

    def __init__(self, memory_cache_ttl: int = 30):
        """
        初始化数据提供层

        Args:
            memory_cache_ttl: 内存缓存过期时间 (秒)
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
        # 使用带重试的调用
        df = self._fetch_with_retry(ak.stock_zh_a_spot_em)
        self._set_cached(cache_key, df)
        return df

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
        df = self._fetch_with_retry(ak.stock_board_industry_name_em)
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
