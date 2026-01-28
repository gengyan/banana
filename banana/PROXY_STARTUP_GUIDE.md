# 本地调试启动脚本说明

## 脚本文件

- **`restart-with-proxy.sh`** - 本地调试用，**带代理启动**（针对需要代理才能访问 Google API 的环境）
- **`restart.sh`** - 原始脚本，部署/生产环境用（不带代理）

## 使用场景

### 场景 1：本地调试（需要代理访问 Google API）

如果你的网络需要代理才能访问 `aiplatform.googleapis.com`：

```bash
cd /Users/mac/Documents/ai/knowledgebase/bananas/banana

# 使用带代理的启动脚本
./restart-with-proxy.sh
```

脚本会自动：
1. 设置代理环境变量：
   - `HTTP_PROXY=http://127.0.0.1:29290`
   - `HTTPS_PROXY=http://127.0.0.1:29290`
   - `NO_PROXY=localhost,127.0.0.1,127.0.0.1:3000,127.0.0.1:8080`
   - `DISABLE_PROXY=false`
2. 停止已有的前后端服务
3. 启动后端（带代理）
4. 启动前端

### 场景 2：部署/生产（不需要代理）

在云服务器或无需代理的环境：

```bash
cd /Users/mac/Documents/ai/knowledgebase/bananas/banana

# 使用原始启动脚本（无代理）
DISABLE_PROXY=true ./restart.sh
```

或修改 `.env` 中的代理配置后使用原脚本。

## 代理配置说明

### 脚本内部代理配置

`restart-with-proxy.sh` 硬编码了以下代理：
```bash
export HTTP_PROXY=http://127.0.0.1:29290
export HTTPS_PROXY=http://127.0.0.1:29290
export NO_PROXY=localhost,127.0.0.1,127.0.0.1:3000,127.0.0.1:8080
export DISABLE_PROXY=false
```

### 如果代理地址不同

如果你的代理不在 `127.0.0.1:29290`，可以：

**方式 1：修改脚本**
```bash
# 编辑 restart-with-proxy.sh
# 将第 15-18 行的代理地址改为你的代理地址，例如：
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

**方式 2：启动时覆盖（推荐）**
```bash
HTTP_PROXY=http://your-proxy:port \
HTTPS_PROXY=http://your-proxy:port \
./restart-with-proxy.sh
```

### 如果代理需要认证

```bash
export HTTP_PROXY=http://username:password@127.0.0.1:29290
export HTTPS_PROXY=http://username:password@127.0.0.1:29290
./restart-with-proxy.sh
```

## 后端代码中的代理支持

后端代码（`generators/gemini_3_pro_image.py` 等）会自动读取这些环境变量，将代理应用到 Google API 请求。

关键代码：
```python
# 代理自动从环境变量读取
http_options = genai.types.HttpOptions(
    timeout=600000,
    proxy=os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'),  # 自动读取
)
```

## 查看服务日志

启动后可以实时查看日志：

```bash
# 查看后端日志（带代理信息）
tail -f /Users/mac/Documents/ai/knowledgebase/bananas/banana/backend.log

# 查看前端日志
tail -f /Users/mac/Documents/ai/knowledgebase/bananas/banana/frontend.log
```

## 停止服务

脚本会在每次启动前自动停止已有的服务。手动停止：

```bash
# 停止后端
pkill -f 'python.*main.py'

# 停止前端
pkill -f 'vite'

# 同时停止两个
pkill -f 'python.*main.py' && pkill -f 'vite'
```

## 常见问题

### 代理连接失败

如果看到错误：
```
ProxyError: Unable to connect to proxy...
```

检查：
1. 代理服务是否在运行：`curl -v -x http://127.0.0.1:29290 https://generativelanguage.googleapis.com`
2. 代理地址和端口是否正确
3. 代理是否允许 CONNECT 到 443 端口

### 后端启动但无法连接 API

检查后端日志：
```bash
grep -i "proxy\|error" /Users/mac/Documents/ai/knowledgebase/bananas/banana/backend.log | tail -20
```

### 在部署环境禁用代理

```bash
# 在 .env 中添加或修改
DISABLE_PROXY=true

# 或启动时：
DISABLE_PROXY=true ./restart.sh
```
