# 上传前保密信息审计报告

## 一、高风险（必须处理）

### 1. studio/readme.md
- **内容**：阿里云服务器 root 密码、宝塔面板账号密码、管理员密码、Replicate API Token、数据库密码、项目 ID 等
- **gitignore**：已在 `studio/.gitignore` 中（第 4 行 `readme.md`），不会被提交
- **建议**：保持现状，勿移除该 gitignore 规则

### 2. test_manager_login.html
- **路径**：`banana/backend/test_manager_login.html`
- **内容**：硬编码默认密码 `admin123456`
- **状态**：✅ 已删除（文件非必需，测试功能由 Python 脚本替代）

### 3. backend/.env
- **路径**：`studio/backend/.env`、`banana/backend/.env`
- **内容**：GOOGLE_API_KEY、支付宝私钥、MANAGER_PASSWORD 等
- **gitignore**：已在 `.env*` 规则中，**不会被提交**
- **建议**：保持现状

### 4. google-key.json
- **路径**：`backend/google-key.json`
- **内容**：Google 服务账户 JSON 密钥
- **gitignore**：已在 `studio/.gitignore` 和 `banana/.gitignore` 中
- **建议**：保持现状

---

## 二、中风险（建议处理）

### 5. .env.development / .env.production
- **路径**：`*/frontend/.env.development`、`*/frontend/.env.production`
- **内容**：API 地址（Cloud Run URL、gpuhub URL 等）
- **状态**：✅ 已加入 frontend/.gitignore

### 6. env.example
- **路径**：`studio/backend/env.example`、`banana/backend/env.example`
- **内容**：含示例值（ALIPAY_APP_ID 等）
- **状态**：✅ 已加入 backend/env.example 到 .gitignore

### 7. 部署相关脚本
- **路径**：`deploy-server.sh`、`fix-server-env-proxy.sh`、`start-backend-on-server.sh` 等
- **状态**：✅ 已加入 fix-*.sh，deploy-*.sh、start*.sh 此前已存在

### 8. nginx.server.conf
- **路径**：`studio/frontend/nginx.server.conf`
- **内容**：域名、路径配置
- **状态**：✅ 已加入 studio/.gitignore

---

## 三、已正确处理

| 项目 | gitignore | 状态 |
|------|-----------|------|
| .env、.env.local 等 | .env* | 已忽略 |
| google-key.json | backend/google-key.json | 已忽略 |
| *.key, *.pem | *.key, *.pem | 已忽略 |
| service-account*.json | backend/service-account*.json | 已忽略 |
| studio/readme.md | readme.md | 已忽略 |
| deploy-*.sh, start*.sh | 多条规则 | 已忽略 |
| *.db, *.sqlite | *.db, *.sqlite* | 已忽略 |
| *.log | *.log | 已忽略 |

---

## 四、上传前检查清单

- [ ] 确认 `studio/readme.md` 未被提交（含服务器密码）
- [x] ~~处理 `banana/backend/test_manager_login.html`~~（已删除）
- [x] ~~.env.development、.env.production、env.example、fix-*.sh、nginx.server.conf~~（已加入 gitignore）
- [ ] 运行 `git status` 和 `git diff` 确认无敏感文件被暂存
- [ ] 若文件曾已提交：`git rm --cached <文件>` 后再提交
