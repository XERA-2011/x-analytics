# X-Analytics

全球科技与 AI 产业周期终端 / 金融数据中台，基于 [FastAPI](https://fastapi.tiangolo.com/) 与 [AKShare](https://github.com/akfamily/akshare) 构建。

---

## 架构与数据流

```mermaid
graph TD
    Client["用户端 (Web / 移动端)"] -->|"HTTPS /analytics"| App["FastAPI 后端 (:8080)"]
    
    subgraph CoreApp ["核心系统"]
        App --> WebUI["原生 Web 仪表盘"]
        App -->|"① 内存热缓存 (<5ms)"| Redis["Redis (内存热缓存)"]
        App -->|"② 快照兜底"| Postgres["PostgreSQL (DataSnapshot)"]
        
        Scheduler["Task Scheduler (后台智能调度)"] --> Redis & Postgres
        Scheduler -->|"国内行情直连 (<100ms)"| PublicAPIs["公开市场行情 (A/H/US/金银)"]
        Scheduler -.->|"深层持仓防封代理"| ProxyWorker["边缘中继 (Cloudflare Worker)"]
    end

    ProxyWorker -->|"资产配置/费率/持仓"| FundAPIs["基金深层数据"]
```

- **三级高可用持久化**：Redis 内存热缓存 ➔ PostgreSQL 数据快照（`DataSnapshot`，冷启动/重启秒开兜底）➔ 容器本地 JSON 文件降级。
- **双通道采集与安全中继**：高频行情直连国内网络；深层基金配置通过边缘 Worker 中继（防封锁且**严格阻断直连回退**，保护源站 IP）。

---

## 本地开发

### 1. 环境准备
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 环境变量 (`.env.local`)
```env
# 通过本地 SSH 隧道连通云端数据库 (免公网暴露端口)
REDIS_URL="redis://:Redis密码@127.0.0.1:6379/0"
DATABASE_URL="postgres://postgres:数据库密码@127.0.0.1:5432/xanalytics"
DEPLOY_SSH_ALIAS="a1"

# 边缘代理配置 (数据抓取防封)
CF_WORKER_PROXY_URL="https://your-worker-proxy.domain"
CF_WORKER_SECRET_KEY="your-secret-key"
```

### 3. 启动服务
```bash
# 启动本地开发服务 (自动拉起数据库安全隧道，退出时自动销毁)
python server.py

# 或使用 Docker 启动
docker compose up -d --build
```

- **本地仪表盘**：`http://localhost:8080/`
- **Swagger API 文档**：`http://localhost:8080/docs`（生产环境默认关闭，通过 `DOCS_ENABLED=true` 按需开启）

---

## 部署与生产运维

本项目专注于业务逻辑与镜像构建。生产部署与基础设施编排由专用运维仓库收敛：
- **发布入口**：统一使用 [`x-actions/deploy.sh`](../x-actions/deploy.sh) 执行本地原生双机构建与发布：
  ```bash
  ./deploy.sh --target all        # 双机滚动增量发布 (a1 + aliyun)
  ./deploy.sh --rollback <tag>    # 秒级版本回滚
  ```
- **生产访问**：`https://xera.dpdns.org/analytics/`
