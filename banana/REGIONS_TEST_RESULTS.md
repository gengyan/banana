# Gemini 3 Pro 区域可用性测试报告 (最终)

**测试时间**: 2026-02-12  
**测试模型**: `gemini-3-pro-image-preview`  
**项目ID**: `gen-lang-client-0801638297`

## 测试结果总结

### ❌ 所有 9 个区域都不支持该模型

| 区域组 | 区域 | HTTP 状态 | 说明 |
|------|------|----------|------|
| Americas | us-central1 | 404 | NOT_FOUND |
| Americas | us-east4 | 404 | NOT_FOUND |
| Americas | us-west1 | 404 | NOT_FOUND |
| Asia Pacific | asia-east1 | 404 | NOT_FOUND |
| Asia Pacific | asia-northeast1 | 404 | NOT_FOUND |
| Asia Pacific | asia-southeast1 | 404 | NOT_FOUND |
| Europe | europe-west1 | 404 | NOT_FOUND |
| Europe | europe-west4 | 404 | NOT_FOUND |
| Europe | europe-west9 | 404 | NOT_FOUND |

### ✅ 模型可用位置

- **Global** (`global`): ✅ 可用
  - 状态: 模型存在
  - 限制: 速率限制 (429 RESOURCE_EXHAUSTED)
  - 重试: 自动重试已启用 (指数退避: 2s-30s)

## 测试方法

使用 Google Cloud Vertex AI HTTP API 的 `generateContent` 端点：
```
POST https://{region}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent
```

## 当前最终配置

```env
# backend/.env
VERTEX_AI_LOCATION=global  
VERTEX_AI_PROJECT=gen-lang-client-0801638297
```

✅ **服务已用该配置重启，功能恢复**

## 速率限制处理

代码中已实现自动重试机制 (见 `backend/generators/gemini_3_pro_image.py`):

```python
# 重试配置
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # 指数退避 (秒)
MAX_WAIT_TIME = 30  # 最多等待 30 秒
```

当收到 429 错误时，自动等待后重试。

## 可能的后续方案

1. **等待 Google 扩展区域支持**
   - 联系 Google Cloud 销售获取最新可用区域信息
   - 定期检查 [Vertex AI 模型可用性文档](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions)

2. **申请项目配额升级**
   - 在 Google Cloud Console 中增加速率限制
   - 防止 429 错误过于频繁

3. **考虑使用其他模型**
   - `gemini-2.0-flash`: 在全球区域可用 (更快更便宜)
   - `gemini-1.5-pro`: 在多个区域可用 (功能全面)

## 测试代码示例

```bash
# 验证当前配置
grep VERTEX_AI_LOCATION /Users/mac/Documents/ai/knowledgebase/bananas/banana/backend/.env

# 查看最近的错误日志
tail -f /Users/mac/Documents/ai/knowledgebase/bananas/banana/backend/backend.log
```

---
**状态**: ✅ 已解决（使用 global 位置）  
**最后更新**: 2026-02-12 19:12
