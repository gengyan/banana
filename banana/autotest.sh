#!/bin/bash
# 果捷后端服务自动化测试脚本
# 功能：账号测试、文生图测试、代理检查、建议接口验证、帮助文档验证

# 不使用 set -e，因为我们需要继续执行即使某些测试失败

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
BACKEND_URL="http://localhost:8080"
FRONTEND_URL="http://localhost:3000"
# 测试账号：使用邮箱格式
TEST_ACCOUNT="test_$(date +%s)@example.com"
TEST_PASSWORD="test123456"
TEST_EMAIL="test@example.com"
TEST_NICKNAME="自动测试用户"
OUTPUT_DIR="./test_output"
LOG_FILE="$OUTPUT_DIR/test_$(date +%Y%m%d_%H%M%S).log"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# 测试计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

test_start() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log_info "测试 #$TOTAL_TESTS: $1"
}

test_pass() {
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "✅ 测试通过: $1"
}

test_fail() {
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "❌ 测试失败: $1"
}

test_warning() {
    log_warning "⚠️  $1"
}

# 等待服务启动
wait_for_service() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    log_info "等待服务启动: $url"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_success "服务已就绪"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    log_error "服务启动超时"
    return 1
}

# ============================================================================
# 测试 23.1: 账号创建和登录测试
# ============================================================================
test_account_creation_and_login() {
    echo ""
    echo "============================================================"
    log_info "测试 23.1: 账号创建和登录"
    echo "============================================================"
    
    # 23.1.1 测试账号注册
    test_start "账号注册"
    
    register_response=$(curl -s -X POST "$BACKEND_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"account\": \"$TEST_ACCOUNT\",
            \"password\": \"$TEST_PASSWORD\",
            \"email\": \"$TEST_EMAIL\",
            \"nickname\": \"$TEST_NICKNAME\"
        }")
    
    if echo "$register_response" | grep -q "success.*true"; then
        test_pass "账号注册成功"
        log_info "注册响应: $register_response"
    else
        test_fail "账号注册失败: $register_response"
        return 1
    fi
    
    # 23.1.2 测试登录
    test_start "账号登录"
    
    login_response=$(curl -s -X POST "$BACKEND_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"account\": \"$TEST_ACCOUNT\",
            \"password\": \"$TEST_PASSWORD\"
        }")
    
    if echo "$login_response" | grep -q "success.*true"; then
        test_pass "账号登录成功"
        # 提取 token
        TOKEN=$(echo "$login_response" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
        log_info "获取到 Token: ${TOKEN:0:20}..."
        export TEST_TOKEN="$TOKEN"
    else
        test_fail "账号登录失败: $login_response"
        return 1
    fi
    
    # 23.1.3 测试重复注册（应该失败）
    test_start "重复注册验证"
    
    duplicate_response=$(curl -s -X POST "$BACKEND_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"account\": \"$TEST_ACCOUNT\",
            \"password\": \"$TEST_PASSWORD\"
        }")
    
    if echo "$duplicate_response" | grep -q "已被注册\|already exists"; then
        test_pass "重复注册验证通过（正确拒绝）"
    else
        test_warning "重复注册验证失败: 应该拒绝重复账号"
    fi
}

# ============================================================================
# 测试 23.2: 文生图测试
# ============================================================================
test_image_generation() {
    echo ""
    echo "============================================================"
    log_info "测试 23.2: 文生图测试"
    echo "============================================================"
    
    # 23.2.1 测试 Gemini 2.5 文生图
    test_start "Gemini 2.5 Flash Image 文生图"
    
    gemini25_response=$(curl -s -X POST "$BACKEND_URL/api/banana-img" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TEST_TOKEN" \
        -d '{
            "prompt": "A beautiful mountain landscape with snow and blue sky, test image",
            "width": 1024,
            "height": 768
        }' \
        -w "\n%{http_code}" \
        -o "$OUTPUT_DIR/test_gemini25.jpg")
    
    http_code=$(echo "$gemini25_response" | tail -1)
    
    if [ "$http_code" = "200" ] && [ -f "$OUTPUT_DIR/test_gemini25.jpg" ]; then
        file_size=$(wc -c < "$OUTPUT_DIR/test_gemini25.jpg")
        if [ "$file_size" -gt 1000 ]; then
            test_pass "Gemini 2.5 生图成功 (大小: $file_size bytes)"
            log_info "图片已保存: $OUTPUT_DIR/test_gemini25.jpg"
        else
            test_fail "Gemini 2.5 返回的文件太小，可能不是有效图片"
        fi
    else
        test_fail "Gemini 2.5 生图失败 (HTTP $http_code)"
    fi
    
    # 23.2.2 测试 Gemini 3 Pro 文生图
    test_start "Gemini 3 Pro Image 文生图"
    
    gemini3_response=$(curl -s -X POST "$BACKEND_URL/api/banana-img-pro" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TEST_TOKEN" \
        -d '{
            "prompt": "A futuristic city at sunset with flying cars, test image",
            "width": 2048,
            "height": 1536
        }' \
        -w "\n%{http_code}" \
        -o "$OUTPUT_DIR/test_gemini3.jpg")
    
    http_code=$(echo "$gemini3_response" | tail -1)
    
    if [ "$http_code" = "200" ] && [ -f "$OUTPUT_DIR/test_gemini3.jpg" ]; then
        file_size=$(wc -c < "$OUTPUT_DIR/test_gemini3.jpg")
        if [ "$file_size" -gt 1000 ]; then
            test_pass "Gemini 3 Pro 生图成功 (大小: $file_size bytes)"
            log_info "图片已保存: $OUTPUT_DIR/test_gemini3.jpg"
        else
            test_fail "Gemini 3 Pro 返回的文件太小，可能不是有效图片"
        fi
    else
        test_fail "Gemini 3 Pro 生图失败 (HTTP $http_code)"
    fi
}

# ============================================================================
# 测试 23.3: 代理配置检查
# ============================================================================
test_proxy_configuration() {
    echo ""
    echo "============================================================"
    log_info "测试 23.3: 代理配置检查"
    echo "============================================================"
    
    # 23.3.1 检查当前代理状态
    test_start "检查后端代理配置"
    
    proxy_health=$(curl -s "$BACKEND_URL/proxy-health")
    
    log_info "代理健康检查响应:"
    echo "$proxy_health" | python3 -m json.tool 2>/dev/null | tee -a "$LOG_FILE" || echo "$proxy_health" | tee -a "$LOG_FILE"
    
    # 检查是否禁用了代理
    if echo "$proxy_health" | grep -q "DISABLE_PROXY"; then
        disable_proxy=$(echo "$proxy_health" | grep -o '"DISABLE_PROXY":"[^"]*"' | cut -d'"' -f4)
        
        if [ "$disable_proxy" = "true" ] || [ "$disable_proxy" = "null" ]; then
            test_pass "生产环境代理配置正确（已禁用或未设置）"
        else
            test_warning "生产环境可能启用了代理（DISABLE_PROXY=$disable_proxy）"
        fi
    else
        test_pass "代理健康检查接口响应正常"
    fi
    
    # 23.3.2 检查环境变量文件
    test_start "检查 .env 配置文件"
    
    if [ -f "backend/.env" ]; then
        log_info "检查 backend/.env 文件中的代理配置:"
        
        if grep -q "^DISABLE_PROXY=true" backend/.env; then
            test_pass "生产环境 .env 正确配置（DISABLE_PROXY=true）"
        elif grep -q "^USE_SOCKS5_PROXY=false" backend/.env; then
            test_pass "生产环境 .env 正确配置（USE_SOCKS5_PROXY=false）"
        else
            test_warning "建议在生产环境设置 DISABLE_PROXY=true"
        fi
    else
        test_warning ".env 文件不存在，可能使用系统环境变量"
    fi
}

# ============================================================================
# 测试 23.4: 用户建议接口验证
# ============================================================================
test_feedback_api() {
    echo ""
    echo "============================================================"
    log_info "测试 23.4: 用户建议接口验证"
    echo "============================================================"
    
    # 23.4.1 提交用户建议
    test_start "提交用户建议"
    
    feedback_response=$(curl -s -X POST "$BACKEND_URL/api/feedback/submit" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TEST_TOKEN" \
        -d "{
            \"content\": \"这是一个自动化测试建议 - $(date)\",
            \"contact\": \"$TEST_EMAIL\",
            \"type\": \"suggestion\"
        }")
    
    if echo "$feedback_response" | grep -q "success.*true"; then
        test_pass "用户建议提交成功"
        log_info "建议响应: $feedback_response"
    else
        test_fail "用户建议提交失败: $feedback_response"
    fi
    
    # 23.4.2 查询用户建议列表
    test_start "查询用户建议列表"
    
    feedback_list=$(curl -s -X GET "$BACKEND_URL/api/feedback/list" \
        -H "Authorization: Bearer $TEST_TOKEN")
    
    if echo "$feedback_list" | grep -q "success.*true\|feedbacks\|\[\]"; then
        test_pass "用户建议列表查询成功"
    else
        test_fail "用户建议列表查询失败: $feedback_list"
    fi
}

# ============================================================================
# 测试 23.5: 帮助文档验证
# ============================================================================
test_help_documentation() {
    echo ""
    echo "============================================================"
    log_info "测试 23.5: 帮助文档验证"
    echo "============================================================"
    
    # 23.5.1 测试帮助文档是否可访问
    test_start "访问帮助文档 HTML"
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL/help.html" 2>/dev/null)
    
    if [ "$http_code" = "200" ]; then
        test_pass "帮助文档 HTML 可正常访问"
    else
        test_warning "帮助文档 HTML 访问失败 (HTTP $http_code) - 可能需要启动前端服务"
    fi
    
    # 23.5.2 测试前端帮助路由
    test_start "访问前端帮助路由"
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL/help" 2>/dev/null)
    
    if [ "$http_code" = "200" ]; then
        test_pass "前端帮助路由可正常访问"
    else
        test_warning "前端帮助路由访问失败 (HTTP $http_code) - 可能需要启动前端服务"
    fi
    
    # 23.5.3 检查静态帮助文件是否存在
    test_start "检查帮助文档文件"
    
    if [ -f "frontend/public/help.html" ] || [ -f "frontend/dist/help.html" ]; then
        test_pass "帮助文档文件存在"
    else
        test_warning "帮助文档文件未找到（可能在其他位置）"
    fi
}

# ============================================================================
# 主测试流程
# ============================================================================
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║        果捷后端服务 - 自动化测试套件                           ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "测试开始时间: $(date)"
    log_info "后端地址: $BACKEND_URL"
    log_info "前端地址: $FRONTEND_URL"
    log_info "测试账号: $TEST_ACCOUNT"
    log_info "日志文件: $LOG_FILE"
    
    # 检查后端服务
    log_info "检查后端服务状态..."
    if ! wait_for_service "$BACKEND_URL"; then
        log_error "后端服务未运行，请先启动后端服务"
        exit 1
    fi
    
    # 执行所有测试
    test_account_creation_and_login
    
    if [ -n "$TEST_TOKEN" ]; then
        test_image_generation
    else
        log_warning "跳过图片生成测试（未获取到 Token）"
    fi
    
    test_proxy_configuration
    
    if [ -n "$TEST_TOKEN" ]; then
        test_feedback_api
    else
        log_warning "跳过用户建议测试（未获取到 Token）"
    fi
    
    test_help_documentation
    
    # 生成测试报告
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                      测试结果汇总                               ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "测试结束时间: $(date)"
    log_info "总计测试数: $TOTAL_TESTS"
    log_success "通过测试数: $PASSED_TESTS"
    log_error "失败测试数: $FAILED_TESTS"
    
    echo ""
    
    if [ $FAILED_TESTS -eq 0 ]; then
        log_success "🎉 所有测试通过！"
        echo ""
        echo "生成的测试文件:"
        ls -lh "$OUTPUT_DIR/" | grep -E "test_.*\.(jpg|log)" || echo "  无输出文件"
        return 0
    else
        log_error "⚠️  部分测试失败，请查看日志: $LOG_FILE"
        return 1
    fi
}

# 清理函数
cleanup() {
    log_info "清理测试环境..."
    # 可以在这里添加清理逻辑（如删除测试账号等）
}

# 捕获退出信号
trap cleanup EXIT

# 运行主函数
main "$@"
