# 支付宝支付接入说明

## 已完成的工作

✅ 后端支付接口实现
- `/api/payment/create` - 创建支付订单
- `/api/payment/notify` - 支付回调接口
- `/api/payment/query/{order_id}` - 查询订单状态

✅ 前端支付页面集成
- Payment页面已集成支付功能
- 支持支付宝支付

✅ 配置文件更新
- `requirements.txt` 已添加 `python-alipay-sdk==3.7.3`
- `env.example` 已添加支付宝配置示例

## 配置步骤

### 1. 安装支付宝SDK

```bash
cd backend
pip install python-alipay-sdk
```

### 2. 获取支付宝配置信息

前往 [支付宝开放平台](https://open.alipay.com/)：
1. 注册并完成企业实名认证
2. 创建应用，获取 App ID
3. 生成 RSA2 密钥对
4. 上传公钥到支付宝平台
5. 保存私钥到本地

### 3. 配置环境变量

在 `backend/.env` 文件中添加以下配置：

```env
# 支付宝配置
ALIPAY_APP_ID=你的App ID
ALIPAY_PRIVATE_KEY=你的应用私钥（RSA2格式）
ALIPAY_PUBLIC_KEY=支付宝公钥
ALIPAY_SANDBOX=true  # true=沙箱环境，false=正式环境
ALIPAY_NOTIFY_URL=https://your-domain.com/api/payment/notify
ALIPAY_RETURN_URL=https://your-domain.com/payment/success
```

**注意：**
- 私钥需要保留完整的格式（包括 BEGIN/END 标记和换行符）
- 私钥格式示例：
```
-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----
```
- 可以使用多行字符串或 `\n` 转义换行符

### 4. 测试沙箱环境

1. 在支付宝开放平台启用沙箱环境
2. 获取沙箱账号（买家账号和卖家账号）
3. 使用沙箱账号进行支付测试

### 5. 部署到正式环境

1. 在支付宝开放平台完成应用审核
2. 签约支付产品
3. 将 `ALIPAY_SANDBOX` 设置为 `false`
4. 更新 `ALIPAY_NOTIFY_URL` 和 `ALIPAY_RETURN_URL` 为正式域名

## 支付流程

1. 用户在前端选择方案并点击"确认支付"
2. 前端调用 `/api/payment/create` 创建订单
3. 后端返回支付URL
4. 前端跳转到支付宝支付页面
5. 用户完成支付
6. 支付宝回调 `/api/payment/notify`（异步通知）
7. 后端验证签名并更新订单状态
8. 支付宝跳转回 `ALIPAY_RETURN_URL`

## 相关文档

- [支付宝开放平台](https://open.alipay.com/)
- [网页支付接入文档](https://opendocs.alipay.com/open/02rabx)
- [服务商必读](https://opendocs.alipay.com/iot/05k6vp)
- [支付宝服务端SDK](https://opendocs.alipay.com/open/009z4r)

## 注意事项

1. **回调URL必须是公网可访问的地址**，本地开发可以使用内网穿透工具
2. **私钥安全**：私钥必须妥善保管，不要提交到代码仓库
3. **签名验证**：所有回调必须验证签名，确保安全性
4. **订单号唯一性**：商户订单号必须保证唯一
5. **金额单位**：金额单位为元，支持两位小数

