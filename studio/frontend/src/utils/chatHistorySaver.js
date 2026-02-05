/**
 * 聊天记录保存工具模块
 * 统一处理聊天记录和图片的保存逻辑
 */

import { createProject, saveMessage } from './storage'

/**
 * 将图片数据转换为 base64 格式
 * @param {string|Blob|File} imageData - 图片数据（可以是 data URL、Blob 或 File）
 * @returns {Promise<string|null>} base64 格式的图片数据，失败返回 null
 */
async function convertImageToBase64(imageData) {
  if (!imageData) {
    return null
  }

  try {
    // 如果已经是 base64 data URL，直接返回
    if (typeof imageData === 'string' && imageData.startsWith('data:')) {
      return imageData
    }

    // 如果是 URL，需要先下载
    if (typeof imageData === 'string' && (imageData.startsWith('http://') || imageData.startsWith('https://'))) {
      const response = await fetch(imageData)
      const blob = await response.blob()
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result)
        reader.onerror = reject
        reader.readAsDataURL(blob)
      })
    }

    // 如果是 Blob 或 File，直接读取
    if (imageData instanceof Blob || imageData instanceof File) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result)
        reader.onerror = reject
        reader.readAsDataURL(imageData)
      })
    }

    // 其他情况，尝试转换为 Blob 再读取
    if (typeof imageData === 'object') {
      try {
        const blob = new Blob([imageData], { type: 'image/png' })
        return new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onloadend = () => resolve(reader.result)
          reader.onerror = reject
          reader.readAsDataURL(blob)
        })
      } catch (e) {
        console.warn('⚠️ 图片数据转换失败:', e)
        return null
      }
    }

    console.warn('⚠️ 不支持的图片数据类型:', typeof imageData)
    return null
  } catch (error) {
    console.error('❌ 图片转换为 base64 失败:', error)
    return null
  }
}

/**
 * 确保项目存在，如果不存在则创建
 * @param {string|null} currentProjectId - 当前项目ID
 * @param {string} message - 用户消息（用于生成项目标题）
 * @param {Function} createNewProject - 创建项目的函数
 * @returns {Promise<string>} 项目ID
 */
async function ensureProjectExists(currentProjectId, message, createNewProject) {
  if (currentProjectId) {
    console.log('📋 使用现有项目:', currentProjectId)
    return currentProjectId
  }

  try {
    console.log('📦 会话开始：创建新项目')
    const projectTitle = message ? message.substring(0, 30) || '新项目' : '新项目'
    console.log('📦 项目标题:', projectTitle)
    const project = await createNewProject(projectTitle)
    console.log('✅ 新项目已创建:', project)
    if (!project || !project.id) {
      throw new Error('创建项目失败：返回的项目对象无效')
    }
    return project.id
  } catch (error) {
    console.error('❌ 创建项目失败:', error)
    throw new Error(`创建项目失败: ${error.message || '未知错误'}`)
  }
}

/**
 * 保存聊天记录和图片
 * @param {Object} options - 保存选项
 * @param {string|null} options.currentProjectId - 当前项目ID
 * @param {Function} options.createNewProject - 创建项目的函数
 * @param {string} options.userMessage - 用户消息内容
 * @param {string|Blob|File|null} options.referenceImage - 参考图片（可选）
 * @param {string|Blob|File|null} options.aiImageData - AI生成的图片数据（可选）
 * @param {string} options.aiResponse - AI回复内容
 * @param {string} options.source - 来源标识（用于日志，如 'Home' 或 'Working'）
 * @returns {Promise<{success: boolean, projectId: string|null, error?: string}>}
 */
