#!/bin/bash
# 完成阿里云后端部署 - 手动加载镜像并启动容器

set -e

SERVER="root@47.82.167.164"
TARGET_DIR="/var/www/gj-server"
PORT=8080

echo "==========================================" 
echo "🔄 完成 studio 后端部署"
echo "==========================================="
echo ""
echo "服务器: $SERVER"
echo "部署目录: $TARGET_DIR"
echo "端口: $PORT"
echo ""

# 远程执行脚本
ssh "$SERVER" << 'REMOTESHELL'
set -e

TARGET_DIR="/var/www/gj-server"
CONTAINER_NAME="guojie-backend"
IMAGE_TAG="1.1.13"
PORT=8080

cd "$TARGET_DIR"

echo "📁 当前工作目录: $(pwd)"
echo ""

# 1. 查找镜像文件
echo "📦 查找镜像文件..."
if ! ls guojie-backend_*.tar >/dev/null 2>&1; then
  echo "❌ 未找到镜像文件"
  echo "请确保镜像已上传。文件应该在: $TARGET_DIR/guojie-backend_*.tar"
  exit 1
fi

IMAGE_FILE=$(ls guojie-backend_*.tar | head -1)
echo "   找到: $IMAGE_FILE ($(du -h "$IMAGE_FILE" | cut -f1))"
echo ""

# 2. 加载镜像
echo "🔄 加载 Docker 镜像..."
docker load -i "$IMAGE_FILE"
rm -f "$IMAGE_FILE"
echo "✅ 镜像加载完成"
echo ""

# 3. 停止旧容器
echo "🛑 清理旧容器..."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
echo "✅ 清理完成"
echo ""

# 4. 启动新容器
echo "🚀 启动新容器..."
docker run -d --name "$CONTAINER_NAME" \
  --restart=always \
  -p "$PORT:8080" \
  "guojie-backend:$IMAGE_TAG" 

sleep 2

echo "✅ 容器已启动"
echo ""
echo "📊 容器状态:"
docker ps --filter name="$CONTAINER_NAME"

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 后续操作："
echo "  • API 文档: http://47.82.167.164:$PORT/docs"
echo "  • OpenAPI: http://47.82.167.164:$PORT/openapi.json"
echo "  • 查看日志: docker logs $CONTAINER_NAME -f"
REMOTESHELL

echo ""
echo "=========================================="
echo "✅ 部署成功！"
echo "=========================================="
echo ""
