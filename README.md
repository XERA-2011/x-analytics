# X-Analytics

金融数据分析平台，基于 [FastAPI](https://fastapi.tiangolo.com/) 与 [AKShare](https://github.com/akfamily/akshare) 构建。

> 本项目仅供技术交流与学习研究使用，不构成任何投资建议。

---

## 架构

```mermaid
graph TD
    Client["用户端"] -->|"HTTPS /analytics"| Nginx["Nginx 反向代理"]
    Nginx -->|"转发至 :8080"| App["FastAPI + 静态 Web UI"]

    App --> Services["业务模块"]
    Scheduler["后台调度"] -->|"定时预热"| Services

    Services <--> Redis["Redis 热缓存"]
    Services <--> LocalCache["进程内缓存兜底"]
    Services <--> Snapshot["快照存储层"]
    Snapshot --> Postgres["PostgreSQL"]
    Snapshot --> LocalJSON["本地 JSON 容灾备份"]

    Services -->|"直连请求"| Sources["公开行情与金融数据源"]
    Services -->|"防封中继"| Worker["Cloudflare Worker"] --> FundSources["需代理的基金数据源"]
```

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
- API 文档：`http://localhost:8080/docs`
