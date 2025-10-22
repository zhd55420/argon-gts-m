# 使用 Python 3.9 官方镜像
FROM python:3.9-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBUG=False

# 安装系统依赖（包括 cron 用于定时任务）
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录和日志目录结构
RUN mkdir -p /app
RUN mkdir -p /app/logs/hostname_updater
RUN mkdir -p /app/logs/myapp
RUN mkdir -p /app/logs/stream
RUN mkdir -p /app/logs/influxdb_query
RUN mkdir -p /app/logs/resource_group
RUN mkdir -p /app/logs/zabbix

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 创建启动脚本
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 使用启动脚本
CMD ["./entrypoint.sh"]
