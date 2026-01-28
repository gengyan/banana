#!/bin/bash

# 本地调试脚本：带代理启动前后端服务
# 用法：./restart-with-proxy.sh
# 代理配置：127.0.0.1:29290

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "=========================================="
echo "🔄 重启前后端服务（带本地代理）"
echo "=========================================="
echo ""

# 代理配置（本地调试）
export HTTP_PROXY=http://127.0.0.1:29290
export HTTPS_PROXY=http://127.0.0.1:29290
export NO_PROXY=localhost,127.0.0.1,127.0.0.1:3000,127.0.0.1:8080
export DISABLE_PROXY=false

echo "📡 代理配置已应用："
echo "   HTTP_PROXY: $HTTP_PROXY"
echo "   HTTPS_PROXY: $HTTPS_PROXY"
echo "   NO_PROXY: $NO_PROXY"
echo "   DISABLE_PROXY: $DISABLE_PROXY"
echo ""

# 函数：停止服务
stop_services() {
    echo "🛑 停止现有服务..."
    
    # 停止前端服务（端口 3000）
    if lsof -ti:3000 > /dev/null 2>&1; then
        echo "   停止前端服务（端口 3000）..."
        lsof -ti:3000 | xargs kill -9 2>/dev/null
        sleep 1
    fi
    
    # 停止后端服务（端口 8080）
    if lsof -ti:8080 > /dev/null 2>&1; then
        echo "   停止后端服务（端口 8080）..."
        lsof -ti:8080 | xargs kill -9 2>/dev/null
        sleep 1
    fi
    
    # 停止所有相关的 node 和 python 进程（更彻底）
    pkill -f "vite" 2>/dev/null
    pkill -f "python.*main.py" 2>/dev/null
    
    sleep 2
    echo "✅ 服务已停止"
    echo ""
}

# 函数：启动后端（带代理）
start_backend() {
    echo "🚀 启动后端服务（带代理）..."
    cd "$SCRIPT_DIR/backend" || exit 1
    
    # 检查环境变量
    if [ ! -f .env ]; then
        echo "❌ .env 文件不存在"
        echo "请创建 .env 文件并设置 GOOGLE_API_KEY"
        return 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo "📦 创建虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install -q -r requirements.txt 2>/dev/null || pip install -r requirements.txt
    
    echo "✅ 后端环境检查通过"
    echo "📝 启动后端服务（端口 8080，代理已启用）..."
    echo ""
    
    # 启动后端：显式传入代理环境变量，输出到终端和日志文件
    HTTP_PROXY=$HTTP_PROXY \
    HTTPS_PROXY=$HTTPS_PROXY \
    NO_PROXY=$NO_PROXY \
    DISABLE_PROXY=$DISABLE_PROXY \
    PORT=8080 \
    nohup python3 main.py > "$SCRIPT_DIR/backend.log" 2>&1 &
    
    BACKEND_PID=$!
    cd "$SCRIPT_DIR" || exit 1
    
    # 等待后端启动
    sleep 3
    
    # 检查后端是否启动成功
    if ps -p $BACKEND_PID > /dev/null; then
        echo "✅ 后端服务已启动（PID: $BACKEND_PID）"
        echo "📋 后端日志文件: $SCRIPT_DIR/backend.log"
        echo ""
        return 0
    else
        echo "❌ 后端服务启动失败"
        cat "$SCRIPT_DIR/backend.log" 2>/dev/null || echo "   无法读取日志文件"
        return 1
    fi
}

# 函数：启动前端
start_frontend() {
    echo "🚀 启动前端服务..."
    cd "$SCRIPT_DIR/frontend" || exit 1
    
    # 检查依赖
    if [ ! -d "node_modules" ]; then
        echo "📦 安装前端依赖..."
        npm install --legacy-peer-deps -q
    fi
    
    echo "✅ 前端环境检查通过"
    echo "📝 启动前端服务（端口 3000）..."
    echo ""
    
    # 启动前端（后台运行）
    nohup npm run dev > "$SCRIPT_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    cd "$SCRIPT_DIR" || exit 1
    
    # 等待前端启动
    sleep 5
    
    # 检查前端是否启动成功
    if ps -p $FRONTEND_PID > /dev/null; then
        echo "✅ 前端服务已启动（PID: $FRONTEND_PID）"
        echo "📋 前端日志文件: $SCRIPT_DIR/frontend.log"
        echo ""
        return 0
    else
        echo "❌ 前端服务启动失败"
        cat "$SCRIPT_DIR/frontend.log" 2>/dev/null || echo "   无法读取日志文件"
        return 1
    fi
}

# 主流程
stop_services
start_backend || exit 1
start_frontend || exit 1

echo "=========================================="
echo "✅ 服务启动完成"
echo "=========================================="
echo ""
echo "📍 前端访问地址："
echo "   http://localhost:3000"
echo ""
echo "📍 后端访问地址："
echo "   http://localhost:8080"
echo ""
echo "📋 查看日志："
echo "   后端: tail -f $SCRIPT_DIR/backend.log"
echo "   前端: tail -f $SCRIPT_DIR/frontend.log"
echo ""
echo "🛑 停止服务："
echo "   pkill -f 'python.*main.py' && pkill -f 'vite'"
echo ""
