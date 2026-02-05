# 前端环境配置指南

## 配置文件说明

前端使用环境变量文件来配置后端 API 地址。Vite 会根据当前模式（development/production）自动加载对应的配置文件。

## 配置文件

### `.env.development` - 开发环境
用于本地开发时的配置。

```env
VITE_API_BASE_URL=http://localhost:8000
```

### `.env.production` - 生产环境
用于生产构建时的配置。

```env
VITE_API_BASE_URL=https://backend-1045502692494.asia-southeast1.run.app
```

### `.env.example` - 配置示例
配置文件的模板，不会被提交到 Git。

## 使用方法

### 1. 开发环境

开发时，前端会自动使用 `.env.development` 中的配置：

```bash
npm run dev
```

### 2. 生产环境

构建生产版本时，前端会自动使用 `.env.production` 中的配置：

```bash
npm run build
```

### 3. 自定义配置

如果需要临时使用不同的后端地址，可以创建 `.env.local` 文件（优先级最高）：

```env
VITE_API_BASE_URL=https://your-custom-backend-url.com
```

## 环境变量优先级

Vite 加载环境变量的优先级（从高到低）：

1. `.env.local` - 本地覆盖（所有环境）
2. `.env.[mode].local` - 本地覆盖（特定环境）
3. `.env.[mode]` - 环境特定配置
4. `.env` - 默认配置

## 当前配置

### 开发环境
- **后端地址**: `http://localhost:8000`（本地后端）

### 生产环境
- **后端地址**: `https://backend-1045502692494.asia-southeast1.run.app`（Cloud Run 后端）

## 更新后端地址

### 方法1：修改配置文件

编辑对应的 `.env` 文件：

```bash
# 开发环境
vim frontend/.env.development

# 生产环境
vim frontend/.env.production
```

### 方法2：使用环境变量（临时）

```bash
# 开发时
VITE_API_BASE_URL=https://custom-backend.com npm run dev

# 构建时
VITE_API_BASE_URL=https://custom-backend.com npm run build
```

### 方法3：Cloud Run 部署时设置

```bash
gcloud run deploy hello \
  --source frontend \
  --region asia-southeast1 \
  --set-env-vars VITE_API_BASE_URL=https://backend-1045502692494.asia-southeast1.run.app \
  --allow-unauthenticated \
  --platform managed
```

## 验证配置

### 检查当前配置

在浏览器控制台中查看：

```javascript
console.log('API Base URL:', import.meta.env.VITE_API_BASE_URL);
```

### 测试 API 连接

打开浏览器开发者工具，查看网络请求，确认请求发送到正确的后端地址。

## 注意事项

1. ✅ `.env` 文件已添加到 `.gitignore`，不会被提交到 Git
2. ✅ `.env.example` 作为模板保留在仓库中
3. ✅ 环境变量必须以 `VITE_` 开头才能在客户端代码中访问
4. ✅ 修改 `.env` 文件后需要重启开发服务器

## 故障排查

### 问题1：环境变量未生效

**解决**：
- 确认变量名以 `VITE_` 开头
- 重启开发服务器
- 检查文件名是否正确（`.env.development` 或 `.env.production`）

### 问题2：构建后仍使用旧地址

**解决**：
- 确认 `.env.production` 文件存在且配置正确
- 重新执行 `npm run build`
- 清除构建缓存：`rm -rf dist && npm run build`

### 问题3：开发环境无法连接后端

**解决**：
- 确认本地后端服务已启动（`http://localhost:8000`）
- 检查 `.env.development` 配置
- 查看浏览器控制台的错误信息

