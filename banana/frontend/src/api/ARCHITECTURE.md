## Chat API v2 — 架构可视化

### 旧版本架构图（任务维度）

```
┌─────────────────────────────────────────────────────────────┐
│                    前端组件（Home, Working）                    │
└────────────────┬──────────────────────────────────────────────┘
                 │
                 │ chatAPI.chat(message, mode, history, refImages)
                 ↓
        ┌────────────────────┐
        │ chat() 分发器      │
        └────┬────────┬────┬─┘
             │        │    └─────┐
             │        │          │
      ┌──────▼─┐ ┌───▼──┐ ┌─────▼──┐
      │ banana │ │banana│ │ imagen │
      │        │ │ _pro │ │        │
      └───┬────┘ └──┬───┘ └────┬───┘
          │         │          │
     ┌────┴┴────┐ ┌──┴──┬─────┘
     │           │ │     │
  ┌──▼──────┐ ┌─▼─▼──┐ ┌▼──────────┐
  │Text →   │ │Image │ │Image →    │
  │Image ✗  │ │→ Image│ │Image (已删除)
  │(重复)   │ │(重复) │ │           │
  └┬────────┘ └──┬───┘ └─┬────────┘
   │             │       │
   │  6 个函数   │       │  冗余实现
   │  各自独立   │       │  难以维护
   │             │       │
   └─────────────┴───────┘
        ↓
   ❌ 代码冗余、难以扩展
```

---

### 新版本架构图（模型维度）

```
┌──────────────────────────────────────────────────────────┐
│           前端组件（Home, Working）                       │
│     ✅ 调用代码完全不变（向后兼容）                      │
└────────────────┬─────────────────────────────────────────┘
                 │
                 │ chatAPI.chat(message, mode, history, refImages)
                 │ OR
                 │ chatAPI.gemini25/3Pro/imagen(message, refImages, options)
                 ↓
        ┌─────────────────────────────┐
        │  MODE_TO_MODEL 映射表        │
        │  ┌────────────────────────┐  │
        │  │ banana → gemini25      │  │
        │  │ banana_pro → gemini3Pro│  │
        │  │ imagen → imagen        │  │
        │  │ imagen4 → imagen4      │  │
        │  │ chat → chatOnly        │  │
        │  └────────────────────────┘  │
        └────────┬──────────────┬────┬──┘
                 │              │    │
                 │              │    │ (新)
        ┌────────▼───┐ ┌────────▼──┐ └──────▼──────┐
        │ gemini25() │ │gemini3Pro()│ │ imagen()   │
        └────┬───────┘ └────┬───────┘ └──┬─────────┘
             │              │            │
             │ referenceImages?          │ (待实现)
             │ YES│NO        │ YES│NO    │
             │   │          │   │       │
        ┌────▼──┴──┬────┬──▼──┴──┐     │
        │           │    │       │     │
    FormData    JSON  FormData JSON    │
    API         API   API      API    │
    /process    /process-json         │
    /process3   /process-json3        │
                     
     ✅ 4 个模型函数
     ✅ 共享 JSON/FormData 逻辑
     ✅ 易于扩展
```

---

### 流程对比

#### 旧版本请求流程

```
用户输入 (Home.jsx)
    ↓
message="描述" refImages=[]
    ↓
chatAPI.chat(msg, 'banana_pro', history, refImages=[])
    ↓
chat() 调度器
    ↓
if (mode === 'banana_pro') → banana_pro 分支
    ↓
if (hasImages) → gemini3ProImageToImage() ← ❌ 无参考图，走错分支！
    ↓
else → gemini3ProTextToImage()
    ↓
重复的代码逻辑（JSON/FormData 处理）
    ↓
/api/process-json3 请求
    ↓
返回结果
```

#### 新版本请求流程

```
用户输入 (Home.jsx)
    ↓
message="描述" refImages=[]
    ↓
chatAPI.chat(msg, 'banana_pro', history, refImages=[])
    ↓
MODE_TO_MODEL['banana_pro'] → 'gemini3Pro' ✅
    ↓
chatAPI.gemini3Pro(msg, null, { history })
    ↓
if (refImages?.length > 0)
    ↓
else → processWithJson(msg, 'banana_pro', history) ✅ 正确！
    ↓
/api/process-json3 请求
    ↓
返回结果
```

