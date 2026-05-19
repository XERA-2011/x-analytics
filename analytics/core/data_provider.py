"""
共享数据提供层
避免多个模块重复请求相同的 API 数据
"""

import akshare as ak
import pandas as pd
import threading
import time
from typing import Optional, Callable, Any, Dict
from .logger import logger


class _SourceCircuitBreaker:
    """自适应源熔断器：连续失败超过阈值后进入冷却期，跳过已知不可用的数据源。

    避免每个预热周期浪费 ~8s 在必然失败的重试上。
    冷却期结束后自动允许重试，如果恢复则清零计数器。
    """

    FAILURE_THRESHOLD = 3       # 连续失败次数阈值
    COOLDOWN_SECONDS = 300      # 冷却时间 (5分钟)

    def __init__(self):
        self._failures: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._lock = threading.Lock()

    def record_failure(self, source: str) -> None:
        with self._lock:
            self._failures[source] = self._failures.get(source, 0) + 1
            self._last_failure_time[source] = time.time()

    def record_success(self, source: str) -> None:
        with self._lock:
            self._failures[source] = 0

    def should_skip(self, source: str) -> bool:
        """判断是否应跳过该数据源（处于熔断冷却中）。"""
        with self._lock:
            failures = self._failures.get(source, 0)
            if failures < self.FAILURE_THRESHOLD:
                return False
            last_time = self._last_failure_time.get(source, 0)
            if time.time() - last_time > self.COOLDOWN_SECONDS:
                # 冷却期结束，允许重试
                self._failures[source] = 0
                return False
            return True

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            return {
                source: {
                    "failures": count,
                    "in_cooldown": count >= self.FAILURE_THRESHOLD
                    and now - self._last_failure_time.get(source, 0) < self.COOLDOWN_SECONDS,
                    "cooldown_remaining": max(
                        0,
                        self.COOLDOWN_SECONDS - (now - self._last_failure_time.get(source, 0)),
                    ),
                }
                for source, count in self._failures.items()
                if count > 0
            }


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
    MIN_A_STOCK_SPOT_ROWS = 1000
    MIN_INDUSTRY_BOARD_ROWS = 20
    _breaker = _SourceCircuitBreaker()

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
                    logger.debug(f"Using memory cache: {key}")
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

    def _require_min_rows(self, df: pd.DataFrame, min_rows: int, label: str) -> pd.DataFrame:
        """拒绝明显残缺的列表型行情，避免缓存局部快照。"""
        if df is None or df.empty or len(df) < min_rows:
            actual = 0 if df is None else len(df)
            raise ValueError(f"{label}数据不完整: expected>={min_rows}, actual={actual}")
        return df

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

        logger.info("请求 A 股实时行情...")

        # --- 第一优先级：东方财富 akshare (可被熔断跳过) ---
        if not self._breaker.should_skip("eastmoney_stock"):
            try:
                df = self._fetch_with_retry(ak.stock_zh_a_spot_em)
                df = self._require_min_rows(df, self.MIN_A_STOCK_SPOT_ROWS, "A股实时行情")
                self._breaker.record_success("eastmoney_stock")
                self._set_cached(cache_key, df)
                return df
            except Exception as e:
                self._breaker.record_failure("eastmoney_stock")
                logger.warning(f"akshare A股实时行情调用失败: {e}, 使用回退源")
        else:
            logger.info("跳过东方财富 A 股接口 (熔断冷却中)，直接使用回退源")

        # --- 第二优先级：东方财富直接 API (可被熔断跳过) ---
        if not self._breaker.should_skip("eastmoney_stock_direct"):
            try:
                df = self._fallback_stock_a_spot()
                df = self._require_min_rows(df, self.MIN_A_STOCK_SPOT_ROWS, "A股实时行情直接回退")
                self._breaker.record_success("eastmoney_stock_direct")
                self._set_cached(cache_key, df)
                return df
            except Exception as e2:
                self._breaker.record_failure("eastmoney_stock_direct")
                logger.warning(f"直接 API 也失败: {e2}, 尝试新浪接口")
        else:
            logger.info("跳过东方财富直接 API (熔断冷却中)，使用新浪接口")

        # --- 最终回退：新浪个股接口 ---
        df = self._fallback_stock_a_spot_sina()
        df = self._require_min_rows(df, self.MIN_A_STOCK_SPOT_ROWS, "A股实时行情新浪回退")
        self._set_cached(cache_key, df)
        return df

    def _fallback_stock_a_spot(self) -> pd.DataFrame:
        """
        直接请求东方财富 API 获取 A 股实时行情数据 (akshare 失败时的回退)
        """
        import requests
        import random

        subdomains_pool = ["push2", "17.push2", "28.push2", "29.push2", "40.push2", "91.push2", "82.push2"]
        subdomains = random.sample(subdomains_pool, min(2, len(subdomains_pool)))

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
                    logger.info(f"直接 API 回退成功 ({sub}), 获取 {len(df)} 只股票")
                    return df
            except Exception as e:
                last_err = e
                continue

        raise ValueError(f"所有东方财富 API 子域均不可用: {last_err}")

    def _fallback_stock_a_spot_sina(self) -> pd.DataFrame:
        """
        最后的回退：使用新浪个股行情接口 (拉取时间稍长约8秒)
        将 '成交额' 映射到 '总市值' 供依赖权重的下游使用
        """
        import akshare as ak
        df_sina = self._fetch_with_retry(ak.stock_zh_a_spot)
        
        df = pd.DataFrame()
        df["代码"] = df_sina["代码"]
        df["名称"] = df_sina["名称"]
        df["最新价"] = pd.to_numeric(df_sina["最新价"], errors="coerce")
        df["涨跌幅"] = pd.to_numeric(df_sina["涨跌幅"], errors="coerce")
        df["换手率"] = 0.0  # 新浪接口没有直接暴露换手率
        
        # 将成交额当做市值代理用于防崩溃和粗略加权
        turnover_amount = pd.to_numeric(df_sina["成交额"], errors="coerce")
        df["总市值"] = turnover_amount
        df["流通市值"] = turnover_amount
        
        logger.info(f"新浪 A股 API 降级回退成功, 获取 {len(df)} 只股票")
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

        logger.info("请求行业板块数据...")

        # --- 第一优先级：东方财富 akshare (可被熔断跳过) ---
        if not self._breaker.should_skip("eastmoney_board"):
            try:
                df = self._fetch_with_retry(ak.stock_board_industry_name_em)
                df = self._require_min_rows(df, self.MIN_INDUSTRY_BOARD_ROWS, "行业板块")
                self._breaker.record_success("eastmoney_board")
                self._set_cached(cache_key, df)
                return df
            except Exception as e:
                self._breaker.record_failure("eastmoney_board")
                logger.warning(f"akshare 调用失败: {e}, 使用回退源")
        else:
            logger.info("跳过东方财富板块接口 (熔断冷却中)，直接使用回退源")

        # --- 第二优先级：东方财富直接 API (可被熔断跳过) ---
        if not self._breaker.should_skip("eastmoney_board_direct"):
            try:
                df = self._fallback_board_industry()
                df = self._require_min_rows(df, self.MIN_INDUSTRY_BOARD_ROWS, "行业板块直接回退")
                self._breaker.record_success("eastmoney_board_direct")
                self._set_cached(cache_key, df)
                return df
            except Exception as e2:
                self._breaker.record_failure("eastmoney_board_direct")
                logger.warning(f"直接 API 也失败: {e2}, 使用新浪行业接口")
        else:
            logger.info("跳过东方财富板块直接 API (熔断冷却中)，使用新浪接口")

        # --- 最终回退：新浪行业接口 ---
        df = self._fallback_board_industry_sina()
        df = self._require_min_rows(df, self.MIN_INDUSTRY_BOARD_ROWS, "行业板块新浪回退")
        self._set_cached(cache_key, df)
        return df

    def _fallback_board_industry(self) -> pd.DataFrame:
        """
        直接请求东方财富 API 获取行业板块数据 (akshare 失败时的回退)
        """
        import requests
        import random

        subdomains_pool = ["push2", "17.push2", "28.push2", "29.push2", "40.push2", "91.push2"]
        subdomains = random.sample(subdomains_pool, min(2, len(subdomains_pool)))

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
                    logger.info(f"直接 API 回退成功 ({sub}), 获取 {len(df)} 个板块")
                    return df
            except Exception as e:
                last_err = e
                continue

        raise ValueError(f"所有东方财富 API 子域均不可用: {last_err}")

    def _fallback_board_industry_sina(self) -> pd.DataFrame:
        """
        使用新浪接口作为最后求生回退，映射为近似的东方财富字段格式
        巧妙地将 '总成交额' 映射给 '总市值' 给热力图面积提供良好支撑
        """
        import akshare as ak
        df_sina = self._fetch_with_retry(ak.stock_sector_spot, indicator="新浪行业")
        
        rows = []
        for _, row in df_sina.iterrows():
            rows.append({
                "板块名称": row.get("板块", ""),
                "板块代码": row.get("label", ""),
                "涨跌幅": pd.to_numeric(row.get("涨跌幅"), errors="coerce"),
                "换手率": 0.0, 
                "总市值": pd.to_numeric(row.get("总成交额"), errors="coerce"), 
                "上涨家数": 0,
                "下跌家数": 0,
                "领涨股票": row.get("股票名称", ""),
            })
            
        df = pd.DataFrame(rows)
        logger.info(f"新浪行业 API 降级回退成功, 获取 {len(df)} 个板块")
        return pd.DataFrame(rows)
    
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

        logger.info(f"请求板块成分股: {sector_name}...")
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

        logger.info(f"请求指数行情: {symbol}...")
        df = self._fetch_with_retry(ak.stock_zh_index_spot_em, symbol=symbol)
        self._set_cached(cache_key, df)
        return df

    def get_index_spot_sina_with_fallback(self) -> pd.DataFrame:
        """
        获取新浪指数实时行情，失败时回退到直接 HTTP 请求。

        解决 stock_zh_index_spot_sina 偶尔返回 HTML 页面导致 JSON 解析失败的问题。
        """
        cache_key = "index_spot_sina_fallback"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        # 第一优先级：akshare 新浪指数接口
        if not self._breaker.should_skip("sina_index_spot"):
            try:
                df = self._fetch_with_retry(ak.stock_zh_index_spot_sina, max_retries=2)
                if df is not None and not df.empty:
                    self._breaker.record_success("sina_index_spot")
                    self._set_cached(cache_key, df)
                    return df
            except Exception as e:
                self._breaker.record_failure("sina_index_spot")
                logger.warning(f"新浪指数接口失败: {e}, 尝试直接 HTTP 回退")
        else:
            logger.info("跳过新浪指数接口 (熔断冷却中)，使用直接 HTTP")

        # 第二优先级：直接 HTTP 请求东方财富指数数据
        df = self._fallback_index_spot_direct()
        self._set_cached(cache_key, df)
        return df

    def _fallback_index_spot_direct(self) -> pd.DataFrame:
        """
        直接 HTTP 请求获取核心指数实时行情 (新浪指数接口失败时的回退)
        使用东方财富指数列表 API。
        """
        import requests
        import random

        # 核心指数代码映射: 东方财富代码 -> 新浪代码
        index_mapping = {
            "1.000001": "sh000001",  # 上证指数
            "0.399001": "sz399001",  # 深证成指
            "0.399006": "sz399006",  # 创业板指
            "1.000688": "sh000688",  # 科创50
            "1.000300": "sh000300",  # 沪深300
            "0.399905": "sz399905",  # 中证500
        }

        secids = ",".join(index_mapping.keys())
        subdomains = ["push2", "17.push2", "82.push2"]
        random.shuffle(subdomains)

        params = {
            "secids": secids,
            "fields": "f2,f3,f4,f12,f13,f14,f5,f6,f15,f16,f17,f18",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/",
        }

        for sub in subdomains:
            url = f"http://{sub}.eastmoney.com/api/qt/ulist.np/get"
            try:
                r = requests.get(url, params=params, headers=headers, timeout=5)
                data = r.json()
                if data.get("data") and data["data"].get("diff"):
                    rows = []
                    for item in data["data"]["diff"]:
                        market = str(item.get("f13", ""))
                        code = str(item.get("f12", ""))
                        secid = f"{market}.{code}"
                        sina_code = index_mapping.get(secid, f"{'sh' if market == '1' else 'sz'}{code}")
                        rows.append({
                            "代码": sina_code,
                            "名称": item.get("f14", ""),
                            "最新价": item.get("f2"),
                            "涨跌额": item.get("f4"),
                            "涨跌幅": item.get("f3"),
                            "今开": item.get("f17"),
                            "最高": item.get("f15"),
                            "最低": item.get("f16"),
                            "昨收": item.get("f18"),
                            "成交量": item.get("f5"),
                            "成交额": item.get("f6"),
                        })
                    df = pd.DataFrame(rows)
                    for col in ["最新价", "涨跌额", "涨跌幅", "今开", "最高", "最低", "昨收", "成交量", "成交额"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    logger.info(f"直接 HTTP 指数回退成功 ({sub}), 获取 {len(df)} 个指数")
                    return df
            except Exception:
                continue

        raise ValueError("所有指数回退源均不可用")

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
                "circuit_breaker": self._breaker.get_stats(),
            }


# 全局数据提供层实例
data_provider = SharedDataProvider.get_instance()
