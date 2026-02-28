# 错误信息改进方案

## 问题描述

用户报告的问题：
1. 后端返回错误：`"Server disconnected without sending a response."`
2. 但前端只显示通用错误信息：`"抱歉，发生了错误。请稍后重试。"`
3. 用户无法看到具体的错误原因

## 解决方案

采用 **HTTP Headers 传递错误信息** 的方式，确保即使 response body 为空或损坏，前端仍然能获取到具体的错误信息。

### 方案架构

```
后端异常 → 设置错误响应 headers → 前端 catch 错误 → 读取 headers → 显示具体错误信息
```

## 后端修改 (main.py)

### 1. 响应错误时添加 Headers

所有错误响应（JSONResponse）现在都包含以下 headers：

```python
headers={
    "X-Error-Code": error_code,           # 错误代码（如 TIMEOUT_ERROR）
    "X-Error-Message": error_message,     # 具体错误消息
    "X-Request-ID": request_id,           # 请求ID，便于追踪
    "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"  # CORS 暴露这些headers
}
```

### 2. 修改的端点

- `/api/banana-img` - Gemini 2.5 图片生成
- `/api/banana-img-pro` - Gemini 3 Pro 图片生成

### 3. 修改的异常处理

所有以下异常处理都已添加 headers：
- ✅ Handler 中的异常 (HANDLER_ERROR)
- ✅ 参数验证错误 (VALIDATION_ERROR)
- ✅ 请求超时 (TIMEOUT_ERROR)
- ✅ 内存错误 (MEMORY_ERROR)
- ✅ 通用异常 (INTERNAL_ERROR)

## 前端修改 (Working.jsx)

### 错误处理优先级

```
1. 从 HTTP headers 中读取错误信息 (X-Error-Message)
   ↓
2. 如果 headers 中没有，则从 response body 中读取
   ↓
3. 如果都没有，则使用默认错误消息
```

### 实现逻辑

```javascript
// 优先从HTTP headers中读取错误信息（在服务器断开连接时仍然可用）
if (error.response && error.response.headers) {
  const headerErrorMessage = error.response.headers['x-error-message']
  const headerErrorCode = error.response.headers['x-error-code']
  
  if (headerErrorMessage) {
    errorMessage = headerErrorMessage
  }
}

// 其次从response body中读取
if (!error.response?.headers?.['x-error-message'] && error.response?.data) {
  // 尝试解析 response body...
}
```

## 用户体验改进

### 原来的流程
```
后端错误: "Server disconnected without sending a response"
    ↓
前端收到空response
    ↓
显示通用错误: "抱歉，发生了错误。请稍后重试。"
    ↗
用户困惑：不知道什么错了
```

### 改进后的流程
```
后端错误: "Server disconnected without sending a response"
    ↓
响应 headers: X-Error-Message="Server disconnected without sending a response"
    ↓
前端从 headers 读取错误信息
    ↓
显示具体错误: "Server disconnected without sending a response"
    ↗
用户了解问题：知道具体错误原因
```

## 测试方法

### 1. 测试超时错误

**后端**：模拟超时异常
```python
# 在处理请求时
raise asyncio.TimeoutError("请求处理超时")
```

**预期前端显示**：
```
请求处理超时（超过10分钟）
```

### 2. 测试服务器错误

**后端**：模拟服务器错误
```python
# 在处理请求时
raise Exception("Server disconnected without sending a response")
```

**前端 console 会看到**：
```javascript
// 从 headers 中读取错误信息
{
  'x-error-code': 'INTERNAL_ERROR',
  'x-error-message': 'Server disconnected without sending a response'
}
```

**前端显示**：
```
Server disconnected without sending a response
```

### 3. 浏览器开发者工具验证

打开 Network 标签，查看响应：

**响应 Headers**：
```
x-error-code: INTERNAL_ERROR
x-error-message: Server disconnected without sending a response
x-request-id: 1771673985155
access-control-expose-headers: X-Error-Code, X-Error-Message, X-Request-ID
```

**响应 Body** (JSON)：
```json
{
  "success": false,
  "error_code": "INTERNAL_ERROR",
  "error_message": "Server disconnected without sending a response",
  "request_id": "1771673985155"
}
```

## 代码变更总结

### 后端文件修改
- `backend/main.py`
  - `/api/banana-img` 异常处理添加 headers
  - `/api/banana-img-pro` 异常处理添加 headers
  - 所有 JSONResponse 添加错误 headers

- `backend/handlers/banana_img_handler.py`
  - `ResponseBuilder.build_error_response()` 返回体中添加错误 headers 字段

### 前端文件修改
- `frontend/src/pages/Working.jsx`
  - `handleSubmit()` 中的 catch 块添加从 headers 读取错误信息的逻辑

## 兼容性说明

✅ **向后兼容**
- 旧的前端仍然能读取 response body 中的错误信息
- 新的前端优先读取 headers，然后降级到 body

✅ **浏览器兼容**
- 所有现代浏览器都支持 HTTP headers 和 CORS expose-headers
- 通过 `Access-Control-Expose-Headers` 暴露自定义 headers

## 监控和调试

### 1. 后端日志查看

```bash
# 查看请求 ID 和错误信息
grep "X-Error-Message\|error_code" backend.log
```

### 2. 前端 Console 输出

```javascript
// Working.jsx 中的调试日志
console.log('✅ 从HTTP headers中获取错误信息:', {
  'x-error-code': headerErrorCode,
  'x-error-message': headerErrorMessage
})
```

### 3. 关联追踪

使用 `x-request-id` 关联前后端日志：
- 前端：`error.response.headers['x-request-id']`
- 后端：日志中的 `[request_id]`

## 未来改进空间

1. ✅ 添加更多特定错误类型的 headers
2. ✅ 前端统一的错误处理中间件
3. ✅ 错误统计和上报机制
4. ✅ 多语言错误消息支持