---

### 模式映射系统图解

```
┌──────────────────────────────────────────────────────────┐
│              MODE_TO_MODEL 映射表                          │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  前端 mode           映射目标           实现函数          │
│  ─────────────────────────────────────────────────────   │
│                                                            │
│  'banana'       ──→  'gemini25'    ──→  gemini25()        │
│                                         ✅ /api/process  │
│                                         ✅ /api/process-json
│                                                            │
│  'banana_pro'   ──→  'gemini3Pro'  ──→  gemini3Pro()      │
│                                         ✅ /api/process3  │
│                                         ✅ /api/process-json3
│                                                            │
│  'image_generation'                                       │
│  'imagen'        ──→  'imagen'    ──→  imagen()          │
│  'imagen3'                             🔄 /api/imagen    │
│                                         🔄 /api/imagen-json
│                                                            │
│  'imagen4'      ──→  'imagen4'    ──→  imagen4()         │
│                                         🔄 /api/imagen4   │
│                                         🔄 /api/imagen4-json
│                                                            │
│  'chat'         ──→  'chatOnly'   ──→  chatOnly()        │
│                                         ✅ /api/process-json
│                                                            │
└──────────────────────────────────────────────────────────┘

✅ = 已实现   🔄 = 待后端实现
```

---

### 数据流对比图

#### 旧版本（混乱）

```
Image → gemini25ImageToImage()   ┐
        ↓ (重复的JSON处理)        │ 代码
        ↓ (重复的FormData处理)    │ 冗余
        ↓ /api/process          │
        
Text → gemini25TextToImage()    │
       ↓ (重复的JSON处理)        │
       ↓ /api/process-json      ┘

Image → gemini3ProImageToImage() ┐
        ↓ (重复的JSON处理)        │ 代码
        ↓ (重复的FormData处理)    │ 冗余
        ↓ /api/process3         │
        
Text → gemini3ProTextToImage()   │
       ↓ (重复的JSON处理)        │
       ↓ /api/process-json3     ┘
```

#### 新版本（清晰）

```
┌─────────────────────────────────┐
│ gemini25(msg, refImages, opts)  │
├─────────────────────────────────┤
│ if (refImages?.length)          │
│   → processWithFormData()       │ ✅ 共享
│     → /api/process             │    实现
│ else                            │    逻辑
│   → processWithJson()           │
│     → /api/process-json         │
└─────────────────────────────────┘

┌──────────────────────────────────┐
│ gemini3Pro(msg, refImages, opts) │
├──────────────────────────────────┤
│ if (refImages?.length)           │
│   → processWithFormData()        │ ✅ 共享
│     → /api/process3             │    实现
│ else                             │    逻辑
│   → processWithJson()            │
│     → /api/process-json3         │
└──────────────────────────────────┘

┌─────────────────────────────────┐
│ imagen(msg, refImages, opts)     │
├─────────────────────────────────┤
│ if (refImages?.length)           │
│   → processWithFormData()        │ ✅ 相同
│     → /api/imagen               │    模式
│ else                             │    可
│   → processWithJson()            │    复用
│     → /api/imagen-json          │
└─────────────────────────────────┘
```

---

### 扩展性演示

#### 添加新模型时

##### 旧方式（需要 2 个函数）
```javascript
// ❌ 麻烦：需要编写两个函数
const claudeVisionImageToImage = async (...) => { ... }
const claudeVisionTextToImage = async (...) => { ... }

// ❌ 麻烦：需要改 chat() 分发器
if (mode === 'claude_vision') {
  if (hasImages) return claudeVisionImageToImage(...)
  else return claudeVisionTextToImage(...)
}
```

