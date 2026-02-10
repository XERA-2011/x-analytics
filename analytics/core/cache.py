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
from typing import Optional, Any, Callable, Dict
from datetime import datetime
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
        self._connect_attempted = False
        self._inflight_tasks = set()  # Track keys currently being refreshed locally

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
    def redis(self) -> Optional[redis.Redis]:
        """懒加载 Redis 连接（使用连接池）
        
        Returns:
            Redis client if connected, None otherwise.
        """
        if self._redis is None and not self._connect_attempted:
            self._connect_attempted = True
            try:
                if self.redis_url is None:
                    raise ValueError("Redis URL is not configured.")
                pool = ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=50,
                    decode_responses=True,
                    socket_connect_timeout=3,
                    socket_timeout=3,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                client = redis.Redis(connection_pool=pool)
                client.ping()
                self._redis = client
                self._connected = True
            except (redis.ConnectionError, redis.TimeoutError, ValueError) as e:
                print(f"⚠️ Redis 连接失败: {e}，将使用无缓存模式")
                self._redis = None
                self._connected = False

        return self._redis

    @property
    def connected(self) -> bool:
        """检查是否已连接"""
        if not self._connect_attempted:
            _ = self.redis  # 触发首次连接
        return self._connected

    def reconnect(self) -> bool:
        """重置连接状态并重新尝试连接 Redis
        
        Returns:
            bool: True if reconnection succeeded.
        """
        self._redis = None
        self._connected = False
        self._connect_attempted = False
        _ = self.redis  # 触发重连
        if self._connected:
            print("✅ Redis 重连成功")
        else:
            print("❌ Redis 重连失败，继续无缓存模式")
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


