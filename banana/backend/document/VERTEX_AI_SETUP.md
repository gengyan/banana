# Vertex AI Imagen API 配置指南

## 当前状态

您已启用了 Vertex AI API，代码已更新支持两种方式调用 Imagen API：

1. **Vertex AI SDK**（推荐，需要服务账户）
2. **API Key 方式**（当前使用，但可能返回空结果）

## 配置 Vertex AI SDK（推荐）

### 步骤 1: 创建服务账户

1. 访问 Google Cloud Console: https://console.cloud.google.com/
2. 选择您的项目
3. 进入 "IAM 和管理" > "服务账户"
4. 点击 "创建服务账户"
5. 填写服务账户信息
6. 授予角色：`Vertex AI User` 或 `Vertex AI Service Agent`

### 步骤 2: 下载密钥文件

1. 点击创建的服务账户
2. 进入 "密钥" 标签
3. 点击 "添加密钥" > "创建新密钥"
4. 选择 JSON 格式
5. 下载密钥文件（例如：`service-account-key.json`）

### 步骤 3: 设置环境变量

在 `.env` 文件中添加：

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

或者使用命令行：

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
export GOOGLE_CLOUD_PROJECT_ID=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```

### 步骤 4: 重启后端服务

```bash
# 停止当前服务
pkill -f "python.*main.py"

# 重新启动
cd backend
python main.py
```

## 使用 API Key 方式（当前方式）

如果暂时无法配置服务账户，系统会继续使用 API Key 方式。

**注意**：API Key 方式可能返回空结果，因为 Imagen API 通常需要通过 Vertex AI SDK 访问。

## 验证配置

配置完成后，测试图片生成功能：

1. 选择 "图片生成" 模式
2. 上传参考图片（可选）
3. 输入描述
4. 提交

如果配置正确，应该能看到生成的图片。

## 故障排查

### 问题：仍然返回空结果

**可能原因**：
1. 服务账户密钥路径不正确
2. 服务账户权限不足
3. 项目 ID 或区域设置错误

**解决方法**：
1. 检查 `GOOGLE_APPLICATION_CREDENTIALS` 路径是否正确
2. 确认服务账户有 `Vertex AI User` 角色
3. 确认项目 ID 和区域设置正确

### 问题：导入错误

如果看到 `无法解析导入 "vertexai"` 的警告，这是正常的。只要安装了 `google-cloud-aiplatform` 包，运行时应该可以正常工作。

## 相关链接

- [Vertex AI 文档](https://cloud.google.com/vertex-ai/docs)
- [Imagen API 文档](https://cloud.google.com/vertex-ai/docs/generative-ai/image/overview)