##### 新方式（只需 1 个函数）
```javascript
// ✅ 简洁：只需一个函数
const claudeVision = async (message, refImages = null, opts = {}) => {
  if (refImages?.length > 0) {
    return await processWithFormData(message, refImages, 'claude_vision', opts.history)
  } else {
    return await processWithJson(message, 'claude_vision', opts.history)
  }
}

// ✅ 简洁：只需扩展映射表
const MODE_TO_MODEL = {
  ...
  'claude_vision': 'claudeVision',  // 一行！
}

// ✅ 自动生效：无需改 chat() 函数
chatAPI.chat(msg, 'claude_vision', history)
```

---

### 组件集成示例

#### Working.jsx

```jsx
// ✅ 现有代码完全兼容
const result = await chatAPI.chat(
  message,
  mode,              // 'banana', 'banana_pro', 'chat', 'imagen', ...
  history,
  referenceImage     // null 或 File
)

// 🆕 可选的更清晰方式
const result = 
  mode === 'banana_pro'
    ? await chatAPI.gemini3Pro(message, referenceImage, { history })
    : mode === 'chat'
    ? await chatAPI.chatOnly(message, { history })
    : await chatAPI.chat(message, mode, history, referenceImage)
```

#### Home.jsx

```jsx
// ✅ 现有代码完全兼容
const result = await chatAPI.chat(
  message,
  mode,
  [],
  referenceImages.map((img) => img.file),
  aspectRatio,
  resolution,
  temperature
)
```

---

### API 接口对应关系图

```
┌─────────────────────────────────────────────────────────┐
│                  前端层（chat.js）                       │
├─────────────────────────────────────────────────────────┤
│ gemini25()          │ gemini3Pro()       │ imagen()      │
│ ─────────────       │ ──────────────      │ ──────────   │
│ if refImages        │ if refImages        │ if refImages │
│   → FormData        │   → FormData        │   → FormData │
│      ↓              │      ↓              │      ↓       │
│ else                │ else                │ else         │
│   → JSON            │   → JSON            │   → JSON     │
└─────────────────────────────────────────────────────────┘
        ↓                    ↓                    ↓
        │                    │                    │
┌───────▼──────┐   ┌─────────▼───────┐   ┌──────▼────────┐
│  后端层      │   │  后端层         │   │  后端层       │
├──────────────┤   ├─────────────────┤   ├───────────────┤
│ /api/process │   │ /api/process3   │   │ /api/imagen   │
│              │   │                 │   │  (待实现)     │
│ /api/process │   │ /api/process-json3│  │ /api/imagen   │
│ -json        │   │                 │   │  -json        │
│              │   │                 │   │  (待实现)     │
│ mode:        │   │ mode:           │   │ mode:         │
│ 'banana'     │   │ 'banana_pro'    │   │ 'imagen'      │
└──────────────┘   └─────────────────┘   └───────────────┘
```

---

### 总体架构特点

```
                        chat() 统一入口
                              ↓
                    ┌─────────────────────┐
                    │ MODE_TO_MODEL 映射  │
                    └────────────┬────────┘
                                 ↓
                    ┌─────────────────────────────────┐
                    │  4 个模型函数（共享实现逻辑）      │
                    │  ├─ gemini25()                  │
                    │  ├─ gemini3Pro()                │
                    │  ├─ imagen()  [预留]            │
                    │  ├─ imagen4() [预留]            │
                    │  └─ chatOnly()                  │
                    └────────────┬────────────────────┘
                                 ↓
                    ┌─────────────────────────────────┐
                    │  共享 JSON/FormData 处理         │
                    │  ├─ processWithJson()           │
                    │  └─ processWithFormData()       │
                    └────────────┬────────────────────┘
                                 ↓
                    ┌─────────────────────────────────┐
                    │  后端 API 调用                   │
                    │  └─ axios.post()                │
                    └─────────────────────────────────┘
```

---

## 架构优势总结

| 优势 | 展现 |
|-----|------|
| **低耦合** | 模式映射系统让前端独立于后端 mode 命名 |
| **高内聚** | 每个函数专注一个生成模型 |
| **易扩展** | 新模型 = 1 个函数 + 1 行映射 |
| **易维护** | 共享逻辑集中，改一处生效 |
| **向后兼容** | `chat()` 入口保持不变 |
| **易理解** | 函数名简洁，职责明确 |
| **可测试** | 每个函数相对独立，易单元测试 |

