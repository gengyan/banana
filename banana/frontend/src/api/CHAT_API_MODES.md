/**
 * 前端 Chat API 模式映射指南
 * 
 * 目的：
 * - 统一接口，支持灵活的模式别名
 * - 便于扩展：添加新模型时只需在 MODE_TO_MODEL 中注册
 * - 避免硬编码逻辑，提高代码可维护性
 */

// ==================== 模式映射表（在 chat.js 中） ====================

const MODE_TO_MODEL = {
  // Gemini 2.5 Flash
  'banana': 'gemini25',
  
  // Gemini 3 Pro
  'banana_pro': 'gemini3Pro',
  
  // Imagen 3（预留，后续实现）
  'imagen': 'imagen',
  
  // 聊天
  'chat': 'chatOnly',
}

// ==================== 使用示例 ====================

// 1. 聊天模式
await chatAPI.chat(message, 'chat', history)

// 2. Gemini 2.5 Flash（文生图 + 图生图）
await chatAPI.chat(prompt, 'banana', history)  // 文生图
await chatAPI.chat(prompt, 'banana', history, referenceImages)  // 图生图

// 3. Gemini 3 Pro（文生图 + 图生图）
await chatAPI.chat(prompt, 'banana_pro', history)  // 文生图
await chatAPI.chat(prompt, 'banana_pro', history, referenceImages)  // 图生图

// 4. Imagen 3（预留，后续实现）
await chatAPI.chat(prompt, 'imagen', history)

// 5. 直接调用模型函数（更推荐，更清晰）
await chatAPI.gemini25(prompt, referenceImages, { history })
await chatAPI.gemini3Pro(prompt, referenceImages, { history })
await chatAPI.imagen(prompt, referenceImages, { history })  // 当实现时
await chatAPI.chatOnly(message, { history })

// ==================== 扩展方案 ====================

/**
 * 添加新的生成模型时的步骤：
 * 
 * 1. 添加模式映射
 *    MODE_TO_MODEL['claude_vision'] = 'claudeVision'
 * 
 * 2. 实现模型函数
 *    const claudeVision = async (message, referenceImages = null, options = {}) => {
 *      // 内部自动判断文生图/图生图
 *      if (referenceImages) {
 *        // 调用 /api/claude-vision（FormData）
 *      } else {
 *        // 调用 /api/claude-vision-json（JSON）
 *      }
 *    }
 * 
 * 3. 添加到 chatAPI 导出
 *    export { ..., claudeVision }
 * 
 * 4. 使用
 *    await chatAPI.chat(prompt, 'claude_vision', history)
 *    或
 *    await chatAPI.claudeVision(prompt, referenceImages, { history })
 */

// ==================== 后端接口对应关系 ====================

/*
前端模式        后端 mode       JSON 接口              FormData 接口
─────────────────────────────────────────────────────────────────
'banana'       'banana'       /api/process-json      /api/process
'banana_pro'   'banana_pro'   /api/process-json3     /api/process3
'imagen'       'imagen'       /api/imagen-json       /api/imagen

当后端实现 Imagen 3 接口时，只需在后端添加对应的路由，
前端无需修改，自动通过模式映射调用。
*/

// ==================== 后端实现清单 ====================

/**
 * 当添加新模型时，后端需要实现：
 * 
 * 1. JSON 接口（文生图，用于去重和缓存）
 *    @app.post("/api/{model}-json")
 *    async def {model}_json(request: ProcessJsonRequest):
 *        # 处理提示词和历史，返回图片
 * 
 * 2. FormData 接口（图生图，支持参考图片）
 *    @app.post("/api/{model}")
 *    async def {model}(request: Request):
 *        # 处理 multipart/form-data，支持 reference_images
 *        # 返回二进制图片流或 JSON
 */
