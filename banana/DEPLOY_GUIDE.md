# 部署脚本使用指南（精简版）

> 从 9 个部署脚本精简为 4 个核心脚本

## 📋 4 个核心部署脚本

### 1. `deploy-server.sh` - 后端部署

部署后端到 Google Cloud Run

```bash
./deploy-server.sh
```

**功能**：
- 加载 `backend/.env` 环境变量
- 自动检测 gcloud 项目
- 配置后端 CORS、Vertex AI、Google API Key 等
- 部署到 Cloud Run（asia-southeast1 区域）

---

### 2. `deploy-web.sh` - 前端部署（海外）

部署前端到 Google Cloud Run

```bash
./deploy-web.sh
```

**功能**：
- 自动检测后端 URL
- 将后端地址编译到前端构建中
- 部署服务名 "hello" 到 Cloud Run
- 支持 BACKEND_URL 环境变量覆盖

---

### 3. `deploy-web-cn.sh` - 前端部署（国内）

部署前端到国内服务器（120.55.181.23）

```bash
./deploy-web-cn.sh
```

**功能**：
- 编译前端代码（npm run build）
- 通过 SSH 连接到 120.55.181.23
- 使用 rsync 快速同步文件
- 自动备份旧版本
- 设置文件权限

---

### 4. `deploy-all.sh` - 全量部署

一键部署所有服务（后端 + 海外前端 + 国内前端）

```bash
./deploy-all.sh
```

**执行流程**：
1. 执行 `deploy-server.sh` - 后端
2. 等待 3 秒钟
3. 执行 `deploy-web.sh` - 海外前端
4. 执行 `deploy-web-cn.sh` - 国内前端
5. 自动更新后端 CORS 配置

---

## 🚀 使用场景

### 场景 1：首次部署或完整更新

```bash
./deploy-all.sh
```

最简单的方式，一键搞定所有部署。

### 场景 2：仅更新后端

```bash
./deploy-server.sh
```

**何时使用**：
- 修改了后端代码或配置
- 更新了 GOOGLE_API_KEY 或其他环境变量

### 场景 3：仅更新海外前端

```bash
./deploy-web.sh
```

**何时使用**：
- 修改了前端代码（不涉及国内服务器）
- 需要快速部署到 Cloud Run

### 场景 4：仅更新国内前端

```bash
./deploy-web-cn.sh
```

**何时使用**：
- 只需要更新国内用户可见的前端
- 不需要更新海外 Cloud Run 版本

---

## ⚙️ 环境变量配置

### 后端配置（backend/.env）

```env
# Google API
GOOGLE_API_KEY=your-api-key

# Vertex AI（用于图片生成）
VERTEX_AI_PROJECT=your-project-id
VERTEX_AI_LOCATION=asia-southeast1

# CORS 允许的前端来源（多个用逗号分隔）
FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://gj.emaos.top,https://gj.emaos.top

# 其他配置
ALIPAY_APP_ID=...
ALIPAY_PRIVATE_KEY=...
```

### 部署前验证

```bash
# 检查 gcloud 登录状态
gcloud auth list

# 检查项目配置
gcloud config get-value project

# 检查后端 .env 文件
cat backend/.env | grep GOOGLE_API_KEY
```

---

## 📊 部署结果验证

### 部署完成后

```bash
# 查看后端 URL
gcloud run services describe backend --region asia-southeast1 --format='value(status.url)'

# 查看海外前端 URL
gcloud run services describe hello --region asia-southeast1 --format='value(status.url)'

# 查看国内前端（直接访问）
http://120.55.181.23
http://gj.emaos.top  # 如果配置了域名
```

### 测试 CORS

打开浏览器，访问前端后打开控制台（F12）：

```javascript
// 测试后端连接
fetch('https://backend-xxx.run.app/docs')
  .then(r => r.ok ? console.log('✅ 后端连接正常') : console.log('❌ 后端返回错误'))
  .catch(e => console.log('❌ CORS 错误或网络错误', e.message))
```

---

## 🔄 对比：旧脚本 vs 新脚本

### 删除的脚本（9 个）

| 旧脚本名 | 替换为 | 说明 |
| --- | --- | --- |
| `deploy-backend.sh` | `deploy-server.sh` | 功能相同，名称简化 |
| `deploy-backend-cloud.sh` | `deploy-server.sh` | 合并为一个脚本 |
| `deploy-cloud-run.sh` | `deploy-web.sh` | 功能相同，名称简化 |
| `deploy-frontend-cloud.sh` | `deploy-web.sh` | 合并为一个脚本 |
| `deploy-frontend-server.sh` | `deploy-web-cn.sh` | 功能相同，名称简化 |
| `redeploy-all.sh` | `deploy-all.sh` | 功能相同，重命名 |
| `redeploy-backend.sh` | `deploy-server.sh` | 合并为一个脚本 |
| `redeploy-frontend.sh` | `deploy-web.sh` | 合并为一个脚本 |
| `build-and-deploy.sh` | `deploy-web.sh` | 前端构建已集成 |

### 新增特性

- **自动 CORS 更新**：`deploy-all.sh` 会自动更新后端 CORS 配置
- **更好的错误处理**：简化的脚本更易调试
- **环境变量管理**：统一从 `.env` 文件读取
- **自动备份**：国内服务器部署自动备份旧版本

---

## 📝 日常工作流

### 本地开发

```bash
# 启动本地开发环境
./start.sh
```

### 测试部署

```bash
# 仅测试后端
./deploy-server.sh

# 仅测试海外前端
./deploy-web.sh

# 仅测试国内前端
./deploy-web-cn.sh
```

### 生产部署

```bash
# 完整部署所有服务
./deploy-all.sh

# 验证部署
bash check-deployment.sh
```

---

## 🆘 常见问题

### Q: 如何回滚国内服务器的前端？

```bash
# 查看备份目录
ssh root@120.55.181.23 "ls -la /data/wwwroot/default/ | grep backup"

# 恢复备份
BACKUP_DIR="/data/wwwroot/default/guojie_backup_20260204_143022"
ssh root@120.55.181.23 "rm -rf /data/wwwroot/default/guojie && cp -r $BACKUP_DIR /data/wwwroot/default/guojie"
```

### Q: 如何只修改后端 CORS 配置？

```bash
# 修改 backend/.env
FRONTEND_ORIGINS=http://localhost:3000,https://new-domain.com

# 部署后端
./deploy-server.sh
```

### Q: 如何跳过国内服务器部署？

```bash
./deploy-server.sh  # 后端
./deploy-web.sh     # 海外前端
# 跳过 ./deploy-web-cn.sh
```

### Q: 国内服务器部署需要什么权限？

- SSH 可登录
- 可写入 `/data/wwwroot/default/guojie` 目录
- 可执行 Nginx 重启命令（如果配置了 Nginx）

---

## 📚 相关文档

- [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md) - 详细的服务器部署指南
- [SCRIPTS.md](SCRIPTS.md) - 所有脚本的完整说明
- [DEPLOYMENT_CHECKLIST.md](document/DEPLOYMENT_CHECKLIST.md) - 部署前检查清单

