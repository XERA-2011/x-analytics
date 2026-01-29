# x-analytics

个人 数据分析平台，基于 [AKShare](https://github.com/akfamily/akshare) 构建。

## 📡 API 接口

完整接口文档：`/analytics/docs` (Swagger UI)

## 🛠️ 本地开发

```bash
# 1. 配置环境变量 (在本地终端或 .env 文件)
export REDIS_URL="redis://:YourStrongRedisPassword@<YourServerIP>:6379/0"
# 如果使用远程 Postgres:
export DATABASE_URL="postgres://postgres:YourStrongPostgresPassword@<YourServerIP>:5432/xanalytics"

# 2. 一键启动 (Redis + App)
docker compose up -d --build

# 3. 本地开发直连远程
python server.py
# 或
uvicorn server:app --reload
```
