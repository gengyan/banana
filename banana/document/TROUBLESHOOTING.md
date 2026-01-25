# 前后端连接问题排查指南

## 问题现象

前端页面显示："抱歉，发生了错误。请稍后重试。"

## 快速排查步骤

### 1. 运行排查脚本

```bash
bash troubleshoot.sh
```

这个脚本会检查：
- 后端服务状态
- 后端健康检查
- CORS 配置
- 前端配置
- 后端日志

### 2. 运行修复脚本（自动修复）

```bash
bash troubleshoot.sh
```

这个脚本会：
- 自动更新后端 CORS 配置（添加前端 URL）
- 自动更新前端配置文件（使用正确的后端地址）

### 3. 重新部署

```bash
# 重新部署后端（更新 CORS）
bash deploy-backend.sh

# 重新部署前端（使用新配置）
bash redeploy-frontend.sh
```

## 常见问题及解决方案

### 问题1: CORS 错误

**现象**：浏览器控制台显示 CORS 相关错误

**原因**：后端未允许前端域名访问

**解决**：

1. 获取前端 URL：
   ```bash
   gcloud run services describe hello --region asia-southeast1 --format="value(status.url)"
   ```

2. 更新 `backend/main.py` 中的 CORS 配置：
   ```python
   origins = [
       "https://your-frontend-url.run.app",  # 添加前端 URL
       "http://localhost:3000",
   ]
   ```

3. 重新部署后端：
   ```bash
   bash deploy-backend.sh
   ```

### 问题2: API 地址配置错误

**现象**：Network 标签页显示 404 或连接失败

**原因**：前端配置的后端地址不正确

**解决**：

1. 获取后端 URL：
   ```bash
   gcloud run services describe backend --region asia-southeast1 --format="value(status.url)"
   ```

2. 更新 `frontend/.env.production`：
   ```env
   VITE_API_BASE_URL=https://backend-xxx.asia-southeast1.run.app
   ```

3. 重新构建和部署前端：
   ```bash
   bash redeploy-frontend.sh
   ```

### 问题3: 后端服务错误

**现象**：后端返回 500 错误

**原因**：后端代码错误或环境变量未设置

**解决**：

1. 查看后端日志：
   ```bash
   gcloud run logs read backend --region asia-southeast1 --limit 50
   ```

2. 检查环境变量：
   ```bash
   gcloud run services describe backend --region asia-southeast1 --format="value(spec.template.spec.containers[0].env)"
   ```

3. 确保 `GOOGLE_API_KEY` 已设置

### 问题4: 网络连接问题

**现象**：无法连接到后端

**解决**：

1. 测试后端健康检查：
   ```bash
   BACKEND_URL=$(gcloud run services describe backend --region asia-southeast1 --format="value(status.url)")
   curl $BACKEND_URL/health
   ```

2. 检查服务状态：
   ```bash
   gcloud run services list --region asia-southeast1
   ```

## 手动排查步骤

### 1. 检查浏览器控制台

1. 打开前端页面
2. 按 F12 打开开发者工具
3. 查看 **Console** 标签页的错误信息
4. 查看 **Network** 标签页的请求状态

### 2. 检查后端日志

```bash
# 查看最近的日志
gcloud run logs read backend --region asia-southeast1 --limit 20

# 实时查看日志
gcloud run logs tail backend --region asia-southeast1
```

### 3. 测试后端 API

```bash
# 获取后端 URL
BACKEND_URL=$(gcloud run services describe backend --region asia-southeast1 --format="value(status.url)")

# 测试健康检查
curl $BACKEND_URL/health

# 测试 API 文档
curl $BACKEND_URL/docs

# 测试 API 端点
curl -X POST $BACKEND_URL/api/chat \
  -H "Content-Type: application/json" \
  -H "Origin: https://your-frontend-url.run.app" \
  -d '{"message":"测试","mode":"chat","history":[]}'
```

### 4. 检查 CORS 配置

确认 `backend/main.py` 中的 `origins` 列表包含前端 URL：

```python
origins = [
    "https://hello-xxx.asia-southeast1.run.app",  # 前端 URL
    "http://localhost:3000",
]
```

### 5. 检查前端配置

确认 `frontend/.env.production` 中的后端地址正确：

```env
VITE_API_BASE_URL=https://backend-xxx.asia-southeast1.run.app
```

## 验证修复

修复后，验证步骤：

1. ✅ 后端健康检查返回 200
2. ✅ 前端可以访问后端 API
3. ✅ 浏览器控制台没有 CORS 错误
4. ✅ 功能测试正常

## 获取帮助

如果问题仍未解决：

1. 运行完整排查脚本：`bash troubleshoot.sh`
2. 查看后端日志找出具体错误
3. 检查浏览器控制台的详细错误信息
4. 确认两个服务都在同一区域（asia-southeast1）