export async function saveChatHistory({
  currentProjectId,
  createNewProject,
  userMessage,
  referenceImage = null,
  aiImageData = null,
  aiResponse = '',
  source = 'Unknown'
}) {
  try {
    console.log(`💾 [${source}] 开始保存聊天记录...`, {
      hasCurrentProjectId: !!currentProjectId,
      currentProjectId,
      hasCreateNewProject: typeof createNewProject === 'function',
      userMessageLength: userMessage?.length || 0,
      hasReferenceImage: !!referenceImage,
      hasAiImageData: !!aiImageData,
      aiResponseLength: aiResponse?.length || 0
    })

    // 1. 确保项目存在
    const targetProjectId = await ensureProjectExists(
      currentProjectId,
      userMessage,
      createNewProject
    )

    if (!targetProjectId) {
      throw new Error('无法获取项目ID，保存失败')
    }

    // 2. 转换参考图为 base64（如果有）
    // ⚠️ 重要：不存储大 Base64 图片数据，只标记有图片
    let referenceImageBase64 = null
    if (referenceImage) {
      // 检查图片大小，如果超过 100KB，不存储 Base64
      const isLargeImage = typeof referenceImage === 'string' && referenceImage.length > 100000
      
      if (isLargeImage) {
        console.log(`🖼️ [${source}] 参考图较大，不存储 Base64 数据以避免存储溢出`)
        referenceImageBase64 = null
      } else {
        console.log(`🖼️ [${source}] 转换参考图为 base64（小图片）...`)
        referenceImageBase64 = await convertImageToBase64(referenceImage)
        if (referenceImageBase64) {
          console.log(`✅ [${source}] 参考图转换成功，长度: ${referenceImageBase64.length} 字符`)
        } else {
          console.warn(`⚠️ [${source}] 参考图转换失败，将保存为 null`)
        }
      }
    }

    // 3. 处理AI生成的图片（如果有）
    // ⚠️ 重要：IndexedDB 支持存储大图片，直接传递 Blob 对象或转换为 base64
    // saveMessage 会自动处理：大图片存储到独立的 images 存储，小图片直接存储在消息中
    let aiImageBase64 = null
    let aiImageBlob = null
    
    if (aiImageData) {
      // ⚠️ 重要：如果 aiImageData 是 Blob 对象（process-json3 返回），直接使用，不转换
      // ⚠️ 关键修复：直接传递 Blob 对象给 saveMessage，不要转换为 Base64
      if (aiImageData instanceof Blob) {
        console.log(`🖼️ [${source}] 检测到 Blob 对象，直接传递 Blob 对象（不转换为 Base64）`)
        aiImageBlob = aiImageData
        // ⚠️ 重要：不要转换为 Base64，直接传递 Blob 对象
        // saveMessage 会直接存储 Blob 对象到 IndexedDB
        aiImageBase64 = null  // 不转换为 Base64，直接使用 Blob
        console.log(`✅ [${source}] 将直接传递 Blob 对象给 saveMessage，大小: ${(aiImageData.size / 1024).toFixed(2)} KB`)
      } else {
        // 字符串格式（Data URL 或 Base64）：转换为 base64
        console.log(`🖼️ [${source}] 转换AI生成的图片为 base64...`)
        aiImageBase64 = await convertImageToBase64(aiImageData)
        if (aiImageBase64) {
          console.log(`✅ [${source}] AI图片转换成功，长度: ${aiImageBase64.length} 字符 (${(aiImageBase64.length / 1024).toFixed(2)} KB)`)
        } else {
          console.warn(`⚠️ [${source}] AI图片转换失败，将保存为 null`)
        }
      }
    }

    // 4. 保存用户消息
    console.log(`💬 [${source}] 保存用户消息...`, {
      projectId: targetProjectId,
      contentLength: userMessage?.length || 0,
      hasImage: !!referenceImageBase64,
      imageLength: referenceImageBase64?.length || 0
    })
    try {
      await saveMessage(targetProjectId, {
        role: 'user',
        content: userMessage,
        imageData: referenceImageBase64
      })
      console.log(`✅ [${source}] 用户消息已保存`)
    } catch (saveError) {
      console.error(`❌ [${source}] 保存用户消息失败:`, saveError)
      console.error(`❌ [${source}] 错误详情:`, {
        message: saveError.message,
        stack: saveError.stack,
        name: saveError.name
      })
      throw new Error(`保存用户消息失败: ${saveError.message || '未知错误'}`)
    }

    // 5. 保存AI回复
    console.log(`🤖 [${source}] 保存AI回复...`, {
      projectId: targetProjectId,
      contentLength: aiResponse?.length || 0,
      hasImage: !!(aiImageBlob || aiImageBase64),
      hasBlob: aiImageBlob instanceof Blob,
      hasBase64: !!aiImageBase64,
      blobSize: aiImageBlob ? `${(aiImageBlob.size / 1024).toFixed(2)} KB` : 'N/A',
      base64Length: aiImageBase64 ? `${(aiImageBase64.length / 1024).toFixed(2)} KB` : 'N/A'
    })
    try {
      // ⚠️ 关键修复：如果 aiImageBlob 存在（Blob 对象），直接传递 Blob 对象
      // 不要传递 Blob URL 字符串或 Base64，直接传递 Blob 对象本身
      // ⚠️ 重要：优先使用 Blob 对象，不要转换为 Base64
      const imageDataToSave = aiImageBlob || aiImageBase64
      console.log(`💾 [${source}] 保存图片数据:`, {
        isBlob: aiImageBlob instanceof Blob,
        isBase64: !!aiImageBase64 && !aiImageBlob,
        blobSize: aiImageBlob ? `${(aiImageBlob.size / 1024).toFixed(2)} KB` : 'N/A',
        base64Length: aiImageBase64 ? `${(aiImageBase64.length / 1024).toFixed(2)} KB` : 'N/A',
        dataType: imageDataToSave ? (imageDataToSave instanceof Blob ? 'Blob' : typeof imageDataToSave) : 'null'
      })
      
      await saveMessage(targetProjectId, {
        role: 'assistant',
        content: aiResponse || '无响应',
        imageData: imageDataToSave  // 直接传递 Blob 对象或 Base64 字符串（优先 Blob）
      })
      console.log(`✅ [${source}] AI回复已保存`)
    } catch (saveError) {
      console.error(`❌ [${source}] 保存AI回复失败:`, saveError)
      console.error(`❌ [${source}] 错误详情:`, {
        message: saveError.message,
        stack: saveError.stack,
        name: saveError.name
      })
      throw new Error(`保存AI回复失败: ${saveError.message || '未知错误'}`)
    }

    console.log(`✅ [${source}] 聊天记录和图片已保存到项目库，项目ID: ${targetProjectId}（共2条消息）`)

    return {
      success: true,
      projectId: targetProjectId
    }
  } catch (error) {
    console.error(`❌ [${source}] 保存聊天记录失败:`, error)
    console.error(`❌ [${source}] 错误堆栈:`, error.stack)
    console.error(`❌ [${source}] 错误详情:`, {
      name: error.name,
      message: error.message,
      stack: error.stack,
      cause: error.cause
    })
    
    // 尝试获取更详细的错误信息
    let errorMessage = error.message || '保存失败'
    if (error.name === 'QuotaExceededError' || error.code === 22 || error.code === 1014) {
      errorMessage = '存储空间不足，请清理项目库中的旧项目后重试'
    } else if (error.message && error.message.includes('QuotaExceededError')) {
      errorMessage = '存储空间不足，请清理项目库中的旧项目后重试'
    }
    
    return {
      success: false,
      projectId: null,
      error: errorMessage
    }
  }
}

