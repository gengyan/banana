#!/bin/sh
set -e

# Cloud Run 会设置 PORT 环境变量，默认为 8080
PORT=${PORT:-8080}
export PORT

# 使用 envsubst 替换 nginx 配置模板中的 PORT 变量
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# 启动 Nginx
exec nginx -g "daemon off;"

