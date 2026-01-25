#!/bin/bash

# 修复服务器 Nginx 配置脚本
# 用于修复 SPA 路由问题（如 /manager 无法访问）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务器信息
SERVER="root@120.55.181.23"
DOMAIN="gj.emaos.top"
DEPLOY_DIR="/data/wwwroot/default/guojie"
NGINX_CONFIG_TEMPLATE="frontend/nginx.server.conf"

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "🔧 修复服务器 Nginx 配置"
echo "=========================================="
echo ""
echo "📋 配置信息:"
echo "  服务器: $SERVER"
echo "  域名: $DOMAIN"
echo "  部署目录: $DEPLOY_DIR"
echo ""

# 检查配置文件是否存在
if [ ! -f "$NGINX_CONFIG_TEMPLATE" ]; then
    echo -e "${RED}❌ 配置文件不存在: $NGINX_CONFIG_TEMPLATE${NC}"
    exit 1
fi

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⚠️  请输入服务器密码${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 使用 SSH ControlMaster 复用连接
SSH_CONTROL_PATH="/tmp/ssh_control_$$"
SSH_OPTS="-o ControlMaster=yes -o ControlPath=$SSH_CONTROL_PATH -o ControlPersist=60 -o StrictHostKeyChecking=no"

# 清理函数
cleanup() {
    ssh -O exit -o ControlPath=$SSH_CONTROL_PATH "$SERVER" 2>/dev/null || true
    rm -f $SSH_CONTROL_PATH
}
trap cleanup EXIT

# 建立 SSH 控制连接
echo "正在建立 SSH 连接..."
ssh $SSH_OPTS -f -N "$SERVER" || {
    echo -e "${RED}❌ SSH 连接失败${NC}"
    exit 1
}

echo -e "${GREEN}✅ SSH 连接已建立${NC}"
echo ""

# 步骤 1: 检查部署目录是否存在
echo "=========================================="
echo -e "${BLUE}📂 步骤 1: 检查部署目录${NC}"
echo "=========================================="
if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "[ ! -d $DEPLOY_DIR ]"; then
    echo -e "${RED}❌ 部署目录不存在: $DEPLOY_DIR${NC}"
    echo -e "${YELLOW}请先运行 deploy-frontend-server.sh 部署前端${NC}"
    exit 1
fi

if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "[ ! -f $DEPLOY_DIR/index.html ]"; then
    echo -e "${RED}❌ index.html 不存在${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 部署目录检查通过${NC}"
echo ""

# 步骤 2: 检查 Nginx 是否安装
echo "=========================================="
echo -e "${BLUE}🔍 步骤 2: 检查 Nginx 安装${NC}"
echo "=========================================="
if ! ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "command -v nginx &> /dev/null"; then
    echo -e "${RED}❌ Nginx 未安装${NC}"
    echo -e "${YELLOW}请先安装 Nginx:${NC}"
    echo "   Ubuntu/Debian: sudo apt-get install nginx"
    echo "   CentOS/RHEL: sudo yum install nginx"
    exit 1
fi

echo -e "${GREEN}✅ Nginx 已安装${NC}"
echo ""

# 步骤 3: 查找现有配置文件
echo "=========================================="
echo -e "${BLUE}📝 步骤 3: 查找现有 Nginx 配置${NC}"
echo "=========================================="
NGINX_CONFIG_PATH=""

# 尝试常见位置
CONFIG_PATHS=(
    "/etc/nginx/sites-available/guojie"
    "/etc/nginx/sites-available/${DOMAIN}"
    "/etc/nginx/conf.d/guojie.conf"
    "/etc/nginx/conf.d/${DOMAIN}.conf"
    "/etc/nginx/sites-enabled/guojie"
    "/etc/nginx/sites-enabled/${DOMAIN}"
)

for path in "${CONFIG_PATHS[@]}"; do
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "[ -f $path ]"; then
        NGINX_CONFIG_PATH="$path"
        echo -e "${GREEN}✅ 找到现有配置: $path${NC}"
        break
    fi
done

if [ -z "$NGINX_CONFIG_PATH" ]; then
    echo -e "${YELLOW}⚠️  未找到现有配置，将创建新配置${NC}"
    
    # 确定使用哪个位置
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "[ -d /etc/nginx/sites-available ]"; then
        NGINX_CONFIG_PATH="/etc/nginx/sites-available/guojie"
        ENABLE_PATH="/etc/nginx/sites-enabled/guojie"
        USE_SITES_AVAILABLE=true
    else
        NGINX_CONFIG_PATH="/etc/nginx/conf.d/guojie.conf"
        USE_SITES_AVAILABLE=false
    fi
    
    echo -e "${BLUE}将创建配置: $NGINX_CONFIG_PATH${NC}"
fi

echo ""

# 步骤 4: 上传配置模板并替换变量
echo "=========================================="
echo -e "${BLUE}📤 步骤 4: 上传配置${NC}"
echo "=========================================="

# 读取模板并替换变量
TEMP_CONFIG=$(mktemp)
sed "s|/data/wwwroot/default/guojie|$DEPLOY_DIR|g" "$NGINX_CONFIG_TEMPLATE" | \
    sed "s|gj.emaos.top|$DOMAIN|g" > "$TEMP_CONFIG"

# 上传到服务器
scp -o ControlPath=$SSH_CONTROL_PATH "$TEMP_CONFIG" "$SERVER:$NGINX_CONFIG_PATH"

rm -f "$TEMP_CONFIG"

echo -e "${GREEN}✅ 配置已上传${NC}"
echo ""

# 步骤 5: 创建符号链接（如果需要）
if [ "$USE_SITES_AVAILABLE" = true ] && [ -n "$ENABLE_PATH" ]; then
    echo "=========================================="
    echo -e "${BLUE}🔗 步骤 5: 启用配置${NC}"
    echo "=========================================="
    
    ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "
        if [ ! -L $ENABLE_PATH ]; then
            ln -s $NGINX_CONFIG_PATH $ENABLE_PATH
            echo '✅ 已创建符号链接'
        else
            echo '✅ 符号链接已存在'
        fi
    "
    echo ""
fi

# 步骤 6: 测试配置
echo "=========================================="
echo -e "${BLUE}✅ 步骤 6: 测试 Nginx 配置${NC}"
echo "=========================================="
if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "nginx -t 2>&1"; then
    echo -e "${GREEN}✅ Nginx 配置测试通过${NC}"
else
    echo -e "${RED}❌ Nginx 配置测试失败${NC}"
    echo -e "${YELLOW}请检查配置文件: $NGINX_CONFIG_PATH${NC}"
    exit 1
fi
echo ""

# 步骤 7: 重载 Nginx
echo "=========================================="
echo -e "${BLUE}🔄 步骤 7: 重载 Nginx${NC}"
echo "=========================================="
if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "systemctl reload nginx 2>&1 || service nginx reload 2>&1"; then
    echo -e "${GREEN}✅ Nginx 已重载${NC}"
else
    echo -e "${RED}❌ Nginx 重载失败，请手动执行: sudo systemctl reload nginx${NC}"
    exit 1
fi
echo ""

# 完成
echo "=========================================="
echo -e "${GREEN}✅ 配置修复完成！${NC}"
echo "=========================================="
echo ""
echo "📋 配置信息:"
echo "  配置文件: $NGINX_CONFIG_PATH"
if [ "$USE_SITES_AVAILABLE" = true ] && [ -n "$ENABLE_PATH" ]; then
    echo "  启用链接: $ENABLE_PATH"
fi
echo "  域名: $DOMAIN"
echo "  部署目录: $DEPLOY_DIR"
echo ""
echo -e "${GREEN}🌐 现在可以访问: http://$DOMAIN/manager${NC}"
echo ""
echo -e "${YELLOW}💡 提示:${NC}"
echo "  如果仍然无法访问，请检查："
echo "  1. 防火墙是否开放 80/443 端口"
echo "  2. DNS 解析是否正确指向服务器 IP"
echo "  3. 浏览器控制台是否有错误信息"
echo ""
