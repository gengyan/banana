# 历史记录存储说明

## 存储位置

历史记录保存在**浏览器的 IndexedDB** 数据库中，这是浏览器提供的本地数据库存储方案。

### 数据库信息

- **数据库名称**: `GuojieUserData`
- **数据库版本**: 1
- **存储位置**: 浏览器本地存储（不依赖服务器）

## 存储结构

IndexedDB 中包含三个数据存储（ObjectStore）：

### 1. projects（项目表）
存储项目基本信息：
- `id`: 项目ID（时间戳字符串）
- `title`: 项目标题
- `createdAt`: 创建时间
- `updatedAt`: 更新时间
- `messageCount`: 消息数量
- `imageCount`: 图片数量
- `preview`: 预览图（base64格式）

### 2. messages（消息表）
存储聊天消息：
- `id`: 消息ID（自动递增）
- `projectId`: 所属项目ID
- `role`: 角色（'user' 或 'assistant'）
- `content`: 消息内容
- `imageData`: 图片数据（base64格式，可选）
- `timestamp`: 时间戳

### 3. images（图片表）
存储图片（Blob格式）：
- `id`: 图片ID（自动递增）
- `projectId`: 所属项目ID
- `messageId`: 关联的消息ID
- `image`: 图片Blob数据
- `mimeType`: 图片MIME类型
- `timestamp`: 时间戳

## 如何查看存储的数据

### Chrome/Edge 浏览器

1. 打开开发者工具（F12）
2. 切换到 **Application** 标签（或 **应用程序**）
3. 在左侧菜单中找到 **Storage** → **IndexedDB**
4. 展开 `GuojieUserData` 数据库
5. 可以查看 `projects`、`messages`、`images` 三个存储表

### Firefox 浏览器

1. 打开开发者工具（F12）
2. 切换到 **存储** 标签
3. 展开 **IndexedDB**
4. 找到 `GuojieUserData` 数据库
5. 可以查看各个存储表

### Safari 浏览器

1. 打开开发者工具（需要先启用：Safari → 偏好设置 → 高级 → 显示开发菜单）
2. 选择 **存储** → **IndexedDB**
3. 找到 `GuojieUserData` 数据库

## 数据特点

### 优点

✅ **本地存储**：数据完全保存在用户的浏览器中，无需服务器
✅ **隐私安全**：数据不会上传到服务器，保护用户隐私
✅ **离线可用**：即使断网也可以查看历史记录
✅ **容量较大**：IndexedDB 可以存储大量数据（通常几GB）

### 限制

⚠️ **浏览器绑定**：数据保存在特定浏览器中，更换浏览器需要重新开始
⚠️ **清除数据**：如果清除浏览器数据，历史记录会被删除
⚠️ **不跨设备**：不同设备之间无法同步数据

## 数据管理

### 自动保存

- 每次在首页提交消息时，会自动创建一个新项目
- 用户消息和AI回复会自动保存到对应的项目中
- 生成的图片也会自动保存

### 手动删除

- 在项目库页面可以删除不需要的项目
- 删除项目时会同时删除相关的所有消息和图片

### 数据导出

目前没有提供导出功能，但可以通过浏览器开发者工具手动查看和复制数据。

## 相关代码文件

- `frontend/src/utils/storage.js` - 存储工具类，包含所有数据库操作函数
- `frontend/src/pages/Home.jsx` - 首页，提交消息时调用保存函数
- `frontend/src/pages/ProjectLibrary.jsx` - 项目库页面，显示所有保存的项目
- `frontend/src/pages/ProjectDetail.jsx` - 项目详情页面，显示项目的聊天记录

