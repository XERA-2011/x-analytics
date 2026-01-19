# x-analytics

个人 A 股数据分析平台，基于 [AKShare](https://github.com/akfamily/akshare) 构建。

## ✨ 特性

- **Redis 缓存加速**: 毫秒级响应，支持 **Stale-While-Revalidate** 策略，数据永不过期（视觉上）
- **抗雪崩设计**: 分布式锁机制，防止缓存击穿导致的数据库压力
- **智能调度器**: 自动识别 A 股交易日与交易时段，动态调整刷新频率
- **数据对齐**: 交易日 09:25 自动执行开盘前数据预热
- **RESTful API**: FastAPI 构建，自带 Swagger 文档
- **Docker 部署**: 一键启动，包含 Redis 服务

## 📡 API 接口

完整接口文档：`/analytics/docs` (Swagger UI)

### 业务 API

| 接口 | 说明 | 缓存 TTL |
|------|------|----------|
| `GET /api/market/overview` | 市场概览(指数/成交/涨跌分布) | 40min (+60min Stale) |
| `GET /api/market/sector-top` | 领涨行业 | 60min (+120min Stale) |
| `GET /api/market/sector-bottom` | 领跌行业 | 60min (+120min Stale) |
| `GET /api/sentiment/fear-greed` | 恐慌贪婪指数 | 5min (+10min Stale) |

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

| 数据 | 交易时段 (09:30-15:00) | 非交易时段 | 备注 |
|------|-----------------------|------------|------|
| 市场概览 | 每 30 分钟 | 每 4 小时 | 9:25 强制刷新 |
| 恐慌贪婪指数 | 每 5 分钟 | 每 4 小时 | |
| 板块排行 | 每 60 分钟 | 每 4 小时 | |
| 基金排行 | 每 12 小时 | 每 12 小时 | |

> **注**: 系统会自动判断交易日，并在每个交易日 **09:25** 执行一次全量预热，确保开盘数据新鲜。
