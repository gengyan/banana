# 本地调试启动脚本说明

## 果捷 Studio（本目录）

- **本地调试**：`./start.sh`（带代理启动前后端）
- **境外部署**：`./restart.sh`（直连，不带代理）

```bash
cd studio
./start.sh      # 本地调试（推荐）
./restart.sh    # 境外部署
```

## 使用场景

### 场景 1：本地调试（需要代理访问 Google API）

如果你的网络需要代理才能访问 `aiplatform.googleapis.com`：

```bash
cd studio
./start.sh
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

### 场景 2：境外部署（不需要代理）

服务器在境外，可直接访问 Google API：

```bash
cd studio

# 无代理启动
./restart.sh
```

或在 `backend/.env` 中设置 `DISABLE_PROXY=true`。

## 代理配置说明

### 脚本内部代理配置

`start.sh` 硬编码了以下代理：
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
# 编辑 start.sh
# 将代理地址改为你的，例如：
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

**方式 2：启动时覆盖（推荐）**
```bash
HTTP_PROXY=http://your-proxy:port \
HTTPS_PROXY=http://your-proxy:port \
./start.sh
```

### 如果代理需要认证

```bash
export HTTP_PROXY=http://username:password@127.0.0.1:29290
export HTTPS_PROXY=http://username:password@127.0.0.1:29290
./start.sh
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
tail -f studio/backend.log

# 查看前端日志
tail -f studio/frontend.log
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
grep -i "proxy\|error" studio/backend.log | tail -20
```

### 在部署环境禁用代理

```bash
# 在 .env 中添加或修改
DISABLE_PROXY=true

# 或启动时（境外部署）：
./restart.sh
```
