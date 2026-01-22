"""
安全中间件
提供安全响应头、限流、管理 API 保护等功能
"""

import os
from typing import Optional, Callable
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .rate_limiter import public_limiter, admin_limiter


# 管理 API 路径前缀 (支持有无 /analytics 前缀)
ADMIN_API_PATHS = [
    "/api/cache/",
    "/api/scheduler/",
    "/analytics/api/cache/",
    "/analytics/api/scheduler/",
]

# 公开 API 路径前缀（需要限流但不需要认证）
PUBLIC_API_PATHS = [
    "/api/",
    "/market-cn/",
    "/market-us/",
    "/metals/",
    "/analytics/api/",
    "/analytics/market-cn/",
    "/analytics/market-us/",
    "/analytics/metals/",
]

# 静态资源路径（不限流）
STATIC_PATHS = [
    "/js/",
    "/css/",
    "/favicon.ico",
    "/analytics/js/",
    "/analytics/css/",
]


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP"""
    # 优先从 X-Forwarded-For 头获取（反向代理场景）
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # 取第一个 IP（最原始的客户端）
        return forwarded.split(",")[0].strip()
    
    # 其次从 X-Real-IP 获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 最后使用直接连接的 IP
    if request.client:
        return request.client.host
    
    return "unknown"


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    安全中间件
    
    功能:
    1. 添加安全响应头
    2. API 限流
    3. 管理 API Token 验证
    """
    
    def __init__(self, app, admin_token: Optional[str] = None):
        super().__init__(app)
        # 从环境变量获取管理 Token
        self.admin_token = admin_token or os.getenv("ADMIN_TOKEN")
    
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        client_ip = get_client_ip(request)
        
        # 1. 检查是否为管理 API
        if any(path.startswith(p) for p in ADMIN_API_PATHS):
            # 验证 Admin Token
            if not self._verify_admin_token(request):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "message": "Invalid or missing admin token",
                    }
                )
            
            # 管理 API 限流
            if not admin_limiter.is_allowed(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": "Rate limit exceeded for admin API",
                        "retry_after": 60,
                    }
                )
        
        # 2. 检查是否为公开 API（需要限流）
        elif any(path.startswith(p) for p in PUBLIC_API_PATHS):
            if not any(path.startswith(p) for p in STATIC_PATHS):
                if not public_limiter.is_allowed(client_ip):
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Too Many Requests",
                            "message": "Rate limit exceeded",
                            "retry_after": 60,
                        }
                    )
        
        # 3. 调用实际处理函数
        response = await call_next(request)
        
        # 4. 添加安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, max-age=0"
        
        # 添加限流信息头（仅 API 请求）
        if any(path.startswith(p) for p in PUBLIC_API_PATHS):
            remaining = public_limiter.get_remaining(client_ip)
            response.headers["X-RateLimit-Limit"] = str(public_limiter.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _verify_admin_token(self, request: Request) -> bool:
        """验证管理 Token"""
        # 如果没有配置 Token，拒绝所有管理请求
        if not self.admin_token:
            return False
        
        # 从请求头获取 Token
        provided_token = request.headers.get("X-Admin-Token")
        if not provided_token:
            return False
        
        # 时间安全比较
        return self.admin_token == provided_token
