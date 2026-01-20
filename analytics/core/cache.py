#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Redis 缓存模块
提供统一的缓存接口和装饰器
支持防雪崩(Locking)和陈旧数据即使返回(Stale-While-Revalidate)
"""

import json
import hashlib
import redis
from redis import ConnectionPool
import time
import threading
from functools import wraps
from typing import Optional, Any, Callable
from .config import settings

# 缓存版本号：当缓存数据结构变化时递增，自动使旧缓存失效
CACHE_VERSION = "v2"


class RedisCache:
    """Redis 缓存封装类"""

    _instance: Optional["RedisCache"] = None
    _instance_lock = threading.Lock()  # 线程安全锁

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化 Redis 连接

        Args:
            redis_url: Redis 连接 URL，默认从配置读取
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
        self._connected = False

    @classmethod
    def get_instance(cls) -> "RedisCache":
        """获取单例实例（线程安全）"""
        if cls._instance is None:
            with cls._instance_lock:
                # 双重检查锁定模式
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def redis(self) -> redis.Redis:
        """懒加载 Redis 连接（使用连接池）"""
        if self._redis is None:
            try:
                # 使用连接池管理连接
                if self.redis_url is None:
                    raise ValueError("Redis URL is not configured.")
                pool = ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=10,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                self._redis = redis.Redis(connection_pool=pool)
                # 测试连接
                self._redis.ping()
                self._connected = True
            except redis.ConnectionError as e:
                print(f"⚠️ Redis 连接失败: {e}，将使用无缓存模式")
                self._connected = False
        if self._redis is None:
            # Try to connect if lazy initialization
            if self.redis_url:
                self._redis = redis.Redis.from_url(
                    self.redis_url, decode_responses=True
                )
            else:
                return redis.Redis()  # Fallback or error

        return self._redis

    @property
    def connected(self) -> bool:
        """检查是否已连接"""
        if self._redis is None:
            _ = self.redis  # 触发连接
        return self._connected

    def get(self, key: str) -> Optional[dict]:
        """获取缓存值"""
        if not self.connected:
            return None
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"缓存读取失败 [{key}]: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """设置缓存值"""
        if not self.connected:
            return False
        try:
            self.redis.setex(
                key, ttl, json.dumps(value, ensure_ascii=False, default=str)
            )
            return True
        except (redis.RedisError, TypeError) as e:
            print(f"缓存写入失败 [{key}]: {e}")
        return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.connected:
            return False
        try:
            self.redis.delete(key)
            return True
        except redis.RedisError as e:
            print(f"缓存删除失败 [{key}]: {e}")
        return False

    def delete_pattern(self, pattern: str) -> int:
        """批量删除"""
        if not self.connected:
            return 0
        try:
            keys = list(self.redis.scan_iter(match=pattern))
            if keys:
                return self.redis.delete(*keys)
        except redis.RedisError as e:
            print(f"批量删除失败 [{pattern}]: {e}")
        return 0

    def get_stats(self) -> dict:
        """获取统计（包含命中率）"""
        if not self.connected:
            return {"connected": False, "error": "Redis 未连接"}
        try:
            memory_info = self.redis.info("memory")
            stats_info = self.redis.info("stats")

            # 计算命中率
            hits = stats_info.get("keyspace_hits", 0)
            misses = stats_info.get("keyspace_misses", 0)
            total = hits + misses
            hit_rate = round(hits / total * 100, 2) if total > 0 else 0

            # 获取缓存键数量
            keys_count = len(
                list(
                    self.redis.scan_iter(
                        match=f"{settings.CACHE_PREFIX}:{CACHE_VERSION}:*", count=1000
                    )
                )
            )

            return {
                "connected": True,
                "version": CACHE_VERSION,
                "keys_count": keys_count,
                "hit_rate": f"{hit_rate}%",
                "hits": hits,
                "misses": misses,
                "memory": {
                    "used_memory_human": memory_info.get("used_memory_human"),
                    "used_memory_peak_human": memory_info.get("used_memory_peak_human"),
                },
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def lock(self, name: str, timeout: int = 10, blocking_timeout: int = 5):
        """获取分布式锁"""
        if not self.connected:
            # 如果没连接，返回一个假的上下文管理器，不做任何事
            class DummyLock:
                def __enter__(self):
                    return True

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

                def acquire(self, blocking=True):
                    return True

                def release(self):
                    pass

            return DummyLock()

        return self.redis.lock(
            f"lock:{name}", timeout=timeout, blocking_timeout=blocking_timeout
        )


# 全局缓存实例
cache = RedisCache.get_instance()


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """生成缓存键（包含版本号，使用 SHA256 哈希）"""
    params_str = json.dumps(
        {"args": args, "kwargs": kwargs}, sort_keys=True, default=str
    )
    # 使用 SHA256 替代 MD5，取前 12 位以减少碰撞风险
    params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:12]
    return f"{settings.CACHE_PREFIX}:{CACHE_VERSION}:{prefix}:{params_hash}"


def cached(key_prefix: str, ttl: int = 60, stale_ttl: Optional[int] = None):
    """
    缓存装饰器 (支持防雪崩和陈旧数据返回)

    Args:
        key_prefix: 缓存键前缀
        ttl: 逻辑过期时间 (秒)，在此时间内认为是"新鲜"的
        stale_ttl: 陈旧数据容忍时间 (秒)。
                   如果设置了此值，Redis 物理过期时间 = ttl + stale_ttl。
                   当数据处于 [ttl, ttl+stale_ttl] 之间时，认为是"陈旧"的：
                   - 当前请求会尝试获取锁去刷新数据
                   - 如果获取不到锁(别人在刷)，则直接返回陈旧数据(Stale-While-Revalidate)

    Usage:
        @cached("market:overview", ttl=60, stale_ttl=300)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1. 生成缓存 key
            cache_key = make_cache_key(key_prefix, *args, **kwargs)

            # 2. 尝试获取缓存
            cached_data = cache.get(cache_key)

            now = time.time()
            should_refresh = False
            return_stale = False

            if cached_data is not None:
                # 检查是否包含元数据 (新版缓存结构)
                if isinstance(cached_data, dict) and "_meta" in cached_data:
                    expire_time = cached_data["_meta"].get("expire_at", 0)
                    real_data = cached_data["data"]

                    if now < expire_time:
                        # 数据新鲜，直接返回
                        if isinstance(real_data, dict):
                            real_data["_cached"] = True
                            real_data["_fresh"] = True
                        return real_data
                    else:
                        # 数据陈旧 (但未物理过期)
                        should_refresh = True
                        return_stale = True
                else:
                    # 旧版格式或无元数据，假设新鲜（或依赖 Redis 物理过期）
                    # 为了兼容，如果正好遇到旧数据，直接返回
                    if isinstance(cached_data, dict):
                        cached_data["_cached"] = True
                    return cached_data
            else:
                # 无缓存
                should_refresh = True
                return_stale = False

            # 3. 需要刷新数据
            if should_refresh:
                lock_key = f"refresh:{cache_key}"
                blocking = not return_stale

                try:
                    # 获取锁
                    lock = cache.lock(
                        lock_key, timeout=30, blocking_timeout=5 if blocking else 0
                    )
                    acquired = lock.acquire(blocking=blocking)

                    if acquired:
                        try:
                            # 再次检查缓存 (双重检查) - 仅针对 Cache Miss 的情况
                            if not return_stale:
                                retry_data = cache.get(cache_key)
                                if retry_data and "_meta" in retry_data:
                                    if now < retry_data["_meta"]["expire_at"]:
                                        return retry_data["data"]

                            # 执行原函数
                            print(f"⚡ 计算新数据: {key_prefix}")
                            result = func(*args, **kwargs)

                            if result is not None:
                                # 重新获取当前时间，确保 TTL 是相对于计算完成时间的
                                current_now = time.time()

                                # 构造带元数据的缓存结构
                                # 物理 TTL = ttl + (stale_ttl if set else 0)
                                physical_ttl = ttl + (stale_ttl if stale_ttl else 0)

                                cache_value = {
                                    "_meta": {
                                        "expire_at": current_now + ttl,
                                        "ttl": ttl,
                                    },
                                    "data": result,
                                }
                                cache.set(cache_key, cache_value, physical_ttl)

                                if isinstance(result, dict):
                                    result["_cached"] = False
                                return result

                        finally:
                            try:
                                lock.release()
                            except redis.RedisError:
                                pass
                    else:
                        # 未获取到锁
                        if return_stale:
                            print(f"🔒 正在刷新中，返回陈旧数据: {key_prefix}")
                            if isinstance(real_data, dict):
                                real_data["_cached"] = True
                                real_data["_stale"] = True
                            return real_data
                        else:
                            # Cache Miss 且获取锁失败 (超时)
                            print(f"⚠️ 获取锁超时，强制执行: {key_prefix}")
                            result = func(*args, **kwargs)
                            return result

                except Exception as e:
                    print(f"❌ 缓存刷新异常: {e}")
                    # 异常降级
                    return func(*args, **kwargs)

            return None  # Should not reach here

        # 保存元数据
        wrapper._original = func  # type: ignore
        wrapper._cache_prefix = key_prefix  # type: ignore
        wrapper._cache_ttl = ttl  # type: ignore
        wrapper._cache_stale_ttl = stale_ttl  # type: ignore

        return wrapper

    return decorator


def warmup_cache(func: Callable, *args, **kwargs) -> bool:
    """预热缓存"""
    if not hasattr(func, "_original"):
        return False

    try:
        # 直接调用原函数
        result = func._original(*args, **kwargs)
        if result is not None:
            now = time.time()
            prefix = getattr(func, "_cache_prefix", None)  # type: Optional[str]
            ttl = getattr(func, "_cache_ttl", None)  # type: Optional[int]
            stale = getattr(func, "_cache_stale_ttl", 0) or 0

            if prefix is None or ttl is None:
                print(f"❌ 缓存预热失败 [{func.__name__}]: 缺少缓存元数据")
                return False

            key = make_cache_key(prefix, *args, **kwargs)

            val = {"_meta": {"expire_at": now + ttl, "ttl": ttl}, "data": result}
            cache.set(key, val, ttl + stale)
            print(f"✅ 缓存预热成功: {prefix}")
            return True
    except Exception as e:
        print(f"❌ 缓存预热失败 [{func.__name__}]: {e}")
    return False
