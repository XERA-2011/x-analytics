import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from analytics.sentiment import SentimentAnalysis
import os

# 创建 FastAPI 应用
# root_path 用于支持通过反向代理访问时 Swagger UI 正常工作
app = FastAPI(
    title="X-Analytics API",
    description="A 股数据分析服务，基于 AKShare 构建",
    version="1.0.0",
    root_path="/analytics"
)

# 配置 CORS (允许跨域)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# API 接口
# -----------------------------------------------------------------------------
@app.get("/api/sentiment/fear-greed", tags=["情绪分析"], summary="获取市场恐慌贪婪指数")
def get_fear_greed_index(symbol: str = "sh000001", days: int = 14):
    """
    计算基于 RSI 和 Bias 的自定义恐慌贪婪指数。
    - 0-20: 极度恐慌 (底部特征)
    - 80-100: 极度贪婪 (顶部风险)
    """
    return SentimentAnalysis.calculate_fear_greed_custom(symbol=symbol, days=days)

@app.get("/api/sentiment/qvix", tags=["情绪分析"], summary="获取中国波指(QVIX)")
def get_qvix_indices():
    """获取主要 ETF 期权的波动率指数 (QVIX)"""
    return SentimentAnalysis.get_qvix_indices()

@app.get("/api/sentiment/north-flow", tags=["情绪分析"], summary="获取北向资金情绪")
def get_north_flow():
    """获取北向资金(聪明钱)的实时流向与净买入额"""
    return SentimentAnalysis.get_north_funds_sentiment()

@app.get("/api/health", tags=["系统"], summary="服务健康检查")
def health_check():
    return {"status": "ok", "service": "x-analytics", "version": "1.0.0"}


# -----------------------------------------------------------------------------
# 静态文件 (Web 仪表盘)
# -----------------------------------------------------------------------------
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


if __name__ == "__main__":
    # 本地调试启动
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
