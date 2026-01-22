# x-analytics

个人 数据分析平台，基于 [AKShare](https://github.com/akfamily/akshare) 构建。

## 📡 API 接口

完整接口文档：`/analytics/docs` (Swagger UI)

## 🛠️ 本地开发

```bash
# 一键启动 (Redis + App)
docker-compose up -d --build

# 重启
docker-compose restart x-analytics

# 清空整个 Redis 数据库
docker exec x-analytics-redis redis-cli FLUSHDB

# 查看日志
docker-compose logs -f x-analytics

# 访问
open http://localhost:8080/          # Web 仪表盘
open http://localhost:8080/docs      # API 文档

# 停止并清空缓存
docker-compose down -v
```
