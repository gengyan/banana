#!/bin/bash
# 测试后端修复效果

BACKEND_URL="https://backend-1045502692494.asia-southeast1.run.app"

echo "🧪 后端修复验证测试"
echo "================================"
echo ""

echo "1️⃣ 测试健康检查..."
HEALTH=$(curl -s -m 10 "$BACKEND_URL/health")
echo "$HEALTH" | python3 -m json.tool
echo ""

echo "2️⃣ 测试管理员登录..."
LOGIN_RESULT=$(curl -s -X POST "$BACKEND_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "manager",
    "password": "Admin@123456"
  }')
echo "$LOGIN_RESULT" | python3 -m json.tool
echo ""

echo "3️⃣ 检查环境变量日志..."
gcloud run services logs read backend --region asia-southeast1 --limit 30 2>&1 | \
  grep -E "VERTEX_AI_LOCATION|VERTEX_AI_PROJECT|管理员账号" | tail -5
echo ""

echo "4️⃣ 测试 Pro 接口错误处理（使用空提示词触发验证错误）..."
PRO_ERROR=$(curl -s -X POST "$BACKEND_URL/api/banana-img-pro" \
  -H "Content-Type: application/json" \
  -d '{"message": ""}' \
  -w "\nHTTP_CODE:%{http_code}")

echo "$PRO_ERROR" | grep -v "HTTP_CODE" | python3 -m json.tool 2>/dev/null || echo "$PRO_ERROR"
HTTP_CODE=$(echo "$PRO_ERROR" | grep "HTTP_CODE" | sed 's/HTTP_CODE://')
echo ""
echo "返回的 HTTP 状态码: $HTTP_CODE"
echo ""

if [[ "$HTTP_CODE" == "503" ]]; then
    echo "❌ Pro 接口仍然返回 503（网关错误）"
else
    echo "✅ Pro 接口返回了正确的 HTTP 状态码（不是 503）"
fi

echo ""
echo "================================"
echo "✅ 测试完成"
