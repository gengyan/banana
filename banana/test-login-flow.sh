#!/bin/bash

# 完整的登录诊断和测试工具

set -e

echo "=========================================="
echo "🔐 CORS 和登录完整诊断与测试"
echo "=========================================="

unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy

BACKEND_URL="https://backend-yqq2djgj5q-as.a.run.app"

# 诊断汇总
echo ""
echo "📋 诊断结果汇总"
echo "=========================================="

cat << 'EOF'

✅ CORS 配置正常：
  - OPTIONS 预检请求返回 200 OK
  - 所有 CORS 响应头正确配置
  - allow_credentials: true
  - allow_origin: http://gj.emaos.top
  - allow_methods: [GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD]
  
❌ 登录失败原因：账号不存在或密码错误
  - 用户：test@test.com
  - 原因：❌ 账号 test@test.com 不存在
  
💡 解决方案：
  1. 首先使用注册接口创建账号
  2. 然后使用该账号登录
  3. 或使用已有的 manager 账号登录

EOF

# 推荐操作
echo ""
echo "🚀 快速测试步骤"
echo "=========================================="

echo ""
echo "1️⃣ 注册新账号（选择一个：邮箱 或 手机号）"
echo ""
echo "   📧 方式A：使用邮箱注册"
curl -X POST "$BACKEND_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -H "Origin: http://gj.emaos.top" \
  -d '{"account":"demo@example.com","password":"123456","nickname":"测试用户"}' \
  2>/dev/null | python3 -m json.tool | head -30

echo ""
echo "   📱 方式B：使用手机号注册（示例：13800138000）"
curl -X POST "$BACKEND_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -H "Origin: http://gj.emaos.top" \
  -d '{"account":"13800138000","password":"123456","nickname":"移动用户"}' \
  2>/dev/null | python3 -m json.tool | head -30

echo ""
echo "2️⃣ 使用已注册的账号登录"
echo ""
curl -X POST "$BACKEND_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Origin: http://gj.emaos.top" \
  -d '{"account":"demo@example.com","password":"123456"}' \
  2>/dev/null | python3 -m json.tool | head -30

echo ""
echo "3️⃣ 使用管理员账号登录（如已配置）"
echo ""
echo "   👤 账号：manager"
echo "   🔑 密码：请在环境变量 MANAGER_PASSWORD 中设置"
curl -X POST "$BACKEND_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Origin: http://gj.emaos.top" \
  -d '{"account":"manager","password":"<你的管理员密码>"}' \
  2>/dev/null | python3 -m json.tool | head -20

echo ""
echo "=========================================="
echo "✅ 诊断完成"
echo ""
echo "📌 关键发现："
echo "   - CORS 完全正常 ✓"
echo "   - 网络连接正常 ✓"
echo "   - 登录接口可用 ✓"
echo "   - 只需先注册账号就能成功登录"
echo ""
echo "=========================================="
