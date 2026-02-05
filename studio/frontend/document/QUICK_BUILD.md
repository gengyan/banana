# 快速构建指南

## 手动构建步骤

### 1. 进入前端目录

```bash
cd frontend
```

### 2. 安装依赖（如果还没安装）

```bash
npm install
```

### 3. 执行构建

```bash
npm run build
```

### 4. 检查构建结果

构建完成后，应该会看到 `dist/` 目录：

```bash
ls -la dist/
```

## 使用构建脚本

也可以使用我创建的构建脚本：

```bash
# 在项目根目录执行
bash package-frontend.sh

# 或者在前端目录执行
cd frontend
bash build.sh
```

## 构建输出

构建成功后，`dist/` 目录包含：

- `index.html` - 入口文件
- `assets/` - 静态资源（JS、CSS、图片等）

## 常见问题

### 1. 构建失败：找不到模块

```bash
# 重新安装依赖
rm -rf node_modules package-lock.json
npm install
npm run build
```

### 2. 构建失败：语法错误

检查代码是否有语法错误，特别是：
- JSX 语法
- 导入路径
- 环境变量使用

### 3. 构建成功但没有 dist 目录

检查构建输出是否有错误信息，确保：
- Node.js 版本 >= 16
- 所有依赖已正确安装
- vite.config.js 配置正确

## 验证构建

构建完成后，可以预览构建结果：

```bash
npm run preview
```

然后在浏览器访问显示的地址（通常是 http://localhost:4173）

