# Imagen 4 实现说明

## 📋 为什么只有一个路由？

根据您的要求，Imagen 4 的实现**完全参考 Gemini 3 的 blob 方式**：

### 🎯 统一架构

```
前端: imagen() → processWithFormData() → /api/imagen
                                             ↓
后端: @app.post("/api/imagen") → 返回二进制 blob
                                             ↓
前端: processBlobResponse() → 存储到 IndexedDB → 显示
```

### ✅ 与 Gemini 3 一致的实现

#### 前端 ([chat.js](frontend/src/api/chat.js#L406-L418))
```javascript
const imagen = async (message, referenceImages = null, options = {}) => {
  // 统一使用 processWithFormData 处理（与 gemini3Pro 一致）
  return await processWithFormData(
    message, 
    referenceImages, 
    '/api/imagen',      // 单一路由
    'imagen',           // mode
    'imagen_4',         // modelVersion
    options
  )
}
```

**特点**:
- 无论有无参考图片，都使用同一个函数 `processWithFormData`
- 自动处理 FormData 构建
- 自动处理 blob 响应
- 自动存储到 IndexedDB
- 与 Gemini 3 Pro 完全相同的调用方式

#### 后端 ([main.py](backend/main.py#L337-L432))
```python
@app.post("/api/imagen")
async def imagen(request: Request):
    # 1. 解析 FormData
    form_data = await request.form()
    message = form_data.get("message", "")
    
    # 2. 调用 Imagen 4 API
    data_url = generate_with_imagen(...)
    
    # 3. 转换 data URL 为二进制
    header, encoded = data_url.split(',', 1)
    mime_type = header.split(';')[0].split(':')[1]
    image_bytes = base64.b64decode(encoded)
    
    # 4. 返回二进制图片（与 banana-img 一致）
    return Response(
        content=image_bytes,
        media_type=mime_type,
        headers={
            "X-Model-Version": "imagen_4",
            "X-Success": "true",
            ...
        }
    )
```

**特点**:
- 单一路由 `/api/imagen`（FormData）
- 返回二进制图片数据（blob）
- 与 `/api/banana-img` 完全相同的响应格式
- 前端无需特殊处理，直接使用已有的 blob 处理逻辑

## 🔄 数据流程

### Gemini 3 Pro 的流程
```
前端 → processWithFormData → /api/banana-img-pro → 二进制 blob → IndexedDB
```

### Imagen 4 的流程（完全一致）
```
前端 → processWithFormData → /api/imagen → 二进制 blob → IndexedDB
```

## 💡 优势

1. **代码复用**: 前端不需要为 Imagen 编写新的处理逻辑
2. **统一体验**: 用户体验与 Gemini 3 完全一致
3. **简化维护**: 只需维护一个路由
4. **性能优化**: 使用 blob 直接传输，避免 base64 的额外开销
5. **IndexedDB**: 自动利用已有的图片缓存机制

## 📝 对比之前的设计

### ❌ 之前（复杂，两个路由）
```
有参考图 → /api/imagen (FormData) → JSON { image_url: "data:..." }
无参考图 → /api/imagen-json (JSON) → JSON { image_url: "data:..." }
```

问题:
- 需要两个路由
- 返回 JSON 包裹的 data URL
- 前端需要特殊处理 data URL
- 不符合项目现有的 blob 架构

### ✅ 现在（简单，统一）
```
所有请求 → /api/imagen (FormData) → 二进制 blob
```

优势:
- 单一路由
- 直接返回二进制数据
- 完全复用 Gemini 的处理逻辑
- 符合项目架构

## 🎯 总结

现在的实现**完全参考 Gemini 3 的 blob 方式**：
- ✅ 单一路由 `/api/imagen`
- ✅ FormData 格式
- ✅ 返回二进制 blob
- ✅ 自动存储 IndexedDB
- ✅ 与 Gemini 完全一致的用户体验

这正是您要求的实现方式！🎉
