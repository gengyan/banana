# 后端问题排查指南

## 已修复的问题

### 1. 模型名称错误 ✅
- **问题**: 使用 `gemini-pro` 模型时出现 404 错误
- **原因**: `gemini-pro` 模型已不再可用
- **解决**: 更新为 `gemini-2.5-flash`（免费配额可用）

### 2. importlib.metadata 警告 ✅
- **问题**: 出现 `module 'importlib.metadata' has no attribute 'packages_distributions'` 警告
- **原因**: Python 版本兼容性问题
- **解决**: 添加了警告过滤器，忽略此警告

### 3. Python 版本警告 ✅
- **问题**: Python 3.9.6 已过时警告
- **原因**: Google API 推荐使用 Python 3.10+
- **解决**: 添加了警告过滤器（不影响功能）

### 4. 环境变量配置 ✅
- **问题**: `.env` 文件不存在
- **解决**: 已创建 `.env` 文件并配置 API Key

## 常见错误及解决方案

### 错误: 404 models/gemini-pro is not found
**解决**: 确保使用正确的模型名称（当前使用 `gemini-2.5-flash`）

### 错误: 429 Quota exceeded
**解决**: 
- 检查 API 配额是否已用完
- 等待配额重置（通常每分钟或每天重置）
- 考虑升级 API 计划

### 错误: address already in use
**解决**: 
```bash
# 查找并停止占用端口的进程
lsof -ti:8000 | xargs kill -9
```

### 错误: GOOGLE_API_KEY 环境变量未设置
**解决**: 
```bash
# 创建 .env 文件
echo "GOOGLE_API_KEY=your_key_here" > backend/.env
```

## 测试后端

### 1. 检查模型可用性
```bash
cd backend
python3 check_error.py
```

### 2. 启动服务
```bash
python3 main.py
```

### 3. 测试 API
```bash
# 测试根路径
curl http://localhost:8000/

# 测试聊天接口
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{"message":"你好","mode":"chat","history":[]}'
```

## 当前配置

- **模型**: `gemini-2.5-flash`
- **端口**: 8000
- **API Key**: 从 `.env` 文件读取

## 注意事项

1. 免费 API 配额有限，注意使用频率
2. 生产环境应限制 CORS 源
3. 建议使用 Python 3.10+ 以获得更好的兼容性

