# 支付宝配置指南 - 获取ID和证书

## 需要的配置信息

为了接入支付宝支付，您需要准备以下信息：

### 1. App ID（应用ID）
- **位置**：支付宝开放平台 → 控制台 → 我的应用 → 应用详情
- **说明**：创建应用后自动生成，格式类似：`2021001234567890`
- **用途**：标识您的应用

### 2. 应用私钥（RSA2私钥）
- **位置**：需要自己生成，不上传到支付宝
- **格式**：RSA2格式的私钥
- **用途**：用于对请求参数进行签名

### 3. 支付宝公钥（RSA2公钥）
- **位置**：支付宝开放平台 → 开发信息 → 接口加签方式 → 查看支付宝公钥
- **格式**：RSA2格式的公钥
- **用途**：用于验证支付宝返回数据的签名

## 详细获取步骤

### 第一步：注册并认证

1. 访问 [支付宝开放平台](https://open.alipay.com/)
2. 使用企业支付宝账号登录
3. 完成企业实名认证（需要营业执照等材料）

### 第二步：创建应用

1. 登录后进入 **控制台**
2. 点击 **创建应用** → **网页&移动应用**
3. 填写应用信息：
   - 应用名称：果捷AI（或其他名称）
   - 应用类型：网页应用
   - 应用简介：AI图片生成服务
4. 提交审核

### 第三步：获取App ID

创建应用后，在 **应用详情** 页面可以看到：
- **App ID**：类似 `2021001234567890`

### 第四步：生成RSA2密钥对

#### 方法1：使用支付宝密钥生成工具（推荐）

1. 下载 [支付宝密钥生成工具](https://opendocs.alipay.com/common/02kkv7)
2. 运行工具，选择 **RSA2**（2048位）
3. 点击 **生成密钥**
4. 保存生成的文件：
   - `应用私钥.txt` 或 `private_key.txt` - 这就是您需要的私钥
   - `应用公钥.txt` 或 `public_key.txt` - 需要上传到支付宝

#### 方法2：使用OpenSSL命令行

```bash
# 生成私钥
openssl genrsa -out private_key.pem 2048

# 生成公钥
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

### 第五步：上传应用公钥到支付宝

1. 进入应用详情 → **开发信息**
2. 找到 **接口加签方式**
3. 点击 **设置** → 选择 **RSA2(SHA256)密钥**
4. 上传您的**应用公钥**（public_key.pem的内容）
5. 保存后，支付宝会显示 **支付宝公钥**

### 第六步：配置到.env文件

在 `backend/.env` 文件中添加：

```env
# 支付宝配置
ALIPAY_APP_ID=2021001234567890  # 替换为您的App ID

# 应用私钥（完整格式，包括BEGIN/END标记）
ALIPAY_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
（完整的私钥内容）
...
-----END RSA PRIVATE KEY-----"

# 支付宝公钥（完整格式）
ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...
（完整的支付宝公钥内容）
...
-----END PUBLIC KEY-----"

# 环境设置
ALIPAY_SANDBOX=true  # 测试用true，生产环境用false

# 回调地址（必须是公网可访问的URL）
ALIPAY_NOTIFY_URL=https://your-domain.com/api/payment/notify
ALIPAY_RETURN_URL=https://your-domain.com/payment/success
```

### 私钥格式说明

私钥需要保留完整的格式，包括换行符。在.env文件中可以使用以下方式：

**方式1：使用转义换行符**
```env
ALIPAY_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n...\n-----END RSA PRIVATE KEY-----"
```

**方式2：使用多行字符串（某些环境变量解析器支持）**
```env
ALIPAY_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...
-----END RSA PRIVATE KEY-----"
```

## 测试环境（沙箱）

在开发阶段，可以使用支付宝沙箱环境：

1. 在支付宝开放平台 → **研发服务** → **沙箱环境**
2. 可以看到：
   - **沙箱应用**：会生成一个测试用的App ID
   - **沙箱账号**：用于测试的买家/卖家账号
   - **RSA2密钥**：可以下载测试用的密钥对

沙箱环境的配置方式与正式环境相同，只是使用沙箱的App ID和密钥。

## 重要提示

⚠️ **安全注意事项**：

1. **私钥绝对不能泄露**：不要提交到代码仓库
2. **不要在生产环境使用测试密钥**
3. **定期更换密钥**：建议定期更换密钥对
4. **使用环境变量**：不要硬编码在代码中
5. **备份密钥**：妥善保存密钥文件，但不要放在公开位置

## 验证配置

配置完成后，重启后端服务，查看启动日志：

```
✅ 支付宝SDK初始化成功（沙箱环境）
```

或

```
✅ 支付宝SDK初始化成功（正式环境）
```

如果看到错误，检查：
1. 私钥格式是否正确（包含BEGIN/END标记）
2. App ID是否正确
3. 密钥是否匹配（应用公钥已上传到支付宝）

## 相关链接

- [支付宝开放平台](https://open.alipay.com/)
- [网页支付接入文档](https://opendocs.alipay.com/open/02rabx)
- [密钥生成工具下载](https://opendocs.alipay.com/common/02kkv7)
- [RSA密钥说明](https://opendocs.alipay.com/common/02kkv6)
