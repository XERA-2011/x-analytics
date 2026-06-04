# x-analytics

个人 数据分析平台，基于 [AKShare](https://github.com/akfamily/akshare) 构建。

## 📡 API 接口

完整接口文档：`/analytics/docs` (Swagger UI)

> 生产环境通常搭配 [`x-actions`](../x-actions) 使用，由 Nginx 将 `/analytics/`
> 反向代理到 `xanalytics:8080/`，并剥离 `/analytics` 前缀后转发给本服务。
> 本地直接运行本项目时，可使用根路径访问。

## 🛠️ 本地开发

你可以根据需求选择以下两种方式之一：

### 方式一：Docker 启动 (仅运行)
适合：**不想安装 Python 环境**，只想快速运行项目看效果。
>Docker 容器内已包含所有依赖，无需本地配置。

```bash
# 一键启动 (自动构建镜像并运行)
docker compose up -d --build

# 查看日志
docker compose logs -f xanalytics
```

### 方式二：Python 源码启动 (推荐开发使用)
适合：**开发调试**，需要 IDE (VS Code) 的智能提示和自动补全。

#### 1. 环境准备 (虚拟环境)
```bash
# 创建虚拟环境 (Windows 使用 python, Mac/Linux 使用 python3)
python -m venv .venv

# 激活环境
# Mac/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 退出环境
deactivate
```

#### 2. 配置环境变量
在项目根目录新建 `.env.local` 文件，填入服务器信息（避免密码泄露）：
```env
REDIS_URL="redis://:Redis密码@<YourServerIP>:6379/0"
DATABASE_URL="postgres://postgres:数据库密码@<YourServerIP>:5432/xanalytics"
```

#### 3. 启动服务
```bash
python server.py
# 或
uvicorn server:app --reload
```

## 🌐 访问地址
- 本地直接访问:
  - Web 仪表盘: http://localhost:8080/
  - API 文档: http://localhost:8080/docs
- 通过 x-actions 网关访问:
  - Web 仪表盘: http://localhost/analytics/
  - API 文档: http://localhost/analytics/docs

## 🧹 常用运维命令
```bash
# 清空 Redis 所有缓存 (强制刷新数据)
python -c "import redis, os; from dotenv import load_dotenv; load_dotenv('.env.local'); r = redis.from_url(os.getenv('REDIS_URL')); r.flushdb(); print('✅ Redis 缓存已清空')"

# 丢弃并重建数据库记录表 (当升级增加列如 indicator_type 导致报错时使用)
# 注意：这会清除全部历史数据！
python scripts/reset_sentiment_history.py
```
