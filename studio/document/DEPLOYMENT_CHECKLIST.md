# 部署前检查清单

## 关键问题分析

### ✅ 1. API地址配置
**问题：** 前端代码中硬编码了生产环境的API地址
**位置：** `frontend/src/config/api.js`
**当前配置：**
- 开发环境：`http://localhost:8000`
- 生产环境默认：`https://backend-1045502692494.asia-southeast1.run.app`
- 可通过环境变量 `VITE_API_BASE_URL` 覆盖

**建议：**
- 部署时设置环境变量 `VITE_API_BASE_URL` 指向实际的后端地址
- 或在构建时指定：`VITE_API_BASE_URL=https://your-backend.com npm run build`

---

### ⚠️ 2. CORS配置（重要）
**问题：** 后端CORS只允许 `localhost:3000` 和 `127.0.0.1:3000`
**位置：** `backend/main.py` 第75行
```python
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
```

**必须修改：**
```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://your-frontend-domain.com",  # 添加生产环境前端域名
    "https://www.your-frontend-domain.com",  # 如果有www版本
]
```

或者使用环境变量：
```python
import os
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
allow_origins=FRONTEND_ORIGINS
```

---

### ⚠️ 3. 环境变量配置
**后端需要配置（`backend/.env`）：**
- ✅ `GOOGLE_API_KEY` - Google API密钥（必需）
- ✅ `HTTP_PROXY` / `HTTPS_PROXY` - 代理配置（如果需要）
- ✅ `DISABLE_PROXY` - 是否禁用代理
- ✅ `ALIPAY_APP_ID` - 支付宝应用ID
- ✅ `ALIPAY_PRIVATE_KEY` - 支付宝私钥
- ✅ `ALIPAY_PUBLIC_KEY` - 支付宝公钥
- ✅ `ALIPAY_SANDBOX` - 是否使用沙箱环境
- ✅ `ALIPAY_NOTIFY_URL` - 支付回调地址（需要公网可访问）
- ✅ `ALIPAY_RETURN_URL` - 支付完成跳转地址（前端地址）

**前端构建时需要配置：**
- ✅ `VITE_API_BASE_URL` - 后端API地址

---

### ✅ 4. IndexedDB存储
**状态：** ✅ 无问题
**说明：** IndexedDB是浏览器端的存储，部署后仍然在用户浏览器中工作，无需服务器配置。

---

### ⚠️ 5. 静态资源路径
**问题：** 前端使用了相对路径引用静态资源（如图片）
**检查位置：**
- `/public/alipay.jpg` - 支付二维码
- `/public/ordernum.jpg` - 订单号示例图
- `/public/tempimgs/` - 模板图片
- `/public/icon.png` - 应用图标

**说明：** 使用相对路径（`/alipay.jpg`）是正确的，部署到根目录或子目录都可以，但需要确认Nginx配置正确。

---

### ⚠️ 6. SPA路由配置（Nginx）
**问题：** React Router使用客户端路由，需要Nginx配置重定向到 `index.html`
**检查：** `frontend/nginx.conf` 中是否配置了 `try_files` 指令

**必需配置：**
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

---

### ⚠️ 7. HTTPS/HTTP混合内容
**问题：** 如果前端使用HTTPS，但后端API使用HTTP，会出现混合内容错误
**建议：** 
- 前端和后端都使用HTTPS
- 或者都使用HTTP（不推荐生产环境）

---

### ⚠️ 8. 支付宝回调地址
**问题：** 支付宝回调URL需要公网可访问
**当前配置（`backend/env.example`）：**
```
ALIPAY_NOTIFY_URL=http://localhost:8000/api/payment/notify
ALIPAY_RETURN_URL=http://localhost:3000/payment/success
```

**部署时必须修改为：**
```
ALIPAY_NOTIFY_URL=https://your-backend-domain.com/api/payment/notify
ALIPAY_RETURN_URL=https://your-frontend-domain.com/payment/success
```

---

### ✅ 9. 构建配置
**状态：** ✅ 配置正确
**说明：** 
- Vite构建配置正确
- 输出目录：`dist`
- 资源哈希：已配置，支持缓存破坏

---

### ⚠️ 10. 代理配置
**问题：** 后端代码中配置了代理（如果需要访问Google API）
**位置：** `backend/main.py` 第28-46行
**说明：** 
- 如果服务器可以直接访问Google API，设置 `DISABLE_PROXY=true`
- 如果需要代理，配置 `HTTP_PROXY` 和 `HTTPS_PROXY`

---

## 部署步骤建议

### 后端部署
1. ✅ 复制 `.env` 文件到服务器（或使用环境变量）
2. ⚠️ **修改CORS配置**，添加前端域名
3. ⚠️ **修改支付宝回调URL**
4. ⚠️ **配置代理**（如果需要）
5. 安装依赖：`pip install -r requirements.txt`
6. 启动服务：`python main.py` 或使用 gunicorn/uvicorn

### 前端部署
1. ✅ 设置环境变量：`VITE_API_BASE_URL=https://your-backend.com`
2. ✅ 构建：`npm run build`
3. ⚠️ **配置Nginx**，确保SPA路由正确
4. ✅ 部署 `dist` 目录到Web服务器

---

## 必须修改的项目（部署前）

1. **后端CORS配置** - 添加前端生产域名
2. **支付宝回调URL** - 修改为生产环境地址
3. **前端API地址** - 通过环境变量配置
4. **Nginx配置** - 确保SPA路由正确

---

## 推荐部署架构

### 方案1：前后端分离部署
- 前端：Nginx（静态文件）+ CDN（可选）
- 后端：Python + FastAPI + Uvicorn/Gunicorn
- 优势：可独立扩展，CDN加速

### 方案2：容器化部署
- 前端：Docker + Nginx
- 后端：Docker + Python
- 优势：环境一致，易于管理

### 方案3：云服务部署
- 前端：Google Cloud Run / AWS S3 + CloudFront
- 后端：Google Cloud Run / AWS Lambda
- 优势：自动扩缩容，高可用

