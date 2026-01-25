#!/bin/bash
# 更新 main.jsx 中的构建时间戳
BUILD_TIME=$(date +"%Y-%m-%d-%H-%M-%S")
sed -i.bak "s|// BUILD: .*|// BUILD: $BUILD_TIME|" src/main.jsx
rm -f src/main.jsx.bak
echo "✅ 已更新构建时间戳: $BUILD_TIME"

