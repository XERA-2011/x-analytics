# x-analytics

个人 数据分析平台，基于 [AKShare](https://github.com/akfamily/akshare) 构建。

## 📡 API 接口

完整接口文档：`/analytics/docs` (Swagger UI)

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
# 创建虚拟环境
python3 -m venv .venv

# 激活环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
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
- Web 仪表盘: http://localhost:8080/
- API 文档: http://localhost:8080/docs
