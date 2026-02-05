# 私钥存放位置指南

## ✅ 正确的位置：`.env` 文件

**私钥应该放在**: `backend/.env` 文件中

**完整路径**: `backend/.env`

## 配置方法

### 1. 打开 `.env` 文件

```bash
cd backend
# 如果文件不存在，从模板复制
cp env.example .env

# 使用编辑器打开
# macOS/Linux:
nano .env
# 或
vim .env

# Windows:
notepad .env
```

### 2. 添加私钥配置

在 `.env` 文件中找到或添加以下配置：

```env
ALIPAY_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
（您的完整私钥内容）
...
-----END RSA PRIVATE KEY-----"
```

**重要**：
- 保留 `-----BEGIN RSA PRIVATE KEY-----` 和 `-----END RSA PRIVATE KEY-----` 标记
- 保留换行符（可以直接粘贴多行）
- 使用双引号包裹整个私钥内容

### 3. 完整配置示例

`.env` 文件中应该包含：

```env
# Google API Key
GOOGLE_API_KEY=your_google_api_key_here

# 支付宝配置
ALIPAY_APP_ID=2021006122600997
ALIPAY_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEApCGtlzJU1dfK1mxKJULpHJ4BQP198A8tLZqK/uJiRejv4UaCPF38+vxMomiMgjT+Uu1UoOUihU2wjP40Am+2eIMWA+TFsrGgDyiRQHt/B8FEOOrLRzxugvTBuFMdUfZz/L6PgNFwmZc0FcXiPnDokbkNb8I7qmf3W9TeChWozY2ADNrAZ8cVO4RVnEBoITkcJAalXwAH0wcB+lWgjTUpn6XDqg4sDQZNL0jFs+7feiDoHdfWUow6k2DAgdaONyAmIc//gpp5IVR54tsTZIjBAWf1kiw43m/a2dH4FkOl++lgtl9sq4Lib+ajqx56DsLzPdWkGALIzB4VXmSgYiVRxwIDAQAB
-----END RSA PRIVATE KEY-----"
ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApCGtlzJU1dfK1mxKJULpHJ4BQP198A8tLZqK/uJiRejv4UaCPF38+vxMomiMgjT+Uu1UoOUihU2wjP40Am+2eIMWA+TFsrGgDyiRQHt/B8FEOOrLRzxugvTBuFMdUfZz/L6PgNFwmZc0FcXiPnDokbkNb8I7qmf3W9TeChWozY2ADNrAZ8cVO4RVnEBoITkcJAalXwAH0wcB+lWgjTUpn6XDqg4sDQZNL0jFs+7feiDoHdfWUow6k2DAgdaONyAmIc//gpp5IVR54tsTZIjBAWf1kiw43m/a2dH4FkOl++lgtl9sq4Lib+ajqx56DsLzPdWkGALIzB4VXmSgYiVRxwIDAQAB
-----END PUBLIC KEY-----"
ALIPAY_SANDBOX=true
ALIPAY_NOTIFY_URL=http://localhost:8000/api/payment/notify
ALIPAY_RETURN_URL=http://localhost:3000/payment/success
```

## ❌ 不要放在这些地方

1. **不要放在代码文件中**（如 `main.py`）
2. **不要放在公开的配置文件**（如 `config.py`）
3. **不要提交到Git仓库**（确保 `.env` 在 `.gitignore` 中）
4. **不要放在前端代码中**
5. **不要硬编码在代码中**

## 安全检查

### 1. 确认 `.env` 在 `.gitignore` 中

```bash
cd backend
cat .gitignore | grep -E "\.env|env" || echo "⚠️ 建议添加 .env 到 .gitignore"
```

应该在 `.gitignore` 中包含：
```
.env
*.env
.env.*
```

### 2. 设置文件权限（Linux/macOS）

```bash
# 设置 .env 文件权限为仅当前用户可读
chmod 600 backend/.env
```

### 3. 验证配置

配置完成后，重启后端服务，查看启动日志：

```
✅ 支付宝SDK初始化成功（沙箱环境）
```

如果看到错误，检查私钥格式是否正确。

## 文件结构

```
backend/
├── .env              ← 私钥放在这里（不提交到Git）
├── env.example       ← 配置模板（可以提交到Git）
├── main.py           ← 代码文件（不要放私钥）
├── requirements.txt
└── ...
```

## 总结

✅ **私钥应该放在**: `backend/.env` 文件中  
✅ **使用环境变量**: 代码通过 `os.getenv()` 读取  
✅ **确保安全**: `.env` 文件不在Git仓库中  
✅ **格式正确**: 保留 BEGIN/END 标记和换行符

