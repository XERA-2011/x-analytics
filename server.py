import uvicorn
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from analytics.core import cache, scheduler, settings
from analytics.core.scheduler import setup_default_jobs, initial_warmup
from analytics.api import market_cn, metals, market_us, market_hk
from analytics.core.patch import apply_patches
from analytics.core.security import SecurityMiddleware
from analytics.core.logger import logger
import os

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
    allow_headers=[],  # 仅允许必要的自定义头
)

# -----------------------------------------------------------------------------
# 注册路由模块
# -----------------------------------------------------------------------------
app.include_router(market_cn.router, prefix="/market-cn", tags=["China Market"])
app.include_router(market_us.router, prefix="/market-us", tags=["US Market"])
app.include_router(metals.router, prefix="/metals", tags=["Precious Metals"])
app.include_router(market_hk.router, prefix="/market-hk", tags=["HK Market"])




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
    
    return {
        "status": "ok",
        "service": "x-analytics",
        "version": settings.VERSION,
        "cache": {
            "connected": cache.connected,
            "host": redis_host,
        },
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
# 静态文件 (Web 仪表盘)
# -----------------------------------------------------------------------------
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


if __name__ == "__main__":
    # 本地调试启动
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
