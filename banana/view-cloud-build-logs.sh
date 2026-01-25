#!/bin/bash
# 查看 Cloud Build 日志，了解服务器构建过程

echo "=========================================="
echo "📋 查看 Cloud Build 构建日志"
echo "=========================================="
echo ""

echo "🔍 查找最近的构建..."
LATEST_BUILD=$(gcloud builds list --limit=1 --format="value(id)" 2>/dev/null)

if [ -z "$LATEST_BUILD" ]; then
    echo "❌ 未找到构建记录"
    exit 1
fi

echo "✅ 找到最近的构建: $LATEST_BUILD"
echo ""

echo "📊 构建信息："
gcloud builds describe "$LATEST_BUILD" --format="table(status,createTime,finishTime,logUrl)" 2>/dev/null

echo ""
echo "📄 查看构建日志（最后 100 行）..."
echo "----------------------------------------"
gcloud builds log "$LATEST_BUILD" --limit=100 2>/dev/null | tail -100

echo ""
echo "----------------------------------------"
echo ""
echo "💡 查看完整日志："
echo "   gcloud builds log $LATEST_BUILD"
echo ""
echo "💡 查看构建详情："
echo "   gcloud builds describe $LATEST_BUILD"
echo ""
echo "💡 在浏览器中查看日志："
BUILD_URL=$(gcloud builds describe "$LATEST_BUILD" --format="value(logUrl)" 2>/dev/null)
if [ -n "$BUILD_URL" ]; then
    echo "   $BUILD_URL"
fi