def wrap_response(
    status: str,
    data: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    cached_at: Optional[float] = None,
    ttl: Optional[int] = None,
) -> Dict[str, Any]:
    """
    包装标准化 API 响应格式
    
    Args:
        status: 'ok' | 'warming_up' | 'error'
        data: 实际数据 (status='ok' 时必填)
        message: 错误/状态消息 (status != 'ok' 时必填)
        cached_at: 缓存时间戳 (Unix timestamp)
        ttl: 剩余有效秒数
    """
    response: Dict[str, Any] = {"status": status}
    
    if status == "ok" and data is not None:
        response["data"] = data
    elif data is not None:
        response["data"] = data
    
    if message:
        response["message"] = message
    
    if cached_at:
        response["cached_at"] = datetime.fromtimestamp(cached_at).isoformat()
    
    if ttl is not None:
        response["ttl"] = ttl
    
    return response


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
                        # 数据新鲜，返回标准格式
                        remaining_ttl = int(expire_time - now)
                        cache_time = cached_data["_meta"].get("cached_at", expire_time - ttl)
                        
                        # 检查数据是否包含错误
                        if isinstance(real_data, dict) and "error" in real_data:
                            return wrap_response(
                                status="error",
                                data=real_data.get("data"),
                                message=real_data.get("message", real_data.get("error")),
                                cached_at=cache_time,
                                ttl=remaining_ttl
                            )
                        
                        return wrap_response(
                            status="ok",
                            data=real_data,
                            cached_at=cache_time,
                            ttl=remaining_ttl
                        )
                    else:
                        # 数据陈旧 (但未物理过期)
                        should_refresh = True
                        return_stale = True
                        stale_data = real_data  # 保存陈旧数据以供后续使用
                else:
                    # 旧版格式或无元数据，假设新鲜
                    if isinstance(cached_data, dict) and "error" in cached_data:
                        return wrap_response(
                            status="error",
                            message=cached_data.get("message", cached_data.get("error"))
                        )
                    return wrap_response(status="ok", data=cached_data)
            else:
                # 无缓存
                should_refresh = True
                return_stale = False
                stale_data = None  # 无陈旧数据可用

            # 3. 需要刷新数据
            if should_refresh:
                # 使用后台线程进行异步刷新，确保不阻塞当前请求
                # 这种模式保证了：
                # 1. 用户请求永远立即返回 (要么是数据，要么是 warming_up)
                # 2. 只有在此进程中未运行任务时才启动新线程 (减少开销)
                # 3. 利用 Redis 锁确保分布式环境下的单一执行
                
                if cache_key not in cache._inflight_tasks:
                    
                    def async_refresh_task():
                        # 标记开始
                        cache._inflight_tasks.add(cache_key)
                        lock_key = f"refresh:{cache_key}"
                        lock = None
                        try:
                            # 尝试获取分布式锁 (非阻塞)
                            lock = cache.lock(lock_key, timeout=60, blocking_timeout=0)
                            if lock.acquire(blocking=False):
                                try:
                                    # Double check (虽然是非阻塞，但在获取锁的过程中可能已有别人更新)
                                    # 仅针对 Cold Start 需要 check，Stale Refresh 无所谓
                                    if not return_stale:
                                        fresh_data = cache.get(cache_key)
                                        if fresh_data and "_meta" in fresh_data and time.time() < fresh_data["_meta"]["expire_at"]:
                                            return

                                    print(f"⚡ [Async] 开始计算: {key_prefix}")
                                    result = func(*args, **kwargs)

                                    if result is not None:
                                        # 结果校验
                                        is_error = False
                                        if isinstance(result, dict) and "error" in result:
                                             # 简单的有效性检查
                                             is_valid = False
                                             for k in ["sectors", "stocks", "data", "indices", "items"]:
                                                 if k in result and result[k]:
                                                     is_valid = True
                                                     break
                                             if not is_valid:
                                                 is_error = True
                                        
                                        if not is_error:
                                            # 写入缓存
                                            current_now = time.time()
                                            
                                            # 物理 TTL
                                            p_ttl = ttl + (stale_ttl if stale_ttl else 0)
                                            
                                            val = {
                                                "_meta": {
                                                    "expire_at": current_now + ttl,
                                                    "cached_at": current_now,
                                                    "ttl": ttl
                                                },
                                                "data": result
                                            }
                                            cache.set(cache_key, val, p_ttl)
                                            print(f"✅ [Async] 缓存更新完成: {key_prefix}")
                                        else:
                                            print(f"⚠️ [Async] 计算结果无效，忽略: {key_prefix}")

                                finally:
                                    try:
                                        lock.release()
                                    except:
                                        pass
                            else:
                                # 未获取到锁，说明其他节点正在计算
                                pass
                        except Exception as e:
                            print(f"❌ [Async] 后台刷新任务异常: {e}")
                        finally:
                            # 标记结束
                            if cache_key in cache._inflight_tasks:
                                cache._inflight_tasks.remove(cache_key)

                    # 启动后台线程
                    threading.Thread(target=async_refresh_task, daemon=True).start()

                # 主线程立即返回
                if return_stale:
                    # 返回陈旧数据但标记为 stale
                    if isinstance(stale_data, dict) and "error" in stale_data:
                        return wrap_response(
                            status="error",
                            message=stale_data.get("message", stale_data.get("error"))
                        )
                    return wrap_response(
                        status="ok",
                        data=stale_data,
                        message="数据刷新中"
                    )
                else:
                    return wrap_response(
                        status="warming_up",
                        message="数据正在后台计算中，请稍后刷新"
                    )

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
            # 检查是否为错误结果，避免缓存失败的数据
            if isinstance(result, dict) and "error" in result:
                has_valid_data = False
                for data_key in ["sectors", "stocks", "data", "indices", "items"]:
                    if data_key in result and result[data_key]:
                        has_valid_data = True
                        break
                if not has_valid_data:
                    print(f"⚠️ 预热检测到错误结果，跳过缓存: {func.__name__} - {result.get('error', 'Unknown')}")
                    return False

            now = time.time()
            prefix = getattr(func, "_cache_prefix", None)  # type: Optional[str]
            ttl = getattr(func, "_cache_ttl", None)  # type: Optional[int]
            stale = getattr(func, "_cache_stale_ttl", 0) or 0

            if prefix is None or ttl is None:
                print(f"❌ 缓存预热失败 [{func.__name__}]: 缺少缓存元数据")
                return False

            key = make_cache_key(prefix, *args, **kwargs)

            val = {"_meta": {"expire_at": now + ttl, "cached_at": now, "ttl": ttl}, "data": result}
            cache.set(key, val, ttl + stale)
            print(f"✅ 缓存预热成功: {prefix}")
            return True
    except Exception as e:
        print(f"❌ 缓存预热失败 [{func.__name__}]: {e}")
    
    # === 故障保护逻辑 ===
    # 如果预热失败（无论是 validation 失败还是 Exception），尝试延长现有缓存的寿命
    try:
        prefix = getattr(func, "_cache_prefix", None)
        if prefix:
             # 我们需要重新计算 key，但这需要 args/kwargs
             # 幸运的是 args/kwargs 就在作用域里
             key = make_cache_key(prefix, *args, **kwargs)
             
             # 获取现有数据
             cached_val = cache.get(key)
             if cached_val and "_meta" in cached_val:
                 # 延长物理 TTL
                 ttl = getattr(func, "_cache_ttl", 60)
                 stale = getattr(func, "_cache_stale_ttl", 0) or 0
                 physical_ttl = ttl + stale
                 
                 # 重新 सेट (SETEX)
                 # 内容不变，只更新过期时间
                 cache.set(key, cached_val, physical_ttl)
                 print(f"🛡️ [预热保护] 已延长现有缓存寿命: {prefix}")
                 return True # 虽然预热新数据失败，但保护了老数据，算作"处理成功"
    except Exception as protect_err:
        print(f"⚠️ [预热保护] 执行失败: {protect_err}")

    return False
