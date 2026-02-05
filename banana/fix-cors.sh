#!/bin/bash

# CORS 修复脚本 - 通过 Cloud Run API 更新 FRONTEND_ORIGINS 环境变量
# 解决 gcloud CLI 无法处理特殊字符问题（如 :// 和 .）

set -e

REGION="asia-southeast1"
SERVICE_NAME="backend"
PROJECT_ID="gen-lang-client-0801638297"

echo "=========================================="
echo "🔧 修复 CORS 配置"
echo "=========================================="

# 清除代理
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy

echo "📍 服务: $SERVICE_NAME"
echo "📍 项目: $PROJECT_ID"
echo "📍 区域: $REGION"

# 方法1：尝试使用 Python gcloud 库（避免 shell 转义问题）
python3 << 'PYTHON_SCRIPT'
import subprocess
import json
import os

os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('ALL_PROXY', None)
os.environ.pop('all_proxy', None)

try:
    # 获取服务信息
    cmd = [
        'gcloud', 'run', 'services', 'describe', 'backend',
        '--region=asia-southeast1',
        '--format=json'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    service_json = json.loads(result.stdout)
    
    # 从服务 JSON 中提取当前的容器镜像
    image = service_json['spec']['template']['spec']['containers'][0]['image']
    print(f"✅ 获得镜像: {image[:80]}...")
    
    # 使用 gcloud run deploy 重新部署，带上 CORS 环境变量
    # 通过创建临时 env 文件来避免命令行特殊字符问题
    with open('/tmp/cors.env', 'w') as f:
        f.write('DISABLE_PROXY=true\n')
        f.write('GOOGLE_API_KEY=AIzaSyBWtpWnMIx9M35qQzPrq-wtPjSm0qNFGtM\n')
        f.write('VERTEX_AI_PROJECT=gen-lang-client-0801638297\n')
        f.write('FRONTEND_ORIGINS=http://120.55.181.23,http://gj.emaos.top,https://gj.emaos.top\n')
    
    # 方法2：直接用 gcloud run deploy 重部署同一镜像，传递环境文件
    print("🚀 重新部署服务（仅更新环境变量）...")
    cmd = [
        'gcloud', 'run', 'deploy', 'backend',
        '--image=' + image,
        '--region=asia-southeast1',
        '--env-vars-file=/tmp/cors.env',
        '--quiet'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 部署成功！CORS 配置已更新")
    else:
        print(f"⚠️  部署失败: {result.stderr}")
        # 尝试只用一个 CORS 变量
        print("💡 尝试简化方法...")
        cmd = [
            'gcloud', 'run', 'deploy', 'backend',
            '--image=' + image,
            '--region=asia-southeast1',
            '--set-env-vars=FRONTEND_ORIGINS=http://120.55.181.23',
            '--quiet'
        ]
        subprocess.run(cmd, check=True)
        print("✅ 已设置 FRONTEND_ORIGINS （部分）")

except Exception as e:
    print(f"❌ 错误: {e}")
    exit(1)

PYTHON_SCRIPT

echo ""
echo "✅ CORS 修复完成！"
echo ""
echo "验证：运行以下命令查看环境变量"
echo "  gcloud run services describe backend --region=asia-southeast1 --format=yaml | grep -A 20 'env:'"

