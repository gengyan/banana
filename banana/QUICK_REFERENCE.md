# 快速参考指南

## 什么被修改了？

### 问题
- 后端错误消息："Server disconnected without sending a response"
- 前端显示："抱歉，发生了错误。请稍后重试。"
- 用户无法看到具体错误原因

### 解决方案  
**通过 HTTP Headers 传递详细的错误信息**

---

## 核心改变

### ▶️ 后端 (`backend/main.py` 和 `backend/handlers/`)

**改变了什么**：所有错误响应（JSONResponse）现在包含这些 headers：

```python
headers={
    "X-Error-Code": "错误代码",           # 如 TIMEOUT_ERROR
    "X-Error-Message": "具体错误信息",    # 如 "请求处理超时"  
    "X-Request-ID": "请求ID",             # 便于追踪
    "Access-Control-Expose-Headers": "..."  # CORS 暴露这些 headers
}
```

**受影响的端点**：
- ✅ `/api/banana-img` - 所有异常处理
- ✅ `/api/banana-img-pro` - 所有异常处理
- ✅ 所有其他返回 JSONResponse 的错误回复

### ▶️ 前端 (`frontend/src/pages/Working.jsx`)

**改变了什么**：错误处理逻辑现在：

```javascript
1. 优先读取 HTTP headers 中的错误信息
   ↓ 如果 headers 为空
2. 从 response body 中读取错误信息
   ↓ 如果 body 也为空
3. 使用默认错误消息
```

---

## 用户体验对比

### 修改前
```
API 请求 → 后端错误 → 前端显示 "抱歉，发生了错误。请稍后重试。" ❌
                                    ↑
                                   用户很困惑
```

### 修改后
```
API 请求 → 后端错误 → 发送 X-Error-Message header
                            ↓
                   前端显示 "请求处理超时（10分钟）" ✅
                                    ↑
                              用户知道何时重试
```

---

## 工作原理

```
后端错误处理
    ↓
构建错误响应（JSON）
    ↓
设置 HTTP Headers：X-Error-Code, X-Error-Message
    ↓
通过 Access-Control-Expose-Headers 暴露给浏览器
    ↓
前端 catch 错误
    ↓
从 error.response.headers['x-error-message'] 读取
    ↓
显示给用户 ✓
```

---

## 关键文件

| 文件 | 修改内容 | 重要性 |
|------|---------|--------|
| `backend/main.py` | 为 JSONResponse 错误添加 headers | 🔴 核心 |
| `backend/handlers/banana_img_handler.py` | ResponseBuilder 返回 headers 字段 | 🔴 核心 |
| `frontend/src/pages/Working.jsx` | 从 headers 读取错误信息 | 🔴 核心 |
| `ERROR_MESSAGE_IMPROVEMENT.md` | 完整文档 | 🟡 参考 |
| `IMPLEMENTATION_SUMMARY.md` | 实施总结 | 🟡 参考 |
| `test-error-headers.sh` | 测试脚本 | 🟢 可选 |

---

## 测试方法（3 种）

### 方法 1：运行测试脚本
```bash
./test-error-headers.sh
```

### 方法 2：curl 测试
```bash
curl -i -X POST http://localhost:8000/api/banana-img \
  -H "Content-Type: application/json" \
  -d '{"message":""}'

# 查看响应 headers 中是否有：
# x-error-message: 消息内容不能为空
```

### 方法 3：浏览器开发者工具
1. F12 打开开发者工具
2. Network 标签
3. 发送请求
4. 点击请求查看 Response Headers
5. 查看是否有 `x-error-message` 等字段

---

## 错误信息流转示例

### 场景：用户提交空消息

```
前端提交：message=""
    ↓
后端验证：message 为空
    ↓
构建错误响应：
{
  "success": false,
  "error_code": "INVALID_REQUEST",
  "error_message": "消息内容不能为空"
}
    ↓
设置 Headers：
X-Error-Code: INVALID_REQUEST
X-Error-Message: 消息内容不能为空
    ↓
发送给前端
    ↓
前端 catch 错误
    ↓
从 headers 读取：
error.response.headers['x-error-message']
= "消息内容不能为空"
    ↓
显示给用户：
"消息内容不能为空" ✓
```

