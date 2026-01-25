#!/bin/bash

# Nginx 配置诊断脚本
# 用于排查 /manager 路由无法访问的问题

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
TARGET_DIR="/data/wwwroot/default/guojie"

echo "=========================================="
echo "🔍 Nginx 配置诊断工具"
echo "=========================================="
echo ""
echo "📋 检查目标:"
echo "  服务器: $SERVER"
echo "  域名: $DOMAIN"
echo "  部署目录: $TARGET_DIR"
echo ""

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⚠️  请输入服务器密码${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 使用 SSH ControlMaster 复用连接
SSH_CONTROL_PATH="/tmp/ssh_control_diagnose_$$"
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

# ========================================
# 检查 1: 部署目录和文件
# ========================================
echo "=========================================="
echo -e "${BLUE}1️⃣  检查部署目录和文件${NC}"
echo "=========================================="

if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "[ -d $TARGET_DIR ]" 2>/dev/null; then
    echo -e "${GREEN}✅ 部署目录存在: $TARGET_DIR${NC}"
    
    # 检查 index.html
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "[ -f $TARGET_DIR/index.html ]" 2>/dev/null; then
        echo -e "${GREEN}✅ index.html 存在${NC}"
        
        # 显示 index.html 的前几行
        echo ""
        echo "📄 index.html 内容预览:"
        ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "head -5 $TARGET_DIR/index.html" 2>/dev/null || echo "无法读取文件"
    else
        echo -e "${RED}❌ index.html 不存在${NC}"
    fi
    
    # 检查 assets 目录
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "[ -d $TARGET_DIR/assets ]" 2>/dev/null; then
        ASSET_COUNT=$(ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "find $TARGET_DIR/assets -type f | wc -l" 2>/dev/null || echo "0")
        echo -e "${GREEN}✅ assets 目录存在，包含 $ASSET_COUNT 个文件${NC}"
    else
        echo -e "${YELLOW}⚠️  assets 目录不存在${NC}"
    fi
else
    echo -e "${RED}❌ 部署目录不存在: $TARGET_DIR${NC}"
fi

echo ""

# ========================================
# 检查 2: Nginx 是否运行
# ========================================
echo "=========================================="
echo -e "${BLUE}2️⃣  检查 Nginx 服务状态${NC}"
echo "=========================================="

if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "command -v nginx &> /dev/null" 2>/dev/null; then
    echo -e "${GREEN}✅ Nginx 已安装${NC}"
    
    # 检查 Nginx 是否运行
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "systemctl is-active nginx &> /dev/null || service nginx status &> /dev/null" 2>/dev/null; then
        echo -e "${GREEN}✅ Nginx 服务正在运行${NC}"
    else
        echo -e "${RED}❌ Nginx 服务未运行${NC}"
        echo "   尝试启动: sudo systemctl start nginx"
    fi
else
    echo -e "${RED}❌ Nginx 未安装${NC}"
fi

echo ""

# ========================================
# 检查 3: 查找 Nginx 配置文件
# ========================================
echo "=========================================="
echo -e "${BLUE}3️⃣  查找 Nginx 配置文件${NC}"
echo "=========================================="

CONFIG_PATHS=(
    "/etc/nginx/sites-available/guojie"
    "/etc/nginx/sites-available/${DOMAIN}"
    "/etc/nginx/sites-enabled/guojie"
    "/etc/nginx/sites-enabled/${DOMAIN}"
    "/etc/nginx/conf.d/guojie.conf"
    "/etc/nginx/conf.d/${DOMAIN}.conf"
    "/etc/nginx/nginx.conf"
)

FOUND_CONFIG=""
for path in "${CONFIG_PATHS[@]}"; do
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "[ -f $path ]" 2>/dev/null; then
        echo -e "${GREEN}✅ 找到配置文件: $path${NC}"
        FOUND_CONFIG="$path"
        
        # 如果是主配置文件，检查是否包含我们的域名配置
        if [[ "$path" == *"nginx.conf" ]]; then
            echo "   这是主配置文件，检查是否包含 server 块..."
            ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep -i '$DOMAIN' $path" 2>/dev/null || echo "   未找到域名配置"
        fi
        break
    fi
done

if [ -z "$FOUND_CONFIG" ]; then
    echo -e "${RED}❌ 未找到相关配置文件${NC}"
    echo "   尝试查找包含域名的配置文件..."
    ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep -r '$DOMAIN' /etc/nginx/ 2>/dev/null | head -5" || echo "   未找到"
fi

echo ""

# ========================================
# 检查 4: 检查配置文件内容（关键：SPA 路由支持）
# ========================================
if [ -n "$FOUND_CONFIG" ]; then
    echo "=========================================="
    echo -e "${BLUE}4️⃣  检查配置文件内容（关键检查）${NC}"
    echo "=========================================="
    
    echo "📄 配置文件: $FOUND_CONFIG"
    echo ""
    
    # 检查是否包含域名
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep -q '$DOMAIN' $FOUND_CONFIG" 2>/dev/null; then
        echo -e "${GREEN}✅ 包含域名配置: $DOMAIN${NC}"
    else
        echo -e "${YELLOW}⚠️  未找到域名配置${NC}"
    fi
    
    # 检查是否包含 root 路径
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep -q 'root.*$TARGET_DIR' $FOUND_CONFIG" 2>/dev/null; then
        echo -e "${GREEN}✅ 包含正确的 root 路径${NC}"
        ROOT_PATH=$(ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep 'root' $FOUND_CONFIG | grep -v '^#' | head -1" 2>/dev/null || echo "")
        echo "   $ROOT_PATH"
    else
        echo -e "${YELLOW}⚠️  未找到正确的 root 路径${NC}"
        echo "   检查所有 root 配置:"
        ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep -i 'root' $FOUND_CONFIG | grep -v '^#'" 2>/dev/null || echo "   未找到"
    fi
    
    # 🔥 关键检查：是否包含 try_files（SPA 路由支持）
    echo ""
    echo -e "${BLUE}🔍 关键检查：SPA 路由支持（try_files）${NC}"
    if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep -q 'try_files' $FOUND_CONFIG" 2>/dev/null; then
        echo -e "${GREEN}✅ 找到 try_files 配置${NC}"
        echo "   配置内容:"
        ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep -A 2 -B 2 'try_files' $FOUND_CONFIG | grep -v '^#'" 2>/dev/null || echo "   无法读取"
        
        # 检查是否正确配置了 try_files $uri $uri/ /index.html;
        if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep 'try_files.*index.html' $FOUND_CONFIG" 2>/dev/null; then
            echo -e "${GREEN}✅ try_files 配置正确（包含 /index.html）${NC}"
        else
            echo -e "${RED}❌ try_files 配置不正确（缺少 /index.html）${NC}"
            echo "   正确的配置应该是: try_files \$uri \$uri/ /index.html;"
        fi
    else
        echo -e "${RED}❌ 未找到 try_files 配置（这是问题所在！）${NC}"
        echo "   需要在 location / 块中添加: try_files \$uri \$uri/ /index.html;"
    fi
    
    # 显示完整的 location / 块
    echo ""
    echo "📄 location / 块内容:"
    ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "sed -n '/location \/ {/,/^[[:space:]]*}/p' $FOUND_CONFIG 2>/dev/null || grep -A 10 'location /' $FOUND_CONFIG | head -15" 2>/dev/null || echo "   无法读取 location 块"
    
    echo ""
fi

# ========================================
# 检查 5: 测试 Nginx 配置语法
# ========================================
echo "=========================================="
echo -e "${BLUE}5️⃣  测试 Nginx 配置语法${NC}"
echo "=========================================="

if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "nginx -t 2>&1" 2>/dev/null; then
    echo -e "${GREEN}✅ Nginx 配置语法正确${NC}"
else
    echo -e "${RED}❌ Nginx 配置语法错误${NC}"
    echo "   错误详情:"
    ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "nginx -t 2>&1" 2>/dev/null || echo "   无法获取错误信息"
fi

echo ""

# ========================================
# 检查 6: 检查服务器上的实际访问
# ========================================
echo "=========================================="
echo -e "${BLUE}6️⃣  测试服务器本地访问${NC}"
echo "=========================================="

# 测试 index.html
if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost/" 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}✅ 服务器本地可以访问首页（HTTP 200）${NC}"
else
    HTTP_CODE=$(ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost/" 2>/dev/null || echo "未知")
    echo -e "${YELLOW}⚠️  服务器本地访问返回: $HTTP_CODE${NC}"
fi

# 测试 /manager 路径
MANAGER_CODE=$(ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost/manager" 2>/dev/null || echo "未知")
echo "   /manager 路径返回: $MANAGER_CODE"

if [ "$MANAGER_CODE" = "200" ]; then
    echo -e "${GREEN}✅ /manager 路径可以访问（HTTP 200）${NC}"
elif [ "$MANAGER_CODE" = "404" ]; then
    echo -e "${RED}❌ /manager 路径返回 404（Nginx 配置问题）${NC}"
    echo "   这说明 Nginx 没有正确配置 SPA 路由支持"
else
    echo -e "${YELLOW}⚠️  /manager 路径返回: $MANAGER_CODE${NC}"
fi

echo ""

# ========================================
# 总结和建议
# ========================================
echo "=========================================="
echo -e "${BLUE}📋 诊断总结${NC}"
echo "=========================================="
echo ""

if ssh -o ControlPath=$SSH_CONTROL_PATH "$SERVER" "grep -q 'try_files.*index.html' $FOUND_CONFIG 2>/dev/null" 2>/dev/null; then
    echo -e "${GREEN}✅ 配置文件看起来正确${NC}"
    echo ""
    echo "如果仍然无法访问，可能的原因："
    echo "  1. Nginx 配置未重载: sudo systemctl reload nginx"
    echo "  2. 浏览器缓存问题: 尝试强制刷新 (Ctrl+F5)"
    echo "  3. DNS 解析问题: 检查域名是否正确解析"
else
    echo -e "${RED}❌ 发现配置问题：缺少 SPA 路由支持${NC}"
    echo ""
    echo "🔧 解决方案："
    echo "  1. 运行修复脚本: ./fix-nginx-config.sh"
    echo "  2. 或手动修复配置文件 $FOUND_CONFIG"
    echo "     在 location / 块中添加: try_files \$uri \$uri/ /index.html;"
    echo ""
fi

echo ""
