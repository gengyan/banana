# 使用官方 Python 基础镜像（3.11-slim 是推荐的轻量级版本）
FROM python:3.11-slim

# 设置环境变量，确保日志能够实时输出
ENV PYTHONUNBUFFERED=True

# 设置容器内的工作目录
WORKDIR /app

# 1. 先安装依赖（利用缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. 核心：在拷贝代码前，使用 ARG 触发器强制刷新
# 或者确保 COPY 顺序正确，不使用缓存来拷贝源代码
# 使用 BUILD_TIME 作为缓存破坏器
ARG BUILD_TIME
RUN echo "Build time: ${BUILD_TIME}"

# 拷贝所有源代码到容器（不使用缓存，确保每次都是最新代码）
COPY . .

# 确保更新脚本可执行
RUN chmod +x update-build-time.sh 2>/dev/null || true
# 更新构建时间戳（确保每次部署内容不同）
RUN ./update-build-time.sh 2>/dev/null || echo "跳过时间戳更新（脚本可能不存在）"

# 确保启动脚本可执行
RUN chmod +x start.sh

# 3. 声明容器将侦听的端口（Cloud Run 默认使用 8080）
EXPOSE 8080 

# 4. 使用启动脚本，确保正确读取 PORT 环境变量
CMD ["./start.sh"]