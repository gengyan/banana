#!/bin/bash

# 后端 CORS 和登录诊断工具

set -e

echo "=========================================="
echo "🔍 CORS 和登录问题诊断"
echo "=========================================="

# 清除代理
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy

BACKEND_URL="https://backend-yqq2djgj5q-as.a.run.app"
FRONTEND_URL="http://gj.emaos.top"

echo ""
echo "📍 后端 URL: $BACKEND_URL"
echo "📍 前端 URL: $FRONTEND_URL"

# 测试 1: 直接 OPTIONS 预检
echo ""
echo "1️⃣  测试 OPTIONS 预检请求..."
curl -v -X OPTIONS "$BACKEND_URL/api/auth/login" \
  -H "Origin: $FRONTEND_URL" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  2>&1 | grep -i "access-control\|200\|<"

# 测试 2: 直接 POST 登录（无凭证）
echo ""
echo "2️⃣  测试 POST 登录请求（包含 CORS 头）..."
curl -v -X POST "$BACKEND_URL/api/auth/login" \
  -H "Origin: $FRONTEND_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"account":"test@test.com","password":"123456"}' \
  2>&1 | head -50

# 测试 3: 检查后端日志中是否有 POST 请求
echo ""
echo "3️⃣  检查后端日志中的 POST /api/auth/login 请求..."
gcloud run services logs read backend --region=asia-southeast1 --limit=30 2>&1 | grep "POST.*login" | head -5 || echo "⚠️  未找到 POST /api/auth/login 日志"

# 测试 4: 检查 CORS 响应头
echo ""
echo "4️⃣  详细 CORS 响应头检查..."
curl -i -X OPTIONS "$BACKEND_URL/api/auth/login" \
  -H "Origin: $FRONTEND_URL" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  2>&1 | grep -E "HTTP|Access-Control|Content-Type|Allow"

echo ""
echo "=========================================="
echo "✅ 诊断完成"
echo "=========================================="
