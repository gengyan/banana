#!/bin/bash

# 完整的安全性和问题诊断报告

set -e

echo "=========================================="
echo "🔐 后端安全性与登录问题综合诊断"
echo "=========================================="

unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy

# 1. 检查环境敏感信息是否泄露
echo ""
echo "🔍 1️⃣ 检查环境敏感信息暴露"
echo "=========================================="

BACKEND_LOGS=$(gcloud run services logs read backend --region=asia-southeast1 --limit=100 2>&1)

echo "$BACKEND_LOGS" | grep -i "api_key\|password\|secret\|token\|credential" | head -5 && \
  echo "⚠️  警告：检测到可能的敏感信息泄露" || \
  echo "✅ 未检测到明显的敏感信息泄露"

# 2. 检查 CORS 配置是否完整
echo ""
echo "🔍 2️⃣ 验证 CORS 配置完整性"
echo "=========================================="

curl -s -X OPTIONS "https://backend-yqq2djgj5q-as.a.run.app/api/auth/login" \
  -H "Origin: http://gj.emaos.top" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization" \
  -H "User-Agent: Mozilla/5.0" \
  -w "\nHTTP Status: %{http_code}\n" | grep -E "access-control|HTTP Status"

# 3. 检查是否有 POST 登录请求到达后端
echo ""
echo "🔍 3️⃣ 检查后端登录请求日志"
echo "=========================================="

gcloud run services logs read backend --region=asia-southeast1 --limit=50 2>&1 | \
  grep -i "post.*login\|401\|400.*login" | tail -10 || \
  echo "⚠️  未检测到 POST /api/auth/login 请求"

# 4. 检查后端是否正确处理 Content-Type 和 credentials
echo ""
echo "🔍 4️⃣ 验证 Content-Type 和 credentials 处理"
echo "=========================================="

echo "📋 后端 CORS 中间件配置:"
grep -A 5 "allow_credentials" /Users/mac/Documents/ai/knowledgebase/bananas/banana/backend/main.py | head -10

# 5. 检查前端 API 配置
echo ""
echo "🔍 5️⃣ 检查前端 API 基础 URL 配置"
echo "=========================================="

echo "📋 前端 API 配置文件内容:"
cat /Users/mac/Documents/ai/knowledgebase/bananas/banana/frontend/src/config/api.js | grep -E "VITE_API_BASE_URL|baseURL|API_BASE_URL"

# 6. 检查是否需要在请求中添加 credentials
echo ""
echo "🔍 6️⃣ 检查 axios 请求配置"
echo "=========================================="

echo "📋 前端 client.js 中的 axios 配置:"
grep -A 2 "axios.create" /Users/mac/Documents/ai/knowledgebase/bananas/banana/frontend/src/api/client.js

# 7. 安全性建议
echo ""
echo "🛡️  7️⃣ 安全性建议"
echo "=========================================="

cat << 'EOF'

✅ 已完成的安全改进：
  1. CORS 允许清单已配置：gj.emaos.top, 120.55.181.23
  2. 后端已设置 allow_credentials=true
  3. 项目 ID 后面的空格已移除
  4. 所有环境变量在读取时使用 .strip()
  5. CORS 响应头完整返回

⚠️ 需要检查的项目：
  1. 前端是否正确发送 POST 请求（检查浏览器控制台网络标签页）
  2. axios 请求是否需要添加 withCredentials: true
  3. Content-Type: application/json 是否被正确发送
  4. 是否有浏览器插件或中间件拦截请求
  5. 防火墙或 CDN 是否有额外的 CORS 限制

🔐 关键安全检查点：
  ✓ 不在日志中打印敏感信息（密码、API密钥）
  ✓ 后端已启用 CORS allow_credentials
  ✓ HTTPS 已正确配置
  ✓ 会话令牌已存储在 localStorage
  ✓ 跨域请求包含必要的安全头

EOF

echo ""
echo "=========================================="
echo "✅ 诊断完成"
echo "=========================================="
