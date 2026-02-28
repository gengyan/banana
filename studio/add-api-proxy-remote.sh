#!/bin/bash
# 在服务器上添加 /api 反向代理到 47.82.167.164 站点
# 通过宝塔 extension 目录注入，无需直接编辑主配置

set -e
EXT_DIR="/www/server/panel/vhost/nginx/extension/47.82.167.164"
API_CONF="$EXT_DIR/api_proxy.conf"

mkdir -p "$EXT_DIR"

cat > "$API_CONF" << 'NGINX_EOF'
    # API 反向代理（studio 后端）
    location /api/ {
        client_max_body_size 50M;
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
NGINX_EOF

echo "已创建 $API_CONF"
nginx -t && nginx -s reload
echo "Nginx 重载成功"
