# X-Data

全球宏观周期与金融数据看板，基于 [FastAPI](https://fastapi.tiangolo.com/) 与 [AKShare](https://github.com/akfamily/akshare) 构建。

- **线上访问**：[https://data.xerafun.com](https://data.xerafun.com)
- **备用访问**：[https://xera.dpdns.org/data/](https://xera.dpdns.org/data/)

> 本项目仅供技术交流与学习研究使用，不构成任何投资建议。

---

## 核心功能

- **Global 全球宏观**：亚洲市场（A股、港股、日韩台、国债利差、汇率、恐慌贪婪指数）、欧美市场（标普/纳指/道指/欧股、恐慌贪婪指数、美债收益率曲线）、全球主要股指横向比对
- **AI 产业周期**：六层 AI 产业链热力与估值联动（算力芯片/架构、存储与代工、数据中心基建、云巨头、软件与 Agent 应用、A股 AI 核心龙头）
- **Gold 贵金属与大宗**：现货黄金/白银、COMEX 金银、国内现货金银、金银比价追踪、央行黄金储备变动
- **QDII 境外基金透视**：高频折溢价测算、实时估算净值、季报重仓持仓穿透拆解（支持环比变动与前十大持仓占比）
- **Chart 周期图表与指数估值**：全球大类资产与核心股指历史走势对比、主要指数 PE/PB 估值分位点

---

## 架构

```mermaid
graph TD
    Client["用户端 (Web / 移动端)"] -->|"HTTPS (data.xerafun.com)"| Nginx["Nginx 网关反向代理"]
    Nginx -->|"转发至 :8080"| App["FastAPI + 原生 Web UI"]

    App --> Services["业务分析模块"]
    Scheduler["后台调度任务"] -->|"定时预热"| Services

    Services <--> Redis["Redis 内存热缓存"]
    Services <--> LocalCache["进程内缓存兜底"]
    Services <--> Snapshot["快照持久化层"]
    Snapshot --> Postgres["PostgreSQL 数据库"]
    Snapshot --> LocalJSON["本地 JSON 容灾备份"]

    Services -->|"直连请求"| Sources["公开行情与金融数据源"]
    Services -->|"防封中继"| Worker["Cloudflare Worker"] --> FundSources["需代理的基金数据源"]
```

- **四级高可用容灾**：Redis 内存热缓存（<5ms）➔ 进程内 LocalCache 兜底 ➔ PostgreSQL 数据快照（`DataSnapshot`，冷启动/重启秒开）➔ 容器本地 JSON 文件降级。
- **双通道采集与安全中继**：高频行情直连国内网络；深层基金配置通过 Cloudflare Worker 边缘中继（防封锁且阻断直连回退，保护源站 IP）。

---

## 本地开发

### 依赖安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 环境变量 (`.env.local`)

首次使用可从示例复制后填写：

```bash
cp .env.example .env.local
```

```env
REDIS_URL="redis://:password@127.0.0.1:6379/0"
DATABASE_URL="postgres://postgres:password@127.0.0.1:5432/xanalytics"
DEPLOY_SSH_ALIAS="a1"

# 本地 Docker Compose 专用环境变量（配置独立运行的 PostgreSQL/Redis 容器）
REDIS_PASSWORD="password"
POSTGRES_PASSWORD="password"
POSTGRES_DB="xanalytics"

CF_WORKER_PROXY_URL="https://your-worker-proxy.domain"
CF_WORKER_SECRET_KEY="your-secret-key"
```

### 运行

```bash
python server.py

# 或使用 Docker
docker compose --env-file .env.local up -d --build
```

Compose 会启动独立的 Redis 和 PostgreSQL 容器，应用通过容器网络连接它们；不会把 `.env.local` 中供本机 Python 使用的 `DATABASE_URL`（通常指向本机 SSH 隧道）传给容器。Worker 配置会从该文件传入应用容器。若不需要 Worker，可留空对应变量。以上密码仅为本地开发示例，不应复用于生产环境。

- 仪表盘：`http://localhost:8080/`
- API 文档：`http://localhost:8080/docs`（生产环境默认关闭，通过 `DOCS_ENABLED=true` 按需开启）

---

## 部署与生产运维

本项目专注于业务逻辑与镜像构建。生产部署与基础设施编排由专用运维仓库收敛：
- **发布入口**：统一使用 [`x-actions/deploy.sh`](https://github.com/xerafun/x-actions) 执行本地免密原生双机构建与发布（甲骨文 A1 与阿里云 ECS）。
- **生产访问**：[https://data.xerafun.com](https://data.xerafun.com)（同时支持 `https://xera.dpdns.org/data/` 子路径）。
