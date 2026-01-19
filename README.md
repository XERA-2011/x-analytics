# x-analytics

个人 A 股数据分析平台，基于 [AKShare](https://github.com/akfamily/akshare) 构建。

## ✨ 特性

- **Redis 缓存加速**: 毫秒级 API 响应，交易时段智能预热
- **后台调度器**: APScheduler 定时刷新缓存，交易时段高频、非交易时段低频
- **RESTful API**: FastAPI 构建，自带 Swagger 文档
- **Docker 部署**: 一键启动，包含 Redis 服务

## 📡 API 接口

完整接口文档：`/analytics/docs` (Swagger UI)

### 业务 API

| 接口 | 说明 | 缓存 TTL |
|------|------|----------|
| `GET /api/market/overview` | 市场概览(指数/成交/涨跌分布) | 60s |
| `GET /api/market/sector-top` | 领涨行业 | 180s |
| `GET /api/market/sector-bottom` | 领跌行业 | 180s |
| `GET /api/sentiment/fear-greed` | 恐慌贪婪指数 | 300s |

### 系统 API

| 接口 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 |
| `GET /api/cache/stats` | 缓存统计 |
| `POST /api/cache/warmup` | 手动触发预热 |
| `DELETE /api/cache/clear` | 清除缓存 |
| `GET /api/scheduler/status` | 调度器状态 |

## 🛠️ 本地开发

```bash
# 一键启动 (Redis + App)
docker-compose up -d --build

# 查看日志
docker-compose logs -f x-analytics

# 访问
open http://localhost:8080/          # Web 仪表盘
open http://localhost:8080/docs      # API 文档

# 停止
docker-compose down
```

### 不使用 Docker 开发

```bash
# 1. 启动 Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 2. 安装依赖 & 启动
pip install -r requirements.txt
python server.py
```

## 📁 项目结构

```
x-analytics/
├── server.py               # FastAPI 入口
├── requirements.txt        # Python 依赖
├── Dockerfile              # 容器构建 (多阶段)
├── docker-compose.yml      # 多服务编排 (Redis + App)
├── analytics/              # 核心分析模块
│   ├── cache.py            # Redis 缓存封装
│   ├── scheduler.py        # APScheduler 后台调度
│   ├── market.py           # 市场分析
│   ├── sentiment.py        # 情绪分析
│   ├── stock.py            # 个股分析
│   ├── index.py            # 指数分析
│   ├── fund.py             # 基金分析
│   └── technical.py        # 技术指标
└── web/                    # Web 仪表盘
```

## 🔧 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接地址 |
| `TZ` | `Asia/Shanghai` | 时区 |

## 📊 缓存预热策略

| 数据 | 交易时段 (9:30-15:00) | 非交易时段 |
|------|----------------------|------------|
| 市场概览 | 每 1 分钟 | 每 30 分钟 |
| 恐慌贪婪指数 | 每 5 分钟 | 每 60 分钟 |
| 板块排行 | 每 3 分钟 | 每 60 分钟 |
