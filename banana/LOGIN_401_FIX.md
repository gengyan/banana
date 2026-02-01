# 登录401错误 - 问题诊断与解决方案

## 问题描述
用户登录时返回 401 错误，错误信息为"账号或密码错误"

## 问题根因
**bcrypt 库未安装**

虽然 `requirements.txt` 中指定了 `bcrypt==4.1.2`，但环境中实际没有安装该库。导致：
- 后端使用 SHA256 作为备用密码验证方式
- 但数据库中存储的密码是用 bcrypt 哈希的
- SHA256 验证 bcrypt 哈希必然失败 → 401 错误

## 诊断过程

### 1. API 响应检查 ✅
```
POST /api/auth/login
Body: {"account": "13333268331", "password": "123456"}
Response: 401 - "账号或密码错误"
```

### 2. 用户数据验证 ✅
- 用户 "13333268331" 在数据库中存在
- 密码哈希格式: `$2b$12$Lbu.KbCNh0M3HDh7N2f4teM...` (bcrypt 格式)

### 3. 密码验证测试 ❌
**安装 bcrypt 前:**
```
[数据库] 密码哈希类型: bcrypt
[数据库] 使用 SHA256 验证（bcrypt 未安装）
[数据库] ❌ 密码哈希格式错误: 不是 sha256 格式
[数据库] 密码验证结果: ❌ 不匹配
```

## 解决方案

### 步骤 1: 安装 bcrypt 库
```bash
pip install bcrypt
```

**输出:**
```
Successfully installed bcrypt-5.0.0
```

### 步骤 2: 验证密码验证现在工作正常 ✅
```
[数据库] 使用 bcrypt 验证
[数据库] bcrypt 验证结果: ✅ 匹配
[数据库] ✅ 用户登录成功: 13333268331
```

### 步骤 3: 重启后端服务
```bash
./restart.sh
```

### 步骤 4: 再次测试登录 API ✅
```
POST /api/auth/login
Response: 200 OK
{
  "success": true,
  "user": {
    "id": "user_1769313889861_d82bba68",
    "account": "13333268331",
    "nickname": "emao",
    "level": "normal"
  },
  "session_token": "vrxSMp8496qmNIdtQinEfJZxiVF0rp0tViqxsWMvEqg"
}
```

## 修改记录

### requirements.txt
- 修改 bcrypt 版本要求: `bcrypt==4.1.2` → `bcrypt>=4.1.2`
- 允许使用更新的 bcrypt 版本（如 5.0.0）

## 测试用例

已验证的可用账户（密码: 123456）：
1. **13333268331** - 昵称: emao
2. **13333268333** - 昵称: emao3
3. **13333268444** - 昵称: emao4

管理员账户:
- **manager** - 可用（如果配置了 MANAGER_PASSWORD）

## 防止方案

为了防止此问题再次发生，建议：

1. **启用依赖检查脚本** - 在服务启动时验证所有必需的库都已安装
2. **CI/CD 检查** - 在部署前检查 requirements.txt 中的所有包是否可安装
3. **启动验证日志** - 添加更明显的警告日志当缺少关键依赖库时

## 相关文件

- [/backend/requirements.txt](/backend/requirements.txt) - Python 依赖配置（已更新）
- [/backend/database.py](/backend/database.py) - 密码验证逻辑
- [/backend/routes/auth.py](/backend/routes/auth.py) - 登录 API 路由

## 总结

✅ **问题已解决**
- bcrypt 已安装（版本 5.0.0）
- 密码验证现在正常工作
- 登录功能已恢复
- 前后端服务已重启
