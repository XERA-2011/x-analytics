# X-Analytics

金融数据分析平台，基于 [FastAPI](https://fastapi.tiangolo.com/) 与 [AKShare](https://github.com/akfamily/akshare) 构建。

> 本项目仅供技术交流与学习研究使用，不构成任何投资建议。

---

## 架构

```mermaid
graph TD
    Client["用户端 (Web / 移动端)"] -->|"HTTPS /analytics"| Nginx["Nginx 反向代理 (x-actions)"]
    Nginx -->|"转发至 :8080"| App["FastAPI + 静态 Web UI"]

    App --> Services["业务模块 (数据获取与计算)"]
    Scheduler["后台调度 (Scheduler)"] -->|"定时预热"| Services

    Services <--> Redis["Redis 热缓存"]
    Services <--> Snapshot["PostgreSQL 快照 (含本地文件兜底)"]

    Services -->|"直连请求"| Sources["公开行情与金融数据源"]
    Services -->|"防封中继"| Worker["Cloudflare Worker (x-worker)"] --> FundSources["需代理的基金数据源"]
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

```env
REDIS_URL="redis://:password@127.0.0.1:6379/0"
DATABASE_URL="postgres://postgres:password@127.0.0.1:5432/xanalytics"
DEPLOY_SSH_ALIAS="a1"

CF_WORKER_PROXY_URL="https://your-worker-proxy.domain"
CF_WORKER_SECRET_KEY="your-secret-key"
```

### 运行

```bash
python server.py

# 或使用 Docker
docker compose up -d --build
```

- 仪表盘：`http://localhost:8080/`
- API 文档：`http://localhost:8080/docs`
