# Google Cloud Run 部署指南

## 部署命令分析

### 命令位置
**应该在项目根目录执行**（`/Users/mac/Documents/ai/knowledgebase/banana/`）

### 命令解析

```bash
gcloud run deploy hello \
  --source frontend \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --platform managed
```

- `gcloud run deploy hello` - 部署名为 "hello" 的服务
- `--source frontend` - 从 `frontend/` 目录构建（相对路径，需要在项目根目录执行）
- `--region asia-southeast1` - 部署到新加坡区域
- `--allow-unauthenticated` - 允许未认证访问（公开访问）
- `--platform managed` - 使用完全托管的 Cloud Run

## 前置条件

### 1. 安装 gcloud CLI

```bash
# macOS
brew install google-cloud-sdk

# 或访问官网下载
# https://cloud.google.com/sdk/docs/install
```

### 2. 登录和配置

```bash
# 登录
gcloud auth login

# 设置项目
gcloud config set project YOUR_PROJECT_ID

# 启用 Cloud Run API
gcloud services enable run.googleapis.com
```

### 3. 检查项目结构

确保以下文件存在：
- ✅ `frontend/Dockerfile`
- ✅ `frontend/package.json`
- ✅ `frontend/nginx.conf`

## 部署步骤

### 方法1：使用部署脚本（推荐）

```bash
# 在项目根目录执行
chmod +x deploy-cloud-run.sh
bash deploy-cloud-run.sh
```

### 方法2：直接执行命令

```bash
# 在项目根目录执行
cd /Users/mac/Documents/ai/knowledgebase/banana

gcloud run deploy hello \
  --source frontend \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --platform managed
```

## 部署过程说明

1. **构建阶段**：
   - Cloud Run 会检测 `frontend/Dockerfile`
   - 在 Cloud Build 中执行多阶段构建
   - 生成包含 Nginx 和静态文件的镜像

2. **部署阶段**：
   - 将镜像推送到 Container Registry
   - 创建 Cloud Run 服务
   - 分配 HTTPS URL

3. **完成**：
   - 输出服务 URL（如：`https://hello-xxxxx-xx.a.run.app`）
   - 服务立即可用

## 部署后操作

### 查看服务信息

```bash
gcloud run services describe hello --region asia-southeast1
```

### 查看日志

```bash
gcloud run logs read hello --region asia-southeast1
```

### 更新部署

修改代码后，重新运行部署命令即可。

### 删除服务

```bash
gcloud run services delete hello --region asia-southeast1
```

## 配置环境变量

如果需要设置环境变量（如 API 地址）：

```bash
gcloud run deploy hello \
  --source frontend \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --platform managed \
  --set-env-vars VITE_API_BASE_URL=https://api.example.com
```

## 自定义域名

### 映射自定义域名

```bash
gcloud run domain-mappings create \
  --service hello \
  --domain your-domain.com \
  --region asia-southeast1
```

## 成本估算

Cloud Run 按使用量计费：
- **免费额度**：每月前 200 万次请求
- **定价**：按 CPU/内存使用时间计费
- **估算**：小型应用每月约 $5-20

## 常见问题

### 1. 构建失败：找不到 Dockerfile

**原因**：不在正确的目录执行

**解决**：确保在项目根目录执行，`frontend/` 是相对路径

### 2. 权限错误

**解决**：
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 3. API 未启用

**解决**：
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 4. 配额限制

**解决**：在 Google Cloud Console 申请增加配额

## 监控和调试

### 实时日志

```bash
gcloud run logs tail hello --region asia-southeast1
```

### 服务指标

在 Google Cloud Console 查看：
- 请求数
- 延迟
- 错误率
- CPU/内存使用

## 最佳实践

1. ✅ 使用部署脚本自动化
2. ✅ 设置环境变量管理配置
3. ✅ 配置监控和告警
4. ✅ 使用自定义域名
5. ✅ 定期查看日志和指标

