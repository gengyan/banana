# Google Imagen API 集成说明

## 已实现的功能

1. **Banana 模式图片生成**
   - 当用户选择 "Banana" 模式时，系统会：
     1. 使用 Gemini API 优化用户输入的提示词
     2. 调用 Google Imagen API 生成图片
     3. 返回 Base64 编码的图片数据
     4. 前端以弹框方式显示生成的图片

## API 端点

### POST /api/process
当 `mode` 为 `"banana"` 时，会调用 Imagen API 生成图片。

请求示例：
```json
{
  "message": "画一个美女",
  "mode": "banana",
  "history": []
}
```

响应示例：
```json
{
  "response": "图片生成成功！",
  "success": true,
  "image_data": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "image_url": null
}
```

## 配置要求

1. **API Key**: 确保 `.env` 文件中设置了 `GOOGLE_API_KEY`
2. **API 权限**: 确保 API Key 有权限访问 Imagen API

## 注意事项

1. **API 可用性**: Imagen API 可能需要特定的 Google Cloud 项目配置
2. **配额限制**: 注意 API 调用配额限制
3. **错误处理**: 如果 Imagen API 不可用，会返回优化后的提示词

## 测试

```bash
# 测试图片生成
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{"message":"画一个美女","mode":"banana","history":[]}'
```

## 故障排查

如果图片生成失败：
1. 检查 API Key 是否正确
2. 检查 API Key 是否有 Imagen API 权限
3. 查看后端日志获取详细错误信息
4. 确认网络连接正常