/**
 * 保存聊天记录（简化版本，用于错误情况）
 * @param {Object} options - 保存选项
 * @param {string|null} options.currentProjectId - 当前项目ID
 * @param {Function} options.createNewProject - 创建项目的函数
 * @param {string} options.userMessage - 用户消息内容
 * @param {string} options.errorMessage - 错误消息
 * @param {string} options.source - 来源标识
 * @returns {Promise<{success: boolean, projectId: string|null, error?: string}>}
 */
export async function saveChatHistoryWithError({
  currentProjectId,
  createNewProject,
  userMessage,
  errorMessage,
  source = 'Unknown'
}) {
  try {
    console.log(`💾 [${source}] 开始保存错误响应...`)

    const targetProjectId = await ensureProjectExists(
      currentProjectId,
      userMessage,
      createNewProject
    )

    if (!targetProjectId) {
      throw new Error('无法获取项目ID，保存失败')
    }

    // 保存用户消息
    await saveMessage(targetProjectId, {
      role: 'user',
      content: userMessage,
      imageData: null
    })

    // 保存错误响应
    await saveMessage(targetProjectId, {
      role: 'assistant',
      content: `错误: ${errorMessage}`,
      imageData: null
    })

    console.log(`✅ [${source}] 错误响应已保存到项目库，项目ID: ${targetProjectId}`)

    return {
      success: true,
      projectId: targetProjectId
    }
  } catch (error) {
    console.error(`❌ [${source}] 保存错误响应失败:`, error)
    return {
      success: false,
      projectId: null,
      error: error.message || '保存失败'
    }
  }
}

