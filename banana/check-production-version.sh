#!/bin/bash

# 诊断脚本：检查生产环境的实际版本

echo "=================================================="
echo "🔍 生产环境诊断脚本"
echo "=================================================="
echo ""

# 1. 检查本地 requirements.txt
echo "📋 本地 requirements.txt 中 google-genai 版本："
grep "google-genai" banana/backend/requirements.txt || echo "❌ 未找到"
echo ""

# 2. 检查本地当前环境的 google-genai 版本
echo "📦 本地当前环境 google-genai 版本："
python -c "import google.genai as g; print(f'版本: {g.__version__}')" 2>/dev/null || echo "❌ 模块未装或版本过旧"
echo ""

# 3. 检查本地代码是否有防御性编程
echo "🛡️  本地代码防御性编程检查："
if grep -q "_create_image_config_safely" banana/backend/generators/gemini_3_pro_image.py; then
    echo "✅ 防御性编程函数已包含"
else
    echo "❌ 防御性编程函数未找到"
fi
echo ""

# 4. 检查版本号日志是否存在
echo "📝 版本号日志检查："
if grep -q "📦 google-genai 版本:" banana/backend/generators/gemini_3_pro_image.py; then
    echo "✅ 版本号日志已添加"
else
    echo "❌ 版本号日志未找到"
fi
echo ""

echo "=================================================="
echo "✅ 诊断完成"
echo ""
echo "如果本地检查都是 ✅，说明代码已准备好"
echo "需要部署到生产环境："
echo "  git add ."
echo "  git commit -m '修复: google-genai 1.64.0 防御性编程'"
echo "  git push origin main"
echo ""
echo "然后在生产环境执行："
echo "  git pull origin main"
echo "  pip install -r backend/requirements.txt --upgrade --force"
echo "  # 重启后端服务"
echo "=================================================="
