## 🔒 管理员密码配置指南

### 问题背景
之前代码中硬编码了管理员密码 `075831`，这是一个严重的安全隐患。新版本已完全重构为使用环境变量配置。

### 解决方案要点

#### 1. **配置管理模块** (`config.py`)
- 创建专门的配置管理模块，统一处理敏感信息
- 敏感信息从环境变量读取，不再硬编码
- 提供配置验证函数，初始化时检查必要配置

#### 2. **环境变量配置**
所有敏感信息现在通过环境变量设置：
```bash
export MANAGER_ACCOUNT=manager              # 管理员账号（可选，默认：manager）
export MANAGER_PASSWORD='YourPassword123!'  # 管理员密码（必须设置！）
export MANAGER_NICKNAME='管理员'             # 管理员昵称（可选，默认：管理员）
export MANAGER_LEVEL=enterprise             # 管理员级别（可选，默认：enterprise）
```

#### 3. **代码更改清单**

| 文件 | 更改内容 |
|------|----------|
| `config.py` | ✅ **新建** - 配置管理模块 |
| `database.py` | ✅ 修改 `create_manager_account()` - 从 config 读取参数 |
| `routes/auth.py` | ✅ 修改登录逻辑 - 使用环境变量验证管理员 |
| `init_database.py` | ✅ 修改初始化脚本 - 添加配置验证 |
| `test_auth_api.py` | ✅ 修改测试脚本 - 使用环境变量 |
| `env.example` | ✅ 修改模板 - 新增管理员配置说明 |

#### 4. **安全特性**

✅ **消除硬编码密码**
- 所有 6 处硬编码密码已删除
- 密码现在只在环境变量和数据库中存储

✅ **配置验证**
- 初始化时自动检查 `MANAGER_PASSWORD` 是否已设置
- 如果未设置，初始化脚本会拒绝运行并给出提示

✅ **灵活配置**
- 支持多环境配置（开发、测试、生产）
- 可通过环境变量轻松切换管理员信息

✅ **密码强度提示**
- 初始化时提醒密码应至少 8 字符
- 建议包含大小写字母、数字、特殊字符

### 🚀 使用步骤

#### 开发环境
```bash
# 1. 设置管理员密码（使用强密码）
export MANAGER_PASSWORD='MySecurePassword123!'

# 2. 初始化数据库
cd backend
python init_database.py

# 3. 启动应用
python main.py
```

#### 测试应用
```bash
# 运行测试脚本（会使用环境变量中的密码）
python test_auth_api.py
```

#### Docker 部署
```dockerfile
# 在 Dockerfile 中设置环境变量（或通过 -e 参数传入）
ENV MANAGER_PASSWORD=your_secure_password
```

或在启动时指定：
```bash
docker run -e MANAGER_PASSWORD='YourPassword123!' your-image
```

#### Cloud Run 部署
```bash
# 通过 Secret Manager 安全存储密码
gcloud secrets create manager-password --data-file=<(echo 'YourPassword123!')

# 在部署时引用 secret
gcloud run deploy ... --set-secrets MANAGER_PASSWORD=manager-password:latest
```

### 📋 配置文件参考

参考 `env.example`，创建 `.env` 文件（**不要提交到 Git！**）：

```bash
# 管理员配置
MANAGER_ACCOUNT=manager
MANAGER_PASSWORD=YourSecurePassword123!
MANAGER_NICKNAME=管理员
MANAGER_LEVEL=enterprise

# 其他配置...
```

### ⚠️ 安全提示

1. **强密码策略**
   - ❌ 避免使用默认密码或弱密码
   - ✅ 使用至少 8-12 字符的复杂密码
   - ✅ 包含大小写字母、数字、特殊字符

2. **密码存储**
   - ❌ 不要在代码中硬编码密码
   - ❌ 不要在版本控制中提交密码
   - ✅ 使用环境变量或密钥管理系统

3. **密码初始化**
   - 首次部署时必须设置 `MANAGER_PASSWORD`
   - 初始化脚本会自动进行验证
   - 如果验证失败，会清晰地显示错误信息

4. **生产环境**
   - 使用专业密钥管理系统（如 AWS Secrets Manager、Google Secret Manager）
   - 定期轮换管理员密码
   - 启用审计日志

### 🔍 调试

#### 查看当前配置
```python
from config import get_config_summary
print(get_config_summary())

# 输出：
# {
#   'manager_account': 'manager',
#   'manager_nickname': '管理员',
#   'manager_level': 'enterprise',
#   'manager_password_set': True,  # 只显示是否已设置，不显示密码本身
#   ...
# }
```

#### 测试管理员登录
```bash
# 确保已设置环境变量
export MANAGER_PASSWORD='YourPassword123!'

# 运行测试脚本
python test_auth_api.py
```

### 📚 相关文件

- [config.py](config.py) - 配置管理模块
- [env.example](env.example) - 环境变量模板
- [database.py](database.py#L511-L545) - 管理员账号创建函数
- [routes/auth.py](routes/auth.py#L181-L220) - 登录验证逻辑

---

**更新时间**: 2026-01-25  
**版本**: 2.0 - 完全移除硬编码密码
