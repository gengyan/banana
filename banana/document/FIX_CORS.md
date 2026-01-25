# CORS 错误修复指南

## 问题描述

前端页面报错：`抱歉，发生了错误。请稍后重试。`
浏览器控制台显示：CORS error

## 原因分析

CORS (Cross-Origin Resource Sharing) 错误表示浏览器阻止了跨域请求。当前端（hello-1045502692494.asia-southeast1.run.app）尝试请求后端 API 时，后端必须明确允许这个来源。

## 修复步骤

### 1. 检查后端 CORS 配置

文件：`backend/main.py`

确保前端域名在 `origins` 列表中：

```python
origins = [
    "https://hello-1045502692494.asia-southeast1.run.app",  # 前端服务 URL
    "http://localhost:3000",  # 本地开发
    "http://localhost:8080",  # 本地开发（备用端口）
    "http://localhost:5173",  # Vite 默认开发端口
]
```

### 2. 重新部署后端

```bash
cd backend
gcloud run deploy backend \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --platform managed \
  --timeout 5m \
  --memory 1Gi
```

### 3. 验证修复

1. 等待部署完成（约 2-3 分钟）
2. 访问前端页面
3. 打开浏览器开发者工具（F12）
4. 查看 Network 标签，确认请求是否成功（状态码 200）
5. 查看 Console 标签，确认没有 CORS 错误

## 常见问题

### Q: 如果前端 URL 变化了怎么办？

A: 更新 `backend/main.py` 中的 `origins` 列表，添加新的前端 URL，然后重新部署后端。

### Q: 可以在生产环境使用 `origins = ["*"]` 吗？

A: 不推荐。如果设置了 `allow_credentials=True`，则不能使用 `["*"]`。应该明确列出允许的前端域名。

### Q: 如何查看实际的前端 URL？

A: 
```bash
gcloud run services describe hello --region asia-southeast1 --format="value(status.url)"
```

### Q: 如何查看实际的后端 URL？

A:
```bash
gcloud run services describe backend --region asia-southeast1 --format="value(status.url)"
```

## 调试方法

### 1. 检查后端 CORS 配置

```bash
grep -A 10 "origins = " backend/main.py
```

### 2. 检查前端 API 配置

查看浏览器控制台输出的 API 配置：
```javascript
console.log('🔧 API 配置:', {
  baseURL: API_BASE_URL,
  ...
});
```

### 3. 测试后端 API

```bash
# 测试后端是否正常
curl https://backend-1045502692494.asia-southeast1.run.app/

# 测试 CORS（从前端域名发起请求）
curl -H "Origin: https://hello-1045502692494.asia-southeast1.run.app" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://backend-1045502692494.asia-southeast1.run.app/api/process
```

## 验证清单

- [ ] 后端 CORS 配置包含前端域名
- [ ] 后端已重新部署
- [ ] 前端 API 配置正确（检查浏览器控制台）
- [ ] 浏览器控制台没有 CORS 错误
- [ ] API 请求返回 200 状态码

