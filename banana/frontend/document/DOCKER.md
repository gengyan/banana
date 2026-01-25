# Docker 构建和部署指南

## 构建 Docker 镜像

### 基本构建

```bash
cd frontend
docker build -t guojie-frontend:latest .
```

### 带标签构建

```bash
docker build -t guojie-frontend:v1.0.0 -t guojie-frontend:latest .
```

## 运行容器

### 基本运行

```bash
docker run -d -p 8080:80 --name guojie-frontend guojie-frontend:latest
```

### 使用环境变量（如果需要）

```bash
docker run -d -p 8080:80 \
  -e VITE_API_BASE_URL=https://api.example.com \
  --name guojie-frontend \
  guojie-frontend:latest
```

## Docker Compose 示例

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:80"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
```

运行：

```bash
docker-compose up -d
```

## 多阶段构建说明

### 第一阶段：构建阶段 (builder)
- 使用 `node:20-alpine` 镜像
- 安装所有依赖（包括 devDependencies）
- 执行 `npm run build` 生成静态文件

### 第二阶段：运行阶段 (final)
- 使用 `nginx:stable-alpine` 镜像（轻量级）
- 只包含构建好的静态文件
- 最终镜像大小约 20-30MB

## 优化说明

### 1. 使用 .dockerignore
排除不需要的文件，减少构建上下文大小：
- node_modules
- dist
- 文档和脚本文件
- Git 文件

### 2. 使用 npm ci
- 更可靠，完全按照 package-lock.json 安装
- 更快，跳过依赖解析
- 适合 CI/CD 环境

### 3. 多阶段构建
- 最终镜像只包含运行所需的文件
- 大幅减小镜像体积
- 提高安全性（不包含构建工具）

### 4. 健康检查
- 自动检测容器健康状态
- 便于监控和自动恢复

## 生产环境部署

### 1. 构建生产镜像

```bash
docker build -t registry.example.com/guojie-frontend:v1.0.0 .
```

### 2. 推送到镜像仓库

```bash
docker push registry.example.com/guojie-frontend:v1.0.0
```

### 3. 在服务器上拉取并运行

```bash
docker pull registry.example.com/guojie-frontend:v1.0.0
docker run -d -p 80:80 --name guojie-frontend registry.example.com/guojie-frontend:v1.0.0
```

## 常见问题

### 1. 构建失败：找不到 nginx.conf

确保 `nginx.conf` 文件存在于 `frontend/` 目录下。

### 2. 路由 404 错误

确保 `nginx.conf` 中配置了 SPA 路由支持：
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

### 3. API 请求失败

前端代码中使用环境变量 `VITE_API_BASE_URL`，需要在构建时设置：
```bash
docker build --build-arg VITE_API_BASE_URL=https://api.example.com -t guojie-frontend .
```

或者在运行时通过反向代理处理 API 请求。

## 镜像大小优化

当前优化后的镜像大小：
- 构建阶段：~500MB（不包含在最终镜像中）
- 最终镜像：~20-30MB（仅包含 Nginx 和静态文件）

## 安全检查清单

- ✅ 使用非 root 用户运行（Nginx 默认）
- ✅ 最小化镜像（Alpine Linux）
- ✅ 排除敏感文件（.dockerignore）
- ✅ 健康检查配置
- ✅ 安全头设置（nginx.conf）

