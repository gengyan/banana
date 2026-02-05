# 自定义服务器部署指南

服务器地址：`120.55.181.23` | 用户：`root`

## 📋 快速开始

### 一键部署前端

```bash
cd /Users/mac/Documents/ai/knowledgebase/bananas/banana
./deploy-frontend-server.sh
```

脚本会自动：
1. 检查 Node.js 依赖
2. 编译前端代码（生成 dist 目录）
3. 备份旧版本
4. 上传到服务器：`/data/wwwroot/default/guojie`
5. 设置文件权限

> **注意**：首次运行时需要输入一次服务器密码。密码不会显示，输入后按 Enter。

---

## 🔧 前提条件

### 1. 服务器环境要求

在服务器上执行以下命令确保环境就绪：

```bash
ssh root@120.55.181.23

# 1. 创建部署目录
mkdir -p /data/wwwroot/default/guojie

# 2. 确保 Nginx 已安装
apt update && apt install -y nginx

# 3. 启动 Nginx
systemctl start nginx
systemctl enable nginx
```

### 2. 本地环境要求

```bash
# Node.js 版本（在项目根目录执行）
node --version  # 需要 v16+

# npm 版本
npm --version   # 需要 v7+
```

---

## 📁 前端部署配置

### 1. Nginx 配置（已提供）

文件位置：`frontend/nginx.server.conf`

在服务器上配置：

```bash
ssh root@120.55.181.23

# 复制 Nginx 配置文件
scp /Users/mac/Documents/ai/knowledgebase/bananas/banana/frontend/nginx.server.conf \
    root@120.55.181.23:/etc/nginx/conf.d/guojie.conf

# 验证配置
nginx -t

# 重新加载 Nginx
systemctl reload nginx
```

### 关键配置说明

```nginx
server {
    listen 80;
    server_name gj.emaos.top;           # ⚠️ 修改为你的域名
    root /data/wwwroot/default/guojie;  # 部署目录（必须和部署脚本一致）
    
    # 关键：SPA 路由支持（所有路由回退到 index.html）
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # 长期缓存静态资源（webpack hash 文件名）
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
}
```

---

## 🚀 后端部署配置

### 1. 检查后端部署到 Cloud Run

后端已部署到 Google Cloud Run，检查状态：

```bash
gcloud run services list --region=asia-southeast1
```

获取后端地址：

```bash
BACKEND_URL=$(gcloud run services describe backend --region=asia-southeast1 --format='value(status.url)')
echo "后端地址: $BACKEND_URL"
```

### 2. 更新 CORS 配置

**重要**：后端 CORS 必须允许前端域名

文件：`backend/main.py` 第 75 行

```python
# ❌ 错误 - 只允许本地
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]

# ✅ 正确 - 添加生产域名
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://gj.emaos.top",           # 前端域名
    "https://www.gj.emaos.top",       # www 版本
    "http://120.55.181.23",           # IP 地址（可选）
]
```

修改后重新部署后端：

```bash
./redeploy-backend.sh
```

---

## 🔌 前端 API 配置

文件：`frontend/src/config/api.js`

前端需要知道后端地址。部署时设置环境变量：

```bash
# 本地开发（使用本地后端）
npm run dev

# 构建生产版本（使用远程后端）
VITE_API_BASE_URL=https://backend-xxx.asia-southeast1.run.app npm run build

# 部署脚本会自动处理（推荐）
./deploy-frontend-server.sh
```

---

## 📊 部署流程详解

### 步骤 1：准备前端

```bash
cd frontend

# 检查依赖
npm install

# 本地测试（可选）
npm run build
```

### 步骤 2：执行部署脚本

```bash
cd /Users/mac/Documents/ai/knowledgebase/bananas/banana
./deploy-frontend-server.sh
```

脚本输出示例：

```
==========================================
🚀 前端部署脚本（简化版）
==========================================

📋 部署配置:
  服务器: root@120.55.181.23
  目标目录: /data/wwwroot/default/guojie

📦 步骤 1: 检查依赖
✅ 依赖检查完成

🔨 步骤 2: 构建生产版本
✅ 构建成功！大小: 2.5M

🚀 步骤 3: 部署到服务器
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  请输入服务器密码（只需输入一次）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ SSH 连接已建立
✅ 备份完成: /data/wwwroot/default/guojie_backup_20260204_143022
✅ 文件上传成功
```

### 步骤 3：验证部署

部署完成后访问：

```
https://gj.emaos.top        # 使用域名访问
或
http://120.55.181.23        # 使用 IP 访问
```

---

## 🐛 常见问题排查

### 问题 1：Nginx 404 错误

**症状**：访问网站出现 404 Not Found

**原因**：Nginx 配置中 SPA 路由回退配置不正确