---

## 常见错误代码

| 错误代码 | 含义 | HTTP 状态 | 用户看到 |
|---------|------|----------|---------|
| INVALID_REQUEST | 参数验证失败 | 400 | "消息内容不能为空" |
| TIMEOUT_ERROR | 请求超时 | 504 | "请求处理超时(超过10分钟)" |
| HANDLER_ERROR | 处理器崩溃 | 500 | "请求处理器错误: ..." |
| INTERNAL_ERROR | 内部错误 | 500 | "内部服务器错误: ..." |
| MEMORY_ERROR | 内存不足 | 503 | "服务器内存不足，请稍后重试" |
| UNKNOWN_ERROR | 未知错误 | 500 | headers 中的消息 |

---

## 兼容性

✅ 旧前端 + 新后端：仍然能工作（通过 response body）  
✅ 新前端 + 旧后端：降级到 response body 处理  
✅ 新前端 + 新后端：最优体验（使用 headers）  
✅ CORS 兼容：通过 Access-Control-Expose-Headers 处理  

---

## 监控和调试

### 后端日志
```bash
# 查看带错误信息的日志
grep "error_code\|X-Error" backend.log
```

### 前端 Console
```javascript
// Working.jsx 中的日志
console.log('✅ 从HTTP headers中获取错误信息:', {
  'x-error-code': headerErrorCode,
  'x-error-message': headerErrorMessage
})
```

### 关联追踪
- 后端日志中有 `[request_id]`
- 前端 headers 中有 `X-Request-ID`
- 两者相同，可以关联查找

---

## 注意事项

⚠️ **请确保**：
1. 后端已重启，新代码已生效
2. 前端已刷新，新代码已加载
3. 浏览器开发者工具可以看到新的 response headers

💡 **提示**：
- 如果前端仍显示通用错误，检查 console 是否有错误信息
- 使用 curl 或 Postman 直接测试后端 API
- 查看浏览器 Network 标签验证 headers 是否返回

---

## 后续优化

🔮 未来可以考虑：
1. 在 `client.js` 中统一处理所有错误（中间件）
2. 前端错误分类显示（4xx vs 5xx）
3. 多语言错误消息支持
4. 错误上报和监控服务

---

## 关键代码片段

### 后端关键修改
```python
# 添加了这个到所有 JSONResponse 错误响应
headers={
    "X-Error-Code": error_code,
    "X-Error-Message": error_message,
    "X-Request-ID": request_id,
    "Access-Control-Expose-Headers": "X-Error-Code, X-Error-Message, X-Request-ID"
}
```

### 前端关键修改
```javascript
// 优先从 headers 读取
if (error.response?.headers?.['x-error-message']) {
  errorMessage = error.response.headers['x-error-message']
}

// 没有 headers 则从 body 读取
else if (error.response?.data?.error_message) {
  errorMessage = error.response.data.error_message
}
```

---

## 验证清单

完成以下检查确保改动正确：

- [ ] 后端 jython main.py 已修改
- [ ] 后端 handlers/banana_img_handler.py 已修改  
- [ ] 前端 pages/Working.jsx 已修改
- [ ] 后端已重启
- [ ] 前端已刷新
- [ ] 测试脚本运行成功
- [ ] curl 测试显示 X-Error-Message header
- [ ] 浏览器 Network 标签可见 headers
- [ ] 前端 console 显示从 headers 读取的日志

---

## 获取帮助

📖 详细信息查看：
- `ERROR_MESSAGE_IMPROVEMENT.md` - 完整的改进方案
- `IMPLEMENTATION_SUMMARY.md` - 详细的实施说明
- 后端 `backend/main.py` 中的注释
- 前端 `frontend/src/pages/Working.jsx` 中的注释
