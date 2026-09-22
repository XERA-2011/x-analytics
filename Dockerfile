# ========================================
# 阶段1: 构建依赖 (Builder)
# ========================================
FROM python:3.9-slim AS builder

WORKDIR /build

# 只复制依赖文件，利用 Docker 缓存
COPY requirements.txt .

# 升级 pip 并安装依赖 (抑制警告)
ENV PATH=/root/.local/bin:$PATH
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir --user -r requirements.txt \
    --no-warn-script-location \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# ========================================
# 阶段2: 最终运行镜像 (Runtime)
# ========================================
FROM python:3.9-slim

WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 从 builder 阶段复制已安装的依赖
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

# 设置 Python 路径
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 8080

# 启动服务
CMD ["python", "server.py"]