**解决**：

```bash
ssh root@120.55.181.23

# 检查 Nginx 配置
cat /etc/nginx/conf.d/guojie.conf

# 确保包含以下内容
# location / {
#     try_files $uri $uri/ /index.html;
# }

# 验证配置
nginx -t

# 重新加载
systemctl reload nginx
```

### 问题 2：CORS 错误

**症状**：浏览器控制台出现 CORS 错误

**原因**：后端没有允许前端域名

**解决**：

```bash
# 1. 修改后端代码
vi backend/main.py  # 第 75 行

# 2. 重新部署后端
./redeploy-backend.sh

# 3. 清除浏览器缓存后重试
```

### 问题 3：文件上传失败

**症状**：部署脚本提示 SSH 连接失败

**解决**：

```bash
# 1. 测试 SSH 连接
ssh -v root@120.55.181.23

# 2. 检查密码和网络
# 3. 如果网络有代理，临时禁用：
unset HTTP_PROXY HTTPS_PROXY

# 重试部署
./deploy-frontend-server.sh
```

### 问题 4：访问速度慢

**原因**：服务器到用户的网络距离或服务器配置

**优化**：

```bash
ssh root@120.55.181.23

# 启用 Gzip 压缩
sed -i 's/# gzip on;/gzip on;/' /etc/nginx/nginx.conf

# 启用缓存
systemctl reload nginx
```

---

## 📈 监控和维护

### 查看部署日志

```bash
ssh root@120.55.181.23

# Nginx 访问日志
tail -f /var/log/nginx/guojie_access.log

# Nginx 错误日志
tail -f /var/log/nginx/guojie_error.log
```

### 查看部署文件

```bash
ssh root@120.55.181.23

# 列出部署目录
ls -la /data/wwwroot/default/guojie/

# 查看备份
ls -la /data/wwwroot/default/ | grep backup
```

### 恢复旧版本

```bash
ssh root@120.55.181.23

# 列出所有备份
ls -la /data/wwwroot/default/ | grep guojie_backup

# 恢复特定备份
BACKUP_DIR="/data/wwwroot/default/guojie_backup_20260204_143022"
rm -rf /data/wwwroot/default/guojie
cp -r $BACKUP_DIR /data/wwwroot/default/guojie

# 重新加载 Nginx
systemctl reload nginx
```

---

## 🔐 安全建议

### 1. SSL/HTTPS 配置

使用 Let's Encrypt 免费证书：

```bash
ssh root@120.55.181.23

# 安装 Certbot
apt install -y certbot python3-certbot-nginx

# 获取证书
certbot certonly --nginx -d gj.emaos.top -d www.gj.emaos.top

# 自动更新证书
certbot renew --quiet --no-eff-email --no-eff-e
```

然后更新 Nginx 配置文件 `/etc/nginx/conf.d/guojie.conf`：

```nginx
server {
    listen 443 ssl http2;
    server_name gj.emaos.top www.gj.emaos.top;
    
    ssl_certificate /etc/letsencrypt/live/gj.emaos.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gj.emaos.top/privkey.pem;
    
    # ... 其他配置
}

# 重定向 HTTP 到 HTTPS
server {
    listen 80;
    server_name gj.emaos.top www.gj.emaos.top;
    return 301 https://$server_name$request_uri;
}
```

### 2. 防火墙配置

```bash
ssh root@120.55.181.23

# 允许 HTTP 和 HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# 限制 SSH 端口（可选）
ufw allow 22/tcp
ufw enable
```

---

## 📞 完整部署清单

- [ ] 服务器已创建目录 `/data/wwwroot/default/guojie`
- [ ] Nginx 已安装并运行
- [ ] Nginx 配置文件已复制到 `/etc/nginx/conf.d/guojie.conf`
- [ ] 后端 CORS 已配置允许前端域名
- [ ] 后端已部署到 Cloud Run
- [ ] 前端 API 配置正确
- [ ] 本地前端依赖已安装（`npm install`）
- [ ] SSH 连接测试正常（`ssh root@120.55.181.23`）
- [ ] 执行部署脚本 `./deploy-frontend-server.sh`
- [ ] 验证访问 `https://gj.emaos.top`
- [ ] 检查浏览器控制台无 CORS 错误
- [ ] 检查 Nginx 日志无错误

---

## 🆘 需要帮助？

常用命令速查：

```bash
# 部署前端
./deploy-frontend-server.sh

# 部署后端
./redeploy-backend.sh

# 检查服务状态
./check-deployment.sh

# 查看日志
gcloud run services logs read backend --region=asia-southeast1 --limit=50

# SSH 连接到服务器
ssh root@120.55.181.23

# 查看文件
ls -la /data/wwwroot/default/guojie/
```
