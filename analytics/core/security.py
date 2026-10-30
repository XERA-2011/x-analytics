"""
安全中间件
提供安全响应头、限流、管理 API 保护等功能
"""

from typing import Callable, Optional
from urllib.parse import urlparse
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .rate_limiter import public_limiter, admin_limiter


# 常见自动化爬虫 User-Agent 关键词 (非回环请求时拦截)
DISALLOWED_UA_KEYWORDS = [
    "python-requests",
    "aiohttp",
    "httpx",
    "scrapy",
    "go-http-client",
    "libwww-perl",
    "urllib",
]


def _is_trusted_domain(url_or_domain: Optional[str]) -> bool:
    """检查 Origin 或 Referer 是否属于受信任域名白名单"""
    if not url_or_domain:
        return True
    try:
        if "://" in url_or_domain:
            hostname = (urlparse(url_or_domain).hostname or "").lower()
        else:
            hostname = url_or_domain.split(":")[0].strip().lower()

        if not hostname:
            return False

        # 本地开发与测试环境放行
        if hostname in ("localhost", "127.0.0.1", "testserver"):
            return True

        # 信任 xerafun.com 及其所有子域名 (如 analytics.xerafun.com)
        if hostname == "xerafun.com" or hostname.endswith(".xerafun.com"):
            return True

        # 信任 dpdns.org 及其所有子域名 (如 xera.dpdns.org, sub.xera2011.dpdns.org)
        if hostname == "dpdns.org" or hostname.endswith(".dpdns.org"):
            return True

        # 信任 Cloudflare Pages 个人主站 (xera.pages.dev)
        if hostname == "xera.pages.dev" or hostname.endswith(".xera.pages.dev"):
            return True

        return False
    except Exception:
        return False


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
    "/chart/",
    "/index-valuation/",
    "/gold/",
    "/market-asia/",
    "/market-hk/",
    "/market-western/",
    "/metals/",
    "/ai/",
    "/qdii/",
    "/analytics/api/",
    "/analytics/chart/",
    "/analytics/index-valuation/",
    "/analytics/gold/",
    "/analytics/market-asia/",
    "/analytics/market-hk/",
    "/analytics/market-western/",
    "/analytics/metals/",
    "/analytics/ai/",
    "/analytics/qdii/",
]

# 静态资源 / 健康检查路径（不限流）
STATIC_PATHS = [
    "/js/",
    "/css/",
    "/favicon.ico",
    "/analytics/js/",
    "/analytics/css/",
    "/api/health",
    "/analytics/api/health",
]


def _is_api_path(path: str) -> bool:
    """判断是否为 API 路径。"""
    return any(path.startswith(p) for p in PUBLIC_API_PATHS)


def _is_static_path(path: str) -> bool:
    """判断是否为静态资源路径。"""
    return any(path.startswith(p) for p in STATIC_PATHS)


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP"""
    # 优先从 X-Real-IP 获取 (由 Nginx 等可信反代从 $remote_addr 注入，防止客户端伪造)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 其次从 X-Forwarded-For 获取
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
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
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        client_ip = get_client_ip(request)
        
        # 1. 检查是否为管理 API
        if any(path.startswith(p) for p in ADMIN_API_PATHS):
            from .config import settings
            admin_token = settings.ADMIN_TOKEN
            request_token = request.headers.get("X-Admin-Token")

            # 强制要求配置并匹配有效 ADMIN_TOKEN，严禁仅依靠易伪造的 IP 判定
            if not admin_token or request_token != admin_token:
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": "error",
                        "message": "Forbidden: valid X-Admin-Token required",
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
        
        # 2. 检查是否为公开 API（需要安全与限流防护）
        elif _is_api_path(path):
            if not _is_static_path(path):
                # OPTIONS 预检请求跳过安全与限流拦截，交由 CORSMiddleware 处理
                if request.method != "OPTIONS":
                    # 校验 Origin (防跨站非法调用)
                    origin = request.headers.get("origin")
                    if origin and not _is_trusted_domain(origin):
                        return JSONResponse(
                            status_code=403,
                            content={
                                "status": "error",
                                "message": "Forbidden: untrusted origin",
                            },
                        )

                    # 校验 Referer (防盗链)
                    referer = request.headers.get("referer")
                    if referer and not _is_trusted_domain(referer):
                        return JSONResponse(
                            status_code=403,
                            content={
                                "status": "error",
                                "message": "Forbidden: untrusted referer",
                            },
                        )

                    # 过滤常见未伪装爬虫 UA (仅对外部非回环客户端生效，保留单元测试与内部探测)
                    is_loopback = (
                        client_ip in ("127.0.0.1", "::1", "localhost", "testserver")
                        or client_ip.startswith("127.")
                    )
                    if not is_loopback:
                        user_agent = request.headers.get("user-agent", "").lower()
                        if any(bot in user_agent for bot in DISALLOWED_UA_KEYWORDS):
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "status": "error",
                                    "message": "Forbidden: automated requests disallowed",
                                },
                            )

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
        if _is_api_path(path):
            # API 响应禁用缓存，避免客户端使用过期数据
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif path in ["/", "/index.html", "/analytics", "/analytics/"] or path.endswith(".html"):
            # HTML 入口文件严格禁止任何缓存（解决微信等移动端 WebView 强缓存旧页面问题）
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        else:
            # 静态资源 (JS/CSS/字体/图标) 允许协商缓存
            response.headers["Cache-Control"] = "public, max-age=86400, must-revalidate"
        
        # 添加限流信息头（仅 API 请求）
        if _is_api_path(path):
            remaining = public_limiter.get_remaining(client_ip)
            response.headers["X-RateLimit-Limit"] = str(public_limiter.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
