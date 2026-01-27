"""
API Rate Limiter
Redis-based distributed rate limiting with fail-open policy.
"""

import time
from typing import Optional
from .cache import cache
from .logger import logger

class RateLimiter:
    """
    Redis-based Fixed Window Rate Limiter
    
    Falls back to allowing requests (Fail Open) if Redis is unavailable.
    """
    
    def __init__(self, requests_per_minute: int = 60, namespace: str = "global"):
        self.requests_per_minute = requests_per_minute
        self.namespace = namespace
    
    def _get_key(self, client_id: str) -> str:
        # Fixed window: 1-minute buckets
        timestamp = int(time.time() // 60)
        return f"rate_limit:{self.namespace}:{client_id}:{timestamp}"

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        if not cache.connected:
            return True # Fail open
            
        try:
            key = self._get_key(client_id)
            
            # Atomic INCR + EXPIRE
            # Using pipeline to ensure atomicity of command submission
            pipe = cache.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, 90) # Expire after 90s to keep it clean (window is 60s)
            results = pipe.execute()
            
            count = results[0]
            # If this is the first request (count=1), it means we just created the key
            
            return count <= self.requests_per_minute
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True # Fail open

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for current window"""
        if not cache.connected:
            return self.requests_per_minute

        try:
            key = self._get_key(client_id)
            count_str = cache.redis.get(key)
            count = int(count_str) if count_str else 0
            return max(0, self.requests_per_minute - count)
        except Exception:
            return self.requests_per_minute


# Global Instances
# Public API: 300 requests/minute
public_limiter = RateLimiter(requests_per_minute=300, namespace="public")

# Admin API: 10 requests/minute
admin_limiter = RateLimiter(requests_per_minute=10, namespace="admin")
