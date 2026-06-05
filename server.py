import os

# 生产环境禁用 tqdm 进度条，避免与日志交叉混排
os.environ.setdefault("TQDM_DISABLE", "1")

import uvicorn
import threading
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from analytics.core.cache import cache, request_refresh_var
from analytics.core import scheduler, settings
from analytics.core.scheduler import setup_default_jobs, initial_warmup
from analytics.api import market_cn, metals, market_us, market_hk, etf
from analytics.core.patch import apply_patches
from analytics.core.security import SecurityMiddleware
from analytics.core.logger import logger

# 应用 API 伪装补丁 (在最早的时机)
apply_patches()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    from analytics.core.db import init_db, close_db

    # 启动时
    logger.info("🚀 x-analytics 服务启动中...")
    
    # 初始化数据库
    await init_db()

    # 将主事件循环注入 scheduler，供后台线程执行 DB 异步操作
    import asyncio
    from analytics.core.scheduler import set_main_loop
    set_main_loop(asyncio.get_event_loop())

    from analytics.core.db import DB_AVAILABLE
    if not DB_AVAILABLE:
        logger.warning("⚠️ Database not available — history/snapshot features disabled")

    # 检查 Redis 连接
    if cache.connected:
        logger.info(f"✅ Redis 已连接: {cache.redis_url}")

        # 启动后台初始预热（非阻塞）
        warmup_thread = threading.Thread(target=initial_warmup, daemon=True)
        warmup_thread.start()

        # 设置并启动调度器
        setup_default_jobs()
        scheduler.start()
    else:
        logger.warning("Redis 未连接，将以无缓存模式运行")

    yield

    # 关闭时
    logger.info("🛑 x-analytics 服务关闭中...")
    scheduler.shutdown(wait=False)
    await close_db()


# 创建 FastAPI 应用
app = FastAPI(
    title="x-analytics API",
    description="三大板块金融数据分析服务：中国市场、美国市场、有色金属",
    version=settings.VERSION,
    root_path="/analytics",
    lifespan=lifespan,
    # 安全：隐藏 OpenAPI 文档（生产环境可取消注释）
    # docs_url=None,
    # redoc_url=None,
)

# -----------------------------------------------------------------------------
# 安全中间件 (顺序重要：先添加的后执行)
# -----------------------------------------------------------------------------

# 1. 安全中间件（限流 + Token 验证 + 安全头）
app.add_middleware(SecurityMiddleware)

# 2. CORS 配置 - 限制跨域访问
#    由于前端和 API 在同一域名下，不需要开放 CORS
#    如需开放特定域名，在 allow_origins 中添加
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # 空列表 = 仅同源请求
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-Admin-Token"],  # 仅允许必要的自定义头
)

class RefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract _refresh from query string
        refresh_token = request.query_params.get("_refresh")
        
        # Set context variable
        token = request_refresh_var.set(bool(refresh_token))
        try:
            response = await call_next(request)
            return response
        finally:
            request_refresh_var.reset(token)

app.add_middleware(RefreshMiddleware)

# -----------------------------------------------------------------------------
# 注册路由模块
# -----------------------------------------------------------------------------
app.include_router(market_cn.router, prefix="/market-cn", tags=["China Market"])
app.include_router(market_us.router, prefix="/market-us", tags=["US Market"])
app.include_router(metals.router, prefix="/metals", tags=["Precious Metals"])
app.include_router(market_hk.router, prefix="/market-hk", tags=["HK Market"])
app.include_router(etf.router, prefix="/etf", tags=["ETF"])




# -----------------------------------------------------------------------------
# 系统管理 API
# -----------------------------------------------------------------------------
@app.get("/api/health", tags=["系统"], summary="服务健康检查")
def health_check():
    # 隐藏 Redis URL 中的密码
    redis_host = None
    if cache.connected and cache.redis_url:
        # 从 redis://:password@host:port/db 中提取 host:port
        import re
        match = re.search(r'@([^/]+)', cache.redis_url)
        if match:
            redis_host = match.group(1)
        else:
            # 无密码格式: redis://host:port/db
            match = re.search(r'redis://([^/]+)', cache.redis_url)
            if match:
                redis_host = match.group(1)
    
    from analytics.core.data_provider import data_provider

    cache_stats = cache.get_stats()

    return {
        "status": "ok",
        "service": "x-analytics",
        "version": settings.VERSION,
        "cache": {
            "connected": cache.connected,
            "host": redis_host,
            "keys_count": cache_stats.get("keys_count", 0),
            "hit_rate": cache_stats.get("hit_rate", "0%"),
            "memory": cache_stats.get("memory", {}),
        },
        "data_source": data_provider.get_status()
    }


@app.get("/api/cache/stats", tags=["系统"], summary="获取缓存统计")
def get_cache_stats():
    """获取 Redis 缓存统计信息"""
    return cache.get_stats()


@app.post("/api/cache/warmup", tags=["系统"], summary="手动触发缓存预热")
def trigger_warmup():
    """立即执行一次缓存预热"""
    # 非阻塞执行
    warmup_thread = threading.Thread(target=initial_warmup, daemon=True)
    warmup_thread.start()
    return {"status": "warmup_started", "message": "缓存预热已在后台启动"}


@app.delete("/api/cache/clear", tags=["系统"], summary="清除所有缓存")
def clear_cache():
    """清除所有 x-analytics 相关缓存"""
    deleted = cache.delete_pattern(f"{settings.CACHE_PREFIX}:*")
    return {"status": "ok", "deleted_keys": deleted}


@app.delete("/api/cache/clear/{pattern}", tags=["系统"], summary="清除指定模式缓存")
def clear_cache_pattern(pattern: str):
    """
    清除匹配指定模式的缓存
    
    示例: 
    - leaders: 清除领涨/领跌板块缓存
    - market: 清除所有市场相关缓存
    - sentiment: 清除情绪指标缓存
    """
    deleted = cache.delete_pattern(f"{settings.CACHE_PREFIX}:*{pattern}*")
    return {"status": "ok", "pattern": pattern, "deleted_keys": deleted}


@app.get("/api/scheduler/status", tags=["系统"], summary="获取调度器状态")
def get_scheduler_status():
    """获取后台调度器运行状态和任务列表"""
    return scheduler.get_status()


# -----------------------------------------------------------------------------
# 测试 API
# -----------------------------------------------------------------------------
@app.api_route("/api/test/callback", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], tags=["测试"], summary="回调测试接口")
async def test_callback(request: Request):
    """
    用于接收并打印外部系统的回调信息，支持各种 HTTP 请求方法
    """
    body = await request.body()
    try:
        body_json = await request.json()
    except Exception:
        body_json = None

    received_at = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")

    info = {
        "received_at": received_at,
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "body_raw": body.decode('utf-8', errors='ignore') if body else "",
        "body_json": body_json,
    }
    
    logger.info(f"========== 收到回调请求 [{received_at}] ==========")
    logger.info(f"Method: {info['method']} | URL: {info['url']}")
    logger.info(f"Headers: {info['headers']}")
    logger.info(f"Query Params: {info['query_params']}")
    if info['body_json']:
        logger.info(f"Body (JSON): {info['body_json']}")
    else:
        logger.info(f"Body (Raw): {info['body_raw']}")
    logger.info(f"===================================")
    
    return {"status": "success", "message": "Callback received", "received_data": info}


# -----------------------------------------------------------------------------
# 静态文件 (Web 仪表盘)
# -----------------------------------------------------------------------------
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


if __name__ == "__main__":
    # 本地调试启动
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
