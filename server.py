import uvicorn
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from analytics.sentiment import SentimentAnalysis
from analytics.market import MarketAnalysis
from analytics.cache import cache
from analytics.scheduler import scheduler, setup_default_warmup_jobs, initial_warmup
import os


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
        setup_default_warmup_jobs()
        scheduler.start()
    else:
        print("⚠️ Redis 未连接，将以无缓存模式运行")

    yield

    # 关闭时
    print("🛑 x-analytics 服务关闭中...")
    scheduler.shutdown(wait=False)


# 创建 FastAPI 应用
# root_path 用于支持通过反向代理访问时 Swagger UI 正常工作
app = FastAPI(
    title="x-analytics API",
    description="A 股数据分析服务，基于 AKShare 构建，支持 Redis 缓存加速",
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
# 业务 API 接口
# -----------------------------------------------------------------------------
@app.get("/api/sentiment/fear-greed", tags=["情绪分析"], summary="获取市场恐慌贪婪指数")
def get_fear_greed_index(symbol: str = "sh000001", days: int = 14):
    """自定义恐慌贪婪指数（支持缓存）"""
    return SentimentAnalysis.calculate_fear_greed_custom(symbol=symbol, days=days)


@app.get(
    "/api/market/overview",
    tags=["市场分析"],
    summary="获取市场概览(指数/成交/涨跌分布)",
)
def get_market_overview():
    """获取主要指数行情、市场广度和两市成交额（支持缓存）"""
    return MarketAnalysis.get_market_overview_v2()


@app.get("/api/market/sector-top", tags=["市场分析"], summary="获取领涨行业")
def get_sector_top(n: int = 5):
    """获取领涨行业板块 Top N（支持缓存）"""
    return MarketAnalysis.get_sector_top(n=n)


@app.get("/api/market/sector-bottom", tags=["市场分析"], summary="获取领跌行业")
def get_sector_bottom(n: int = 5):
    """获取领跌行业板块 Top N（支持缓存）"""
    return MarketAnalysis.get_sector_bottom(n=n)


# -----------------------------------------------------------------------------
# 指数 & 基金 & 个股 API (新增)
# -----------------------------------------------------------------------------
@app.get("/api/index/compare", tags=["指数分析"], summary="获取主要指数对比")
def get_index_compare():
    """获取主要指数对比 (上证/深证/创业板等)"""
    from analytics.index import IndexAnalysis

    # 暂时不加缓存装饰器，因为 compare_indices 内部涉及多个网络请求，如果要缓存建议在内部加
    # 暂时不加缓存装饰器，因为 compare_indices 内部涉及多个网络请求，如果要缓存建议在内部加
    data = IndexAnalysis.compare_indices()
    return data


@app.get("/api/fund/top", tags=["基金分析"], summary="获取基金涨幅榜")
def get_fund_top(n: int = 10):
    """获取场外基金日涨幅榜 Top N"""
    from analytics.fund import FundAnalysis

    # 同样由内部或 Redis 缓存控制
    # 同样由内部或 Redis 缓存控制
    data = FundAnalysis.get_top_funds(top_n=n)
    if not data:
        return []

    # 已经是 list[dict]
    return [
        {
            "基金代码": item["基金代码"],
            "基金简称": item["基金简称"],
            "日增长率": item["日增长率"],
        }
        for item in data
    ]


@app.get("/api/stock/search", tags=["个股分析"], summary="搜索个股")
def search_stock(keyword: str):
    """搜索 A 股股票 (代码或名称)"""
    from analytics.stock import StockAnalysis

    return StockAnalysis.search(keyword=keyword)


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
    from analytics.scheduler import initial_warmup

    # 非阻塞执行
    warmup_thread = threading.Thread(target=initial_warmup, daemon=True)
    warmup_thread.start()

    return {"status": "warmup_started", "message": "缓存预热已在后台启动"}


@app.delete("/api/cache/clear", tags=["系统"], summary="清除所有缓存")
def clear_cache():
    """清除所有 x-analytics 相关缓存"""
    deleted = cache.delete_pattern("xanalytics:*")
    return {"status": "ok", "deleted_keys": deleted}


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
