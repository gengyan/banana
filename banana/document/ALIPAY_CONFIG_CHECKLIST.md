# 支付宝配置检查清单

## ✅ 已完成

1. ✅ **App ID**: 2021006122600997
2. ✅ **支付宝公钥**: 已提供（格式正确）

## ❌ 还需要配置

### 1. 应用私钥（必需）

**说明**：这是最重要的配置，用于对支付请求进行签名。

**获取方式**：
1. 使用支付宝密钥生成工具（推荐）：
   - 下载：https://opendocs.alipay.com/common/02kkv7
   - 生成 RSA2（2048位）密钥对
   - 保存 `应用私钥.txt`

2. 或使用 OpenSSL 命令行：
   ```bash
   openssl genrsa -out private_key.pem 2048
   ```

**格式要求**：
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
（完整的私钥内容，通常很长）
...
-----END RSA PRIVATE KEY-----
```

**⚠️ 重要**：
- 私钥绝对不能泄露
- 不要提交到代码仓库
- 妥善保管私钥文件

### 2. 配置.env文件

如果还没有 `.env` 文件，请：

```bash
cd backend
cp env.example .env
```

然后在 `.env` 文件中添加您的应用私钥：

```env
ALIPAY_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
（粘贴您的私钥内容）
-----END RSA PRIVATE KEY-----"
```

### 3. 回调地址配置（根据实际部署情况）

**开发环境**（本地测试）：
- 可以使用内网穿透工具（如 ngrok、frp）来获取公网地址
- 或使用沙箱环境测试（不需要公网地址，但正式环境需要）

**生产环境**：
- `ALIPAY_NOTIFY_URL`: 必须是公网可访问的HTTPS地址
- `ALIPAY_RETURN_URL`: 支付完成后用户跳转的地址

当前默认配置（开发环境）：
```env
ALIPAY_NOTIFY_URL=http://localhost:8000/api/payment/notify
ALIPAY_RETURN_URL=http://localhost:3000/payment/success
```

## 配置完成后验证

1. 确保 `.env` 文件配置完整
2. 重启后端服务
3. 查看启动日志，应该看到：
   ```
   ✅ 支付宝SDK初始化成功（沙箱环境）
   ```
   或
   ```
   ✅ 支付宝SDK初始化成功（正式环境）
   ```

## 测试支付流程

1. 使用沙箱环境测试（`ALIPAY_SANDBOX=true`）
2. 获取沙箱测试账号（买家账号）
3. 在前端页面发起支付
4. 使用沙箱账号完成支付测试

## 常见问题

### Q: 私钥格式不对怎么办？
A: 确保私钥包含完整的 BEGIN/END 标记，并且保留换行符。

### Q: 本地开发如何测试回调？
A: 使用内网穿透工具，或者先测试支付跳转功能，回调功能在部署到公网后再测试。

### Q: 沙箱环境和正式环境的区别？
A: 沙箱环境用于测试，使用测试账号；正式环境用于生产，需要完成应用审核和产品签约。
