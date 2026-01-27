
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

class TestRedisRateLimiter(unittest.TestCase):
    def test_fail_open(self):
        print("\n--- Test 1: Fail Open (No Redis Connection) ---")
        # Mock the cache object imported in rate_limiter.py
        with patch("analytics.core.rate_limiter.cache") as mock_cache:
            mock_cache.connected = False
            
            from analytics.core.rate_limiter import RateLimiter
            limiter = RateLimiter(requests_per_minute=2, namespace="test_fail_open")
            
            # Should allow everything
            r1 = limiter.is_allowed('ip1')
            r2 = limiter.is_allowed('ip1')
            r3 = limiter.is_allowed('ip1')
            
            print(f"Req 1: {r1}")
            print(f"Req 2: {r2}")
            print(f"Req 3: {r3}")
            
            self.assertTrue(r1)
            self.assertTrue(r2)
            self.assertTrue(r3)
            print("✅ Fail Open Test Passed")

    def test_redis_logic(self):
        print("\n--- Test 2: Redis Logic (Mocked) ---")
        
        with patch("analytics.core.rate_limiter.cache") as mock_cache:
            mock_cache.connected = True
            mock_pipeline = MagicMock()
            mock_cache.redis.pipeline.return_value = mock_pipeline
            
            # Mock pipeline execution results
            # Req 1: count=1
            # Req 2: count=2
            # Req 3: count=3 (Blocked, limit=2)
            mock_pipeline.execute.side_effect = [[1], [2], [3]]
            
            from analytics.core.rate_limiter import RateLimiter
            limiter = RateLimiter(requests_per_minute=2, namespace="test_redis")
            
            r1 = limiter.is_allowed('ip2')
            print(f"Req 1 (Count 1): {r1}")
            
            r2 = limiter.is_allowed('ip2')
            print(f"Req 2 (Count 2): {r2}")
            
            r3 = limiter.is_allowed('ip2')
            print(f"Req 3 (Count 3): {r3}")
            
            self.assertTrue(r1)
            self.assertTrue(r2)
            self.assertFalse(r3)
            print("✅ Redis Logic Test Passed")

if __name__ == "__main__":
    unittest.main()
