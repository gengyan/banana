# ==================================
# 第一阶段：构建 (Build Stage)
# 职责：安装依赖，执行 npm run build 生成静态文件
# ==================================
FROM node:20-alpine AS builder

# 设置容器内的工作目录
WORKDIR /app

# 拷贝依赖文件并安装
# 使用 npm ci 而不是 npm install，更可靠且更快
# 注意：不利用 Docker 缓存机制，确保每次都是全新安装
COPY package.json package-lock.json ./
RUN npm ci --only=production=false --no-audit --no-fund && \
    npm cache clean --force && \
    rm -rf /tmp/* /var/tmp/*

# 拷贝所有源代码（.dockerignore 会排除不需要的文件）
COPY . .
# 确保更新脚本可执行
RUN chmod +x update-build-time.sh 2>/dev/null || true

# 核心：执行构建，生成静态文件
# 确保您的 package.json 中有 "build": "vite build"
# 清理所有可能的缓存，确保每次都是全新构建
RUN rm -rf node_modules/.vite /app/dist /app/.vite ~/.npm ~/.cache && \
    npm run build && \
    echo "=== 构建完成，检查生成的文件 ===" && \
    ls -la /app/dist/assets/*.js 2>/dev/null | head -5

# 验证构建结果（调试用）
RUN echo "=== 构建结果验证 ===" && \
    ls -la /app/dist/ && \
    echo "=== index.html 中的 JS 文件引用 ===" && \
    cat /app/dist/index.html | grep -E '\.js' | head -5 && \
    echo "=== 检查文件名哈希是否变化 ===" && \
    ls -la /app/dist/assets/ | grep -E '\.js$' | head -5

# ==================================
# 第二阶段：运行 (Serve Stage)
# 职责：使用轻量级的 Nginx 容器服务第一阶段生成的静态文件
# ==================================
FROM nginx:stable-alpine AS final

# 安装 curl 用于健康检查
RUN apk add --no-cache curl

# 1. 拷贝 Nginx 配置文件（直接监听 8080 端口）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 2. 核心：从构建阶段拷贝编译好的静态文件
# /app/dist 是 Vite build 的默认输出目录
# 确保使用 --from=builder 从构建阶段拷贝最新的构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 验证文件是否正确拷贝（调试用）
RUN echo "=== 验证拷贝的文件 ===" && \
    ls -la /usr/share/nginx/html/ && \
    echo "=== index.html 中的 JS 引用 ===" && \
    cat /usr/share/nginx/html/index.html | grep -E '\.js' | head -3

# 4. 创建非 root 用户（安全最佳实践）
# Nginx alpine 镜像默认使用 nginx 用户，但确保权限正确
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# 5. 容器监听端口（Cloud Run 使用 PORT 环境变量，默认 8080）
EXPOSE 8080

# 6. 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 7. 启动 Nginx 服务器
CMD ["nginx", "-g", "daemon off;"]

