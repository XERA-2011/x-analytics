"""
API 限流器
基于内存的简单限流实现，防止 API 滥用
"""

import time
import threading
from typing import Dict
from collections import defaultdict


class RateLimiter:
    """
    基于滑动窗口的内存限流器
    
    使用方法:
        limiter = RateLimiter(requests_per_minute=60)
        if not limiter.is_allowed(client_ip):
            raise HTTPException(429, "Too Many Requests")
    """
    
    def __init__(self, requests_per_minute: int = 60, cleanup_interval: int = 60):
        """
        初始化限流器
        
        Args:
            requests_per_minute: 每分钟允许的请求数
            cleanup_interval: 清理过期记录的间隔（秒）
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1分钟窗口
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
        self.cleanup_interval = cleanup_interval
    
    def is_allowed(self, client_id: str) -> bool:
        """
        检查客户端是否允许请求
        
        Args:
            client_id: 客户端标识（通常是 IP 地址）
            
        Returns:
            True 允许请求，False 拒绝请求
        """
        now = time.time()
        window_start = now - self.window_size
        
        with self._lock:
            # 清理过期记录
            if now - self._last_cleanup > self.cleanup_interval:
                self._cleanup(window_start)
                self._last_cleanup = now
            
            # 获取该客户端的请求记录
            requests = self._requests[client_id]
            
            # 移除窗口外的请求
            requests[:] = [ts for ts in requests if ts > window_start]
            
            # 检查是否超过限制
            if len(requests) >= self.requests_per_minute:
                return False
            
            # 记录本次请求
            requests.append(now)
            return True
    
    def get_remaining(self, client_id: str) -> int:
        """获取剩余可用请求数"""
        now = time.time()
        window_start = now - self.window_size
        
        with self._lock:
            requests = self._requests.get(client_id, [])
            valid_requests = [ts for ts in requests if ts > window_start]
            return max(0, self.requests_per_minute - len(valid_requests))
    
    def _cleanup(self, cutoff_time: float) -> None:
        """清理过期的请求记录"""
        empty_keys = []
        for client_id, requests in self._requests.items():
            requests[:] = [ts for ts in requests if ts > cutoff_time]
            if not requests:
                empty_keys.append(client_id)
        
        for key in empty_keys:
            del self._requests[key]


# 全局限流器实例
# 公开 API: 60 次/分钟
public_limiter = RateLimiter(requests_per_minute=60)

# 管理 API: 10 次/分钟
admin_limiter = RateLimiter(requests_per_minute=10)
