#!/bin/bash

echo "🚀 开始构建前端项目..."

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi

# 执行构建
echo "🔨 执行构建..."
npm run build

# 检查构建结果
if [ -d "dist" ]; then
    echo ""
    echo "✅ 构建成功！"
    echo "📁 构建输出目录: dist/"
    echo "📊 文件大小:"
    du -sh dist/
    echo ""
    echo "📝 构建文件列表:"
    ls -lh dist/ | head -20
    echo ""
    echo "💡 提示:"
    echo "1. 将 dist 目录中的所有文件上传到你的 Web 服务器"
    echo "2. 确保服务器配置了正确的路由（单页应用需要配置回退到 index.html）"
    echo "3. 设置环境变量 VITE_API_BASE_URL 指向你的后端 API 地址"
else
    echo "❌ 构建失败，dist 目录不存在"
    exit 1
fi

