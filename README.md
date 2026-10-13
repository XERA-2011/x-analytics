# X-Analytics

全球科技与 AI 产业周期终端 / 金融数据分析平台，基于 [FastAPI](https://fastapi.tiangolo.com/) 与 [AKShare](https://github.com/akfamily/akshare) 构建。

---

## 🏗️ 全局项目架构

```mermaid
graph TD
    Client["📱 用户端 (Web / 移动端)"] -->|"端口访问 :2012"| App["⚡ FastAPI 后端 & Web 服务 (:8080)"]
    
    subgraph CoreApp ["核心系统应用"]
        App -->|静态资源| WebUI["🖥️ Web 仪表盘 (原生 JS/CSS)"]
        App -->|"① 优先读取热缓存 (<5ms)"| Redis["🔴 Redis 缓存 (内存热数据)"]
        App -->|"② 冷启动/缓存失效 0ms 兜底"| Postgres["🐘 Postgres (DataSnapshot 快照持久化)"]
        App -->|历史趋势归档| PostgresHist["🐘 Postgres (Sentiment/Signal 历史表)"]
        
        Scheduler["⏰ Task Scheduler (后台调度 & 定时保鲜)"] -->|双写缓存与快照| Redis
        Scheduler -->|双写缓存与快照| Postgres
        
        Scheduler -->|公开行情直连高速抓取| DomesticAPIs["🌐 公开市场行情数据源 (行情/净值/宏观)"]
        Scheduler -.->|深层页面防封中继| ProxyWorker["⚡ 边缘中继代理 (Serverless Worker)"]
        App -.->|穿透持仓按需中继| ProxyWorker
    end

    ProxyWorker -->|"安全发包 (资产配置/费率/持仓)"| DeepFinancialAPIs["📄 基金与财报深层数据源"]
```

系统核心架构包含如下关键模块：
- **双层高可用持久化体系**：
  - **一级 Redis 热缓存**：高频行情与指标秒级/分钟级在内存极速响应；
  - **二级 PostgreSQL 数据快照 (`DataSnapshot`)**：所有日线指标、全球大盘对比与估值数据持久化落盘。即使 Redis 冷启动、容器销毁重建，依然实现 0ms 瞬间秒开兜底，并由后台异步静默刷新，彻底消除前端卡死；
  - **三级本地 JSON 备份**：容器本地文件系统快照双写，保障极端无数据库场景下的平滑降级。
- **核心应用服务**：包含 FastAPI 后端服务、前端 Web 仪表盘、后台 Task Scheduler 智能调度器。
- **边缘代理中继 (Serverless Worker)**：通用的 HTTP API 代理中继，配备请求密钥鉴权、请求头清洗与防盗链伪造，保障服务器源站 IP 安全。
- **双通道数据采集**：
  - **主流高频数据**：A股/港股/美股实时行情、官方净值、黄金价格等走国内直连网络，保障极低延迟（<100ms）；
  - **深层低频数据**：持仓穿透、资产配置比例与综合费率等深层 HTML 页面，通过边缘中继代理防封抓取，杜绝源站 IP 风险。

---

## 📊 五大核心模块

1. **全球市场 (Global)**：亚洲市场（沪深/港股动能、估值水位）、美股及西方市场动能与原生指数对标、国债收益率与利差监控。
2. **图表中心 (Chart)**：全球主要国家/地区主要指数多周期走势对比（支持中国台湾加权、纳指100、沪深300等）、多周期收益率看板、核心指数估值温度计（PE-TTM 历史百分位）。
3. **AI 产业链 (AI)**：全球 7 层产业链结构监测、中美科技竞争力对比、泡沫风险温度计。
4. **黄金分析 (Gold)**：国内实时金价、国际金价（伦敦金/COMEX）、溢价率监测、黄金 ETF 跟踪与套利计算模型。
5. **QDII 基金 (QDII)**：主动型 QDII、纳斯达克100 & 标普500 基金对标、季报真实资产配置与重仓穿透、综合费率监测。

---

## ⚖️ 合规与术语规范 (Compliance & Terminology)

- **国家与地区表述**：涉跨国、跨市场及包含中国港澳台地区指数对比时，页面文案及说明中**严格统一使用「国家/地区」**，严禁使用「多国/各国」；
- **台湾地区命名**：指数清单与对比图表中，台湾指数**严格统一命名为「中国台湾加权」**（TWII）。

---

## 📡 API 接口

完整 Swagger UI 接口文档：`/docs`（本地开发默认开启；生产环境为最小化攻击面默认关闭，可通过 `DOCS_ENABLED=true` 按需开启）

公开核心接口：
- 全球市场行情: `/market-asia/` / `/market-western/`
- 全球主要国家/地区主要指数走势对比: `/chart/indices-comparison`
- 指数估值温度计: `/index-valuation/valuation/{index_code}`
- AI 产业周期分析: `/ai/overview`
- 黄金与贵金属数据: `/metals/` / `/gold/`
- QDII 基金持仓穿透: `/qdii/funds` / `/qdii/holdings/{code}`
- 宏观利率与基准: `/market-asia/lpr`

服务启动后直接访问根路径或者对应端口即可查看仪表盘与数据接口。

---

## 🛠️ 本地开发与运行

### 方式一：Python 源码启动 (推荐开发使用)

#### 1. 环境准备 (虚拟环境)
```bash
# 创建虚拟环境
python -m venv .venv

# 激活环境 (Mac/Linux)
source .venv/bin/activate
# Windows (PowerShell):
# .\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置环境变量
在项目根目录新建 `.env.local` 文件，填入配置：

```env
# 本地通过自动 SSH 隧道直接连通云端数据库与缓存 (安全免公网暴露端口)
REDIS_URL="redis://:Redis密码@127.0.0.1:6379/0"
DATABASE_URL="postgres://postgres:数据库密码@127.0.0.1:5432/xanalytics"

# 本地直连云端数据库安全隧道别名 (对应 ~/.ssh/config 中的 Host，如 a1)
DEPLOY_SSH_ALIAS="a1"

# Cloudflare Worker 中继代理配置 (用于数据抓取防封)
CF_WORKER_PROXY_URL="https://your-worker-proxy.domain"
CF_WORKER_SECRET_KEY="your-secret-key"
```

#### 3. 启动服务
```bash
# 启动本地服务 (自动建立数据库 SSH 安全隧道，进程退出时自动销毁)
python server.py

# 亦可使用独立脚本随时手动管理安全隧道
./tunnel.sh status   # 查看隧道状态
./tunnel.sh start    # 手动启动隧道
./tunnel.sh stop     # 手动关闭隧道
```

---

### 方式二：Docker 启动

```bash
# 一键启动 (自动构建镜像并运行)
docker compose up -d --build

# 查看日志
docker compose logs -f xanalytics
```

---

## 🌐 访问地址

- **本地开发直接访问**:
  - Web 仪表盘: `http://localhost:8080/`
  - API 文档 (Swagger): `http://localhost:8080/docs`
- **生产环境统一 HTTPS 访问 (推荐)**:
  - Web 仪表盘与 API: `https://xera.dpdns.org/analytics/`
- **生产环境直连端口访问**:
  - Web 仪表盘与 API: `http://141.148.178.120:2012/` (或阿里云 `:2012/`)

---

## 🔒 代理安全与熔断机制

当配置了环境变量 `CF_WORKER_PROXY_URL` 时，系统将**强制使用指定的 Cloudflare Worker 中继代理**发起外网 HTTP 抓取。若代理未配置或中继失败，系统将**严格阻断发包（绝不降级直连）**，杜绝服务器源站 IP 被封锁的风险。

---

## 🧹 常用运维命令

```bash
# 重启容器服务 (更新 .env 环境变量或生效改动)
docker compose restart xanalytics

# 平滑重新构建并更新运行容器
docker compose up -d --build xanalytics

# 清空 Redis 所有缓存 (强制刷新全局数据)
python -c "import redis, os; from dotenv import load_dotenv; load_dotenv('.env.local'); r = redis.from_url(os.getenv('REDIS_URL')); r.flushdb(); print('✅ Redis 缓存已清空')"

# 重置历史数据表
python scripts/reset_sentiment_history.py
```

---

## 🚀 持续集成与生产部署

本项目专注于核心量化业务逻辑与 Docker 镜像构建，不直接存放任何服务器基础设施配置或部署密钥：

1. **多架构镜像构建**：代码推送至 `main` 分支后，GitHub Actions 自动构建跨架构 Docker 镜像（同时支持 `linux/amd64` 与 `linux/arm64`），并发布至 GHCR 与阿里云 ACR。
2. **生产部署入口**：线上生产部署统一在独立私有运维仓库 `x-actions` 中执行（通过本地免密直连进行多目标滚动发布与健康检查）。


