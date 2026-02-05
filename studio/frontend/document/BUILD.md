# 前端项目构建指南

## 构建步骤

### 1. 安装依赖（如果还没有安装）

```bash
cd frontend
npm install
```

### 2. 设置生产环境 API 地址（可选）

创建 `.env.production` 文件：

```bash
# 生产环境的 API 地址
VITE_API_BASE_URL=https://your-backend-api.com
```

如果不设置，将使用代码中的默认值 `http://localhost:8000`。

### 3. 执行构建

```bash
npm run build
```

或者使用构建脚本：

```bash
bash build.sh
```

### 4. 构建输出

构建完成后，所有文件将输出到 `dist/` 目录：

- `index.html` - 入口 HTML 文件
- `assets/` - 静态资源目录（JS、CSS、图片等）

### 5. 部署到 Web 服务器

将 `dist/` 目录中的所有文件上传到你的 Web 服务器。

#### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/dist;
    index index.html;

    # 单页应用路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理（可选，如果不想使用环境变量）
    location /api {
        proxy_pass http://your-backend-api.com;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Apache 配置示例

创建 `.htaccess` 文件放在 `dist/` 目录：

```apache
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteBase /
  RewriteRule ^index\.html$ - [L]
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteRule . /index.html [L]
</IfModule>
```

## 环境变量

### 开发环境

创建 `.env.development` 文件：

```
VITE_API_BASE_URL=http://localhost:8000
```

### 生产环境

创建 `.env.production` 文件：

```
VITE_API_BASE_URL=https://your-production-api.com
```

## 优化配置

构建配置已优化：

- 代码分割（Code Splitting）
- 资源压缩
- Tree Shaking
- 生产环境优化

## 注意事项

1. **CORS 配置**: 确保后端 API 配置了正确的 CORS 设置
2. **API 地址**: 确保生产环境的 API 地址可访问
3. **路由配置**: 单页应用需要服务器配置路由回退到 `index.html`
4. **静态资源路径**: 如果部署在子路径，需要配置 `base` 选项

