import uvicorn
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from analytics.core import cache, scheduler, settings
from analytics.core.scheduler import setup_default_jobs, initial_warmup
from analytics.api.market_cn import router as cn_market_router
from analytics.api.metals import router as metals_router
from analytics.api.market_us import router as us_market_router
from analytics.core.patch import apply_patches
import os

# 应用 API 伪装补丁 (在最早的时机)
apply_patches()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 x-analytics 服务启动中...")

    # 检查 Redis 连接
    if cache.connected:
        print(f"✅ Redis 已连接: {cache.redis_url}")

        # 启动后台初始预热（非阻塞）
        warmup_thread = threading.Thread(target=initial_warmup, daemon=True)
        warmup_thread.start()

        # 设置并启动调度器
        setup_default_jobs()
        scheduler.start()
    else:
        print("⚠️ Redis 未连接，将以无缓存模式运行")

    yield

    # 关闭时
    print("🛑 x-analytics 服务关闭中...")
    scheduler.shutdown(wait=False)


# 创建 FastAPI 应用
app = FastAPI(
    title="x-analytics API",
    description="三大板块金融数据分析服务：沪港深市场、美股市场、有色金属",
    version="2.0.0",
    root_path="/analytics",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# 注册路由模块
# -----------------------------------------------------------------------------
app.include_router(cn_market_router)
app.include_router(metals_router)
app.include_router(us_market_router)


# -----------------------------------------------------------------------------
# 兼容性API接口 (保持向后兼容)
# -----------------------------------------------------------------------------
@app.get(
    "/api/sentiment/fear-greed", tags=["兼容性接口"], summary="获取市场恐慌贪婪指数"
)
def get_fear_greed_index_compat(symbol: str = "sh000001", days: int = 14):
    """兼容旧版本的恐慌贪婪指数接口"""
    from analytics.modules.market_cn import CNFearGreedIndex

    return CNFearGreedIndex.calculate(symbol=symbol, days=days)


@app.get("/api/commodity/gold-silver", tags=["兼容性接口"], summary="获取金银比及价格")
def get_gold_silver_ratio_compat():
    """兼容旧版本的金银比接口"""
    from analytics.modules.metals import GoldSilverAnalysis

    return GoldSilverAnalysis.get_gold_silver_ratio()


# -----------------------------------------------------------------------------
# 系统管理 API
# -----------------------------------------------------------------------------
@app.get("/api/health", tags=["系统"], summary="服务健康检查")
def health_check():
    return {
        "status": "ok",
        "service": "x-analytics",
        "version": "2.0.0",
        "cache": {
            "connected": cache.connected,
            "url": cache.redis_url if cache.connected else None,
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
