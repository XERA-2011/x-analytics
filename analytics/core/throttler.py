"""
全局请求节流器
限制 AkShare API 请求频率，防止 IP 被封禁
"""

import time
import random
import threading
from typing import Optional, List


class RequestThrottler:
    """
    全局请求节流器

    特性:
    - 限制每分钟最大请求数
    - 请求前随机延迟 (模拟人类行为)
    - 线程安全
    """

    _instance: Optional["RequestThrottler"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        max_requests_per_minute: int = 10,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
    ):
        """
        初始化节流器

        Args:
            max_requests_per_minute: 每分钟最大请求数
            min_delay: 最小随机延迟 (秒)
            max_delay: 最大随机延迟 (秒)
        """
        self.max_rpm = max_requests_per_minute
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._requests: List[float] = []
        self._request_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "RequestThrottler":
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def wait_if_needed(self) -> float:
        """
        如果超过速率限制，则等待

        Returns:
            float: 实际等待时间 (秒)
        """
        with self._request_lock:
            now = time.time()
            total_wait = 0.0

            # 清理 60 秒前的请求记录
            self._requests = [t for t in self._requests if now - t < 60]

            # 检查是否超过限制
            if len(self._requests) >= self.max_rpm:
                # 计算需要等待的时间
                oldest_request = self._requests[0]
                wait_time = 60 - (now - oldest_request) + 0.1  # 额外 0.1s 缓冲
                if wait_time > 0:
                    print(f"⏳ 请求频率过高，等待 {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    total_wait += wait_time
                    now = time.time()
                    # 重新清理
                    self._requests = [t for t in self._requests if now - t < 60]

            # 添加随机延迟 (模拟人类行为)
            random_delay = random.uniform(self.min_delay, self.max_delay)
            time.sleep(random_delay)
            total_wait += random_delay

            # 记录本次请求
            self._requests.append(time.time())

            return total_wait

    def get_stats(self) -> dict:
        """获取节流器统计信息"""
        with self._request_lock:
            now = time.time()
            recent_requests = [t for t in self._requests if now - t < 60]
            return {
                "requests_last_minute": len(recent_requests),
                "max_requests_per_minute": self.max_rpm,
                "remaining_quota": max(0, self.max_rpm - len(recent_requests)),
            }


# 全局节流器实例
throttler = RequestThrottler.get_instance()
