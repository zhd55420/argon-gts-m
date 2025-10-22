#!/bin/bash

# 设置环境变量
export SECRET_KEY=${SECRET_KEY:-'S#perS3crEt_1122'}
export DEBUG=${DEBUG:-'False'}

# 等待数据库就绪（如果是外部数据库）
# sleep 10

# 执行数据库迁移
echo "Applying database migrations..."
python manage.py migrate --noinput

# 确保静态文件已收集（双重保险）
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 设置 django-crontab
echo "Setting up cron jobs..."
python manage.py crontab add

# 启动 cron 服务
echo "Starting cron service..."
service cron start

# 启动 Gunicorn（基于你的 systemd 配置）
echo "Starting Gunicorn..."
exec gunicorn --access-logfile - --workers 3 --bind 0.0.0.0:8000 --timeout 300 core.wsgi:application
