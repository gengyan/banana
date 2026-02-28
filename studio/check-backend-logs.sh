#!/bin/bash
# 查看服务器后端日志，用于排查 500 等错误
SERVER="${1:-root@47.82.167.164}"
echo "=========================================="
echo "📋 查看 guojie-backend 最近 150 行日志"
echo "=========================================="
ssh "$SERVER" "docker logs guojie-backend --tail 150 2>&1"
