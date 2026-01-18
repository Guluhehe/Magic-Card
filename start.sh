#!/bin/bash
# Render 启动脚本

# 设置环境变量（如果需要）
export PORT=${PORT:-5000}

# 启动 gunicorn
exec gunicorn server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
