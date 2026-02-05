# 常见错误及解决方案

## 后端错误

### 1. ModuleNotFoundError: No module named 'google.generativeai'
**错误信息**: 
```
ModuleNotFoundError: No module named 'google.generativeai'
```

**原因**: 依赖包未安装在当前 Python 环境中

**解决方案**:
```bash
cd backend
# 根据你使用的 Python 命令选择
python -m pip install -r requirements.txt
# 或
python3 -m pip install -r requirements.txt
```

### 2. 404 models/gemini-pro is not found
**错误信息**: 
```
404 models/gemini-pro is not found for API version v1beta
```

**原因**: 模型名称已过时

**解决方案**: 代码已更新为使用 `gemini-2.5-flash`，确保使用最新代码

### 3. 429 Quota exceeded
**错误信息**: 
```
429 You exceeded your current quota
```

**原因**: API 配额已用完

**解决方案**: 
- 等待配额重置（通常每分钟或每天）
- 检查 Google Cloud 控制台的配额设置
- 考虑升级 API 计划

### 4. address already in use
**错误信息**: 
```
ERROR: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
```

**原因**: 端口 8000 已被占用

**解决方案**:
```bash
# 查找并停止占用端口的进程
lsof -ti:8000 | xargs kill -9
```

## 前端错误

### 1. vite: command not found
**错误信息**: 
```
sh: vite: command not found
```

**原因**: 前端依赖未安装

**解决方案**:
```bash
cd frontend
npm install
```

### 2. Cannot find module 'react'
**错误信息**: 
```
Error: Cannot find module 'react'
```

**原因**: 前端依赖未安装或安装不完整

**解决方案**:
```bash
cd frontend
# 删除 node_modules 和 package-lock.json，重新安装
rm -rf node_modules package-lock.json
npm install
```

### 3. 端口 3000 被占用
**错误信息**: 
```
Port 3000 is in use
```

**解决方案**:
```bash
# 查找并停止占用端口的进程
lsof -ti:3000 | xargs kill -9
# 或使用其他端口
npm run dev -- --port 3001
```

## 检查工具

### 后端检查
```bash
cd backend
python check_errors.py
```

### 前端检查
```bash
cd frontend
npm list --depth=0  # 检查已安装的包
```

## 快速诊断

### 后端
1. 检查 Python 版本: `python --version`
2. 检查依赖: `python -m pip list | grep -E "fastapi|google-generativeai"`
3. 检查环境变量: `cat backend/.env`
4. 测试 API: `curl http://localhost:8000/`

### 前端
1. 检查 Node 版本: `node --version`
2. 检查依赖: `ls frontend/node_modules | head -10`
3. 检查服务: `curl http://localhost:3000/`

