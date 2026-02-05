# 后端 Docker 部署指南

## Dockerfile 说明

### 关键配置

- **基础镜像**: `python:3.11-slim`（轻量级 Python 镜像）
- **工作目录**: `/app`
- **端口**: `8080`（Cloud Run 默认）
- **启动命令**: 使用 Gunicorn + Uvicorn Workers 运行 FastAPI

### 启动命令解析

```bash
gunicorn main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8080} \
  --timeout 120
```

- `main:app`: main.py 文件中的 `app` 变量（FastAPI 实例）
- `--workers 2`: 使用 2 个 worker 进程
- `--worker-class uvicorn.workers.UvicornWorker`: 使用 Uvicorn worker（支持异步）
- `--bind 0.0.0.0:${PORT:-8080}`: 绑定到所有网络接口，使用 PORT 环境变量（默认 8080）
- `--timeout 120`: 请求超时时间 120 秒（适合图片生成等耗时操作）

## 本地构建和测试

### 1. 构建镜像

```bash
cd backend
docker build -t guojie-backend:latest .
```

### 2. 运行容器

```bash
# 设置环境变量
export GOOGLE_API_KEY=your_api_key_here

# 运行容器
docker run -d \
  -p 8080:8080 \
  -e GOOGLE_API_KEY=$GOOGLE_API_KEY \
  -e PORT=8080 \
  --name guojie-backend \
  guojie-backend:latest
```

### 3. 测试

```bash
# 健康检查
curl http://localhost:8080/health

# API 文档
open http://localhost:8080/docs
```

## Cloud Run 部署

### 1. 部署命令

```bash
cd backend

gcloud run deploy backend \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --platform managed \
  --timeout 5m \
  --set-env-vars GOOGLE_API_KEY=your_api_key_here
```

### 2. 设置环境变量

在 Cloud Run 控制台或使用命令设置：

```bash
gcloud run services update backend \
  --region asia-southeast1 \
  --set-env-vars GOOGLE_API_KEY=your_api_key_here
```

### 3. 更新 CORS 配置

部署后，更新 `main.py` 中的 CORS 配置：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-domain.com",  # 前端域名
        "http://localhost:3000",  # 本地开发
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 性能优化

### Worker 数量

根据 Cloud Run 的 CPU 配置调整 worker 数量：

- **1 CPU**: `--workers 1`
- **2 CPU**: `--workers 2-4`
- **4+ CPU**: `--workers 4-8`

### 内存配置

图片生成需要较多内存，建议：

- **最小**: 512MB
- **推荐**: 1GB
- **大量图片**: 2GB+

### 超时设置

- **请求超时**: `--timeout 120`（Gunicorn）
- **Cloud Run 超时**: `--timeout 5m`（部署时设置）

## 环境变量

### 必需变量

- `GOOGLE_API_KEY`: Google API 密钥

### 可选变量（Vertex AI）

- `GOOGLE_APPLICATION_CREDENTIALS`: 服务账号密钥路径
- `GOOGLE_CLOUD_PROJECT_ID`: GCP 项目 ID
- `GOOGLE_CLOUD_LOCATION`: 区域（如 us-central1）

## 监控和日志

### 查看日志

```bash
gcloud run logs read backend --region asia-southeast1

# 实时日志
gcloud run logs tail backend --region asia-southeast1
```

### 健康检查

```bash
curl https://your-backend-url/health
```

## 常见问题

### 1. 端口错误

确保 Dockerfile 中 `EXPOSE 8080` 和启动命令使用 `${PORT:-8080}`

### 2. 环境变量未设置

使用 `--set-env-vars` 或 Cloud Run 控制台设置环境变量

### 3. 超时错误

增加超时时间：
- Gunicorn: `--timeout 120`
- Cloud Run: `--timeout 5m`

### 4. 内存不足

增加 Cloud Run 内存配置：
```bash
gcloud run services update backend \
  --region asia-southeast1 \
  --memory 1Gi
```

## 安全建议

1. ✅ 限制 CORS 源（生产环境）
2. ✅ 使用 Secret Manager 存储 API 密钥
3. ✅ 启用 Cloud Run 身份验证（如需要）
4. ✅ 定期更新依赖包
5. ✅ 监控异常请求和错误日志

