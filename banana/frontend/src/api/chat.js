/**
 * 聊天和图片生成 API - v2
 * 重构：按生成模型维度拆分（而非按任务类型）
 * 
 * 架构理念：
 * - 领域模型 = 生成模型（Gemini 2.5、Gemini 3 Pro、Imagen 3）
 * - 一个模型 = 一个函数
 * - 参数驱动逻辑：根据是否有参考图自动选择策略（JSON接口 vs FormData接口）
 * - 模式映射：支持多种模式别名，便于扩展
 */

import axios from 'axios'
import client from './client'
import { API_BASE_URL } from '../config/api'
import logger from '../utils/logger'
import { saveImageBlob } from '../utils/indexedDBStorage'

// 防重复调用：使用 Promise 复用机制
const pendingProcessPromises = new Map()

// ==================== 模式映射表 ====================
/**
 * 模式映射：用户传入的 mode → 对应的模型函数
 * 支持灵活的别名系统，便于后续扩展
 */
const MODE_TO_MODEL = {
  // Gemini 2.5 Flash
  'banana': 'gemini25',
  
  // Gemini 3 Pro
  'banana_pro': 'gemini3Pro',
  
  // Imagen 3（预留，后续实现）
  'imagen': 'imagen',
  
  // 默认聊天模式
  'chat': 'chatOnly',
}

// ==================== 辅助函数 ====================

/**
 * 处理 Blob 响应，支持嗅探和转换多种格式
 */
const processBlobResponse = async (blob, headers, modelVersion) => {
  const contentType = headers['content-type'] || ''
  const mimeType = contentType.split(';')[0].trim().toLowerCase()

  // 嗅探前缀，识别 JSON / dataURL / 裸 base64
  const headText = await blob.slice(0, 120).text().catch(() => '')
  const trimmedHead = headText.trim()
  const looksLikeJson = trimmedHead.startsWith('{') || trimmedHead.startsWith('[')
  const looksLikeDataUrl = trimmedHead.startsWith('data:image')
  const looksLikeBase64 = trimmedHead.length > 30 && /^[A-Za-z0-9+/=\s]+$/.test(trimmedHead)
  const isJsonByHeader = mimeType === 'application/json' || mimeType.includes('json')
  const shouldTreatAsText = isJsonByHeader || (trimmedHead.length > 0 && (looksLikeJson || looksLikeDataUrl || looksLikeBase64))

  if (shouldTreatAsText) {
    try {
      const text = await blob.text()
      
      // JSON 格式
      if (looksLikeJson || isJsonByHeader) {
        const jsonData = JSON.parse(text)
        if (jsonData && jsonData.image_data) {
          return convertBase64ToBlob(jsonData.image_data, jsonData.image_format || 'jpeg', jsonData.model_version || modelVersion, jsonData.response)
        }
        return jsonData
      }
      
      // Data URL 格式
      if (looksLikeDataUrl) {
        const [headerPart, dataPart] = text.split(',')
        const mimeMatch = headerPart.match(/data:([^;]+)/)
        const inferredFormat = (mimeMatch?.[1] || 'image/jpeg').replace('image/', '')
        return convertBase64ToBlob(dataPart, inferredFormat, modelVersion)
      }
      
      // 裸 Base64 格式
      if (looksLikeBase64) {
        const inferredFormat = mimeType.includes('png') ? 'png' : 'jpeg'
        return convertBase64ToBlob(text.replace(/\s+/g, ''), inferredFormat, modelVersion)
      }
    } catch (textParseError) {
      console.error('❌ 文本嗅探解析失败，回退为原始 Blob', textParseError)
    }
  }

  // 原始二进制图片流
  const format = mimeType.includes('png') ? 'png' : (mimeType.includes('jpeg') || mimeType.includes('jpg') ? 'jpeg' : 'jpeg')
  const modelName = getModelName(modelVersion)
  
  return {
    success: true,
    image_blob: blob,
    image_format: format,
    model_version: modelVersion,
    response: `图片生成成功！(${modelName})`,
    is_blob: true
  }
}

/**
 * 将 Base64 字符串转换为 Blob
 */
const convertBase64ToBlob = (base64String, format, modelVersion, response = null) => {
  try {
    const raw = atob(base64String)
    const view = new Uint8Array(raw.length)
    for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
    const blob = new Blob([view], { type: `image/${format}` })
    
    return {
      success: true,
      image_blob: blob,
      image_format: format,
      model_version: modelVersion,
      response: response || '图片生成成功（本地解码）',
      is_blob: true
    }
  } catch (error) {
    console.error('❌ Base64 转 Blob 失败，回退为 data URL:', error)
    const dataUrl = base64String.startsWith('data:')
      ? base64String
      : `data:image/${format};base64,${base64String}`
    return {
      success: true,
      image_data: dataUrl,
      image_format: format,
      model_version: modelVersion,
      response: response || '图片生成成功（Base64 回退）',
      is_blob: false
    }
  }
}

/**
 * 获取模型友好名称
 */
const getModelName = (modelVersion) => {
  switch (modelVersion) {
    case '2.5': return 'Gemini 2.5 Flash'
    case '3_pro': return 'Gemini 3 Pro'
    case 'imagen': return 'Imagen 3'
    default: return `Gemini ${modelVersion}`
  }
}

/**
 * 生成请求缓存键
 */
const generateRequestKey = (message, mode, aspectRatio, resolution, temperature) => {
  return JSON.stringify({
    message: message.substring(0, 2000),
    mode: mode || 'chat',
    aspectRatio: aspectRatio || null,
    resolution: resolution || null,
    temperature: temperature || null
  })
}

// ==================== 通用处理逻辑 ====================

/**
 * 使用 FormData 接口（支持参考图片）
 * @param {string} message - 提示词
 * @param {Array<File>|File|null} referenceImages - 参考图片
 * @param {string} endpoint - API 端点（如 /api/banana-img 或 /api/process3）
 * @param {string} mode - 模式（'banana' 或 'banana_pro'）
 * @param {string} modelVersion - 模型版本
 * @param {Object} options - 其他选项
 */
const processWithFormData = async (message, referenceImages, endpoint, mode, modelVersion, options = {}) => {
  const { aspectRatio, resolution, temperature, history } = options
  
  const formData = new FormData()
  formData.append('message', message)
  formData.append('mode', mode)
  formData.append('skip_optimization', 'true')
  
  if (history && history.length > 0) {
    formData.append('history', JSON.stringify(history))
  }
  if (aspectRatio) formData.append('aspect_ratio', aspectRatio)
  if (resolution) formData.append('resolution', resolution)
  if (temperature !== null && temperature !== undefined) {
    formData.append('temperature', temperature.toString())
  }
  
  // 添加参考图片
  if (referenceImages) {
    const images = Array.isArray(referenceImages) ? referenceImages : [referenceImages]
    images.forEach((image) => {
      if (image) formData.append('reference_images', image)
    })
  }

  const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, {
    headers: {
      // ⚠️ 让浏览器自动生成 multipart boundary，避免手动设置导致文件被忽略
      'Accept': 'application/json,image/*,text/plain'
    },
    // ⚠️ 关键修复：设置 responseType 为 'arraybuffer' 以便正确接收 Blob 响应
    // axios 会根据 Content-Type 自动判断：
    // - Content-Type: image/* → 转换为 Blob
    // - Content-Type: application/json → 保持为对象
    responseType: 'arraybuffer',
    timeout: 300000,
    maxContentLength: 50 * 1024 * 1024,
    maxBodyLength: 50 * 1024 * 1024,
  })

  // 调试日志
  console.log(`📥 [processWithFormData] 收到响应:`, {
    status: response.status,
    contentType: response.headers['content-type'],
    dataType: typeof response.data,
    isArrayBuffer: response.data instanceof ArrayBuffer,
    size: response.data?.byteLength || response.data?.length
  })

  // 处理 arraybuffer 响应
  if (response.data instanceof ArrayBuffer) {
    // 根据 Content-Type 判断是 JSON 还是二进制图片
    const contentType = response.headers['content-type'] || ''
    const isJson = contentType.includes('application/json')
    
    if (isJson) {
      // JSON 格式：转换为文本，然后解析
      const decoder = new TextDecoder()
      const text = decoder.decode(response.data)
      console.log('📝 [processWithFormData] 解析 JSON 响应')
      const jsonData = JSON.parse(text)
      
      if (jsonData.image_data) {
        return convertBase64ToBlob(jsonData.image_data, jsonData.image_format || 'jpeg', modelVersion, jsonData.response)
      } else if (jsonData.success === false) {
        throw new Error(jsonData.response || jsonData.error_message || '图片生成失败')
      }
      return jsonData
    } else {
      // 二进制图片数据：转换为 Blob
      console.log('🖼️ [processWithFormData] 处理二进制图片响应')
      const blob = new Blob([response.data], { type: contentType || 'image/jpeg' })
      return await processBlobResponse(blob, response.headers, modelVersion)
    }
  } else if (typeof response.data === 'object') {
    // 纯对象响应（某些情况下 axios 可能已处理）
    if (response.data.image_data) {
      console.log('✅ [processWithFormData] 收到 JSON 格式响应，转换为 Blob')
      return convertBase64ToBlob(response.data.image_data, response.data.image_format || 'jpeg', modelVersion, response.data.response)
    } else if (response.data.success === false) {
      console.error('❌ [processWithFormData] 收到错误响应:', response.data)
      throw new Error(response.data.response || response.data.error_message || '图片生成失败')
    }
    return response.data
  }
  
  console.warn('⚠️ [processWithFormData] 未知响应格式:', typeof response.data)
  return response.data
}

/**
 * 使用 JSON 接口（仅支持提示词，不支持参考图片）
 * @param {string} message - 提示词
 * @param {string} endpoint - API 端点（如 /api/banana-img）
 * @param {string} mode - 模式
 * @param {string} modelVersion - 模型版本
 * @param {Object} options - 其他选项
 */
const processWithJson = async (message, endpoint, mode, modelVersion, options = {}) => {
  const { aspectRatio, resolution, temperature, history } = options
  
  const payload = {
    message,
    mode,
    history: history || [],
    skip_optimization: true,
  }
  if (aspectRatio) payload.aspect_ratio = aspectRatio
  if (resolution) payload.resolution = resolution
  if (temperature !== null && temperature !== undefined) payload.temperature = temperature
  
  // banana-img 接口返回二进制图片数据（不是JSON），必须用 blob 类型
  const response = await client.post(endpoint, payload, {
    responseType: 'blob',
    headers: { Accept: 'application/json,image/*,text/plain' },
    timeout: 300000,
    maxContentLength: 50 * 1024 * 1024,
    maxBodyLength: 50 * 1024 * 1024,
  })
  
  console.log(`📥 [processWithJson] 收到响应:`, {
    endpoint,
    dataType: typeof response.data,
    isBlob: response.data instanceof Blob,
    hasImageData: response.data?.image_data ? 'yes' : 'no',
    success: response.data?.success
  })
  
  // 新格式：JSON 响应，包含 image_data 等字段
  if (typeof response.data === 'object' && response.data.image_data) {
    console.log('✅ [processWithJson] 转换 Base64 为 Blob')
    return convertBase64ToBlob(response.data.image_data, response.data.image_format || 'jpeg', modelVersion, response.data.response)
  }
  
  // 错误响应
  if (typeof response.data === 'object' && response.data.success === false) {
    console.error('❌ [processWithJson] 收到错误响应:', response.data)
    throw new Error(response.data.response || response.data.error_message || '图片生成失败')
  }
  
  // 旧格式：Blob 响应（纯图片二进制）
  if (response.data instanceof Blob) {
    console.log('📦 [processWithJson] 处理 Blob 响应')
    return await processBlobResponse(response.data, response.headers, modelVersion)
  }
  
  console.warn('⚠️ [processWithJson] 未知响应格式:', typeof response.data)
  return response.data
}

// ==================== 模型适配器 ====================

/**
 * Gemini 2.5 Flash 模型
 * 自动判断文生图/图生图
 * @param {string} message - 提示词
 * @param {Array<File>|File|null} referenceImages - 参考图片（可选）
 * @param {Object} options - 其他选项 { history, aspectRatio, resolution, temperature }
 */
const gemini25 = async (message, referenceImages = null, options = {}) => {
  const hasImages = referenceImages && (
    (Array.isArray(referenceImages) && referenceImages.length > 0) ||
    referenceImages instanceof File
  )
  
  try {
    // 有参考图：使用 FormData 接口
    if (hasImages) {
      console.log('🎨 [Gemini 2.5] 图生图模式（FormData）')
      return await processWithFormData(message, referenceImages, '/api/banana-img', 'banana', '2.5', options)
    }
    
    // 无参考图：优先用 JSON，失败回退到 FormData
    console.log('🎨 [Gemini 2.5] 文生图模式（JSON 接口）')
    try {
      const requestKey = generateRequestKey(message, 'banana', options.aspectRatio, options.resolution, options.temperature)
      
      if (pendingProcessPromises.has(requestKey)) {
        console.log(`♻️ 复用已存在的 Gemini 2.5 请求`)
        return pendingProcessPromises.get(requestKey)
      }
      
      const promise = processWithJson(message, '/api/banana-img', 'banana', '2.5', options)
      pendingProcessPromises.set(requestKey, promise)
      
      const result = await promise
      pendingProcessPromises.delete(requestKey)
      return result
    } catch (error) {
      // JSON 接口失败，回退到 FormData
      console.warn('🟡 [Gemini 2.5] JSON 接口失败，回退到 FormData')
      return await processWithFormData(message, null, '/api/banana-img', 'banana', '2.5', options)
    }
  } catch (error) {
    console.error('❌ [Gemini 2.5] 请求失败:', error.message)
    throw error
  }
}

/**
 * Gemini 3 Pro 模型
 * 自动判断文生图/图生图
 * @param {string} message - 提示词
 * @param {Array<File>|File|null} referenceImages - 参考图片（可选）
 * @param {Object} options - 其他选项
 */
const gemini3Pro = async (message, referenceImages = null, options = {}) => {
  // ⚠️ 调试：输出 referenceImages 的详细信息
  console.log(`📦 [Gemini 3 Pro] 收到的 referenceImages:`, {
    type: Array.isArray(referenceImages) ? 'Array' : (referenceImages instanceof File ? 'File' : typeof referenceImages),
    length: Array.isArray(referenceImages) ? referenceImages.length : 'N/A',
    isNull: referenceImages === null,
    isUndefined: referenceImages === undefined,
    isEmptyArray: Array.isArray(referenceImages) && referenceImages.length === 0,
    value: referenceImages
  })
  
  const hasImages = referenceImages && (
    (Array.isArray(referenceImages) && referenceImages.length > 0) ||
    referenceImages instanceof File
  )
  
  try {
    // ⚠️ 重要修复：统一使用 processWithFormData，支持参考图和无参考图
    // 这样避免了前端 state 同步问题导致参考图丢失
    console.log(`🎨 [Gemini 3 Pro] 统一使用 FormData 方式（支持参考图和无参考图）`)
    return await processWithFormData(message, referenceImages, '/api/banana-img-pro', 'banana_pro', '3_pro', options)
  } catch (error) {
    console.error('❌ [Gemini 3 Pro] 请求失败:', error.message)
    throw error
  }
}

/**
 * Imagen 3 模型（当前预留，后续实现）
 * @param {string} message - 提示词
 * @param {Array<File>|File|null} referenceImages - 参考图片（可选）
 * @param {Object} options - 其他选项
 */
const imagen = async (message, referenceImages = null, options = {}) => {
  // 当前预留，后续实现
  throw new Error('❌ Imagen 3 接口尚未实现，敬请期待！')
}



/**
 * 纯文本聊天（支持可选的参考图片）
 * @param {string} message - 消息内容
 * @param {Array<File>|File|null} referenceImages - 参考图片（可选）
 * @param {Object} options - 其他选项 { history, temperature }
 */
const chatOnly = async (message, referenceImages = null, options = {}) => {
  const { temperature, history } = options
  
  const requestKey = generateRequestKey(message, 'chat', null, null, temperature)
  
  if (pendingProcessPromises.has(requestKey)) {
    console.log(`♻️ 复用已存在的聊天请求`)
    return pendingProcessPromises.get(requestKey)
  }
  
  const promise = (async () => {
    try {
      // 判断是否有参考图片
      const hasImages = referenceImages && (
        (Array.isArray(referenceImages) && referenceImages.length > 0) ||
        referenceImages instanceof File
      )
      
      // 有参考图：使用 /api/chat-with-images（FormData）
      if (hasImages) {
        console.log('💬 [聊天+图片] 使用 FormData 接口发送参考图片')
        
        const formData = new FormData()
        formData.append('message', message)
        formData.append('mode', 'chat')
        
        if (history && history.length > 0) {
          formData.append('history', JSON.stringify(history))
        }
        if (temperature !== null && temperature !== undefined) {
          formData.append('temperature', temperature.toString())
        }
        
        // 添加参考图片
        const images = Array.isArray(referenceImages) ? referenceImages : [referenceImages]
        images.forEach((image) => {
          if (image) formData.append('reference_images', image)
        })
        
        const response = await axios.post(`${API_BASE_URL}/api/chat-with-images`, formData, {
          headers: {
            // 让 axios 自动设置 multipart/form-data + boundary
            // 不要设置 Content-Type，让 FormData 处理
          },
          timeout: 300000,
          maxContentLength: 50 * 1024 * 1024,
          maxBodyLength: 50 * 1024 * 1024,
        })
        
        console.log(`✅ [聊天+图片] 响应成功`, response.data)
        return response.data
      }
      
      // 无参考图：使用 /api/chat（JSON）
      console.log('💬 [纯文本聊天] 使用 JSON 接口')
      
      const payload = {
        message,
        mode: 'chat',
        history: history || [],
      }
      if (temperature !== null && temperature !== undefined) {
        payload.temperature = temperature
      }
      
      const response = await client.post('/api/chat', payload)
      console.log(`✅ [纯文本聊天] 响应成功`, response.data)
      return response.data
      
    } catch (error) {
      console.error('❌ [聊天] 请求失败:', error.message)
      throw error
    } finally {
      pendingProcessPromises.delete(requestKey)
    }
  })()
  
  pendingProcessPromises.set(requestKey, promise)
  return promise
}

// ==================== 统一入口（向后兼容 + 灵活扩展）====================

const chatAPI = {
  /**
   * 聊天/图片生成统一接口（兼容旧版本 + 支持灵活扩展）
   * 
   * 支持的 mode 值：
   * - 'chat' → 纯文本聊天
   * - 'banana' → Gemini 2.5 Flash（文生图/图生图）
   * - 'banana_pro' → Gemini 3 Pro（文生图/图生图）
   * - 'imagen' → Imagen 3（文生图/图生图，预留）
   * 
   * 使用示例：
   * - chatAPI.chat(message, 'chat', history) → 聊天
   * - chatAPI.chat(message, 'banana', history, refImages) → Gemini 2.5 生图
   * - chatAPI.chat(message, 'banana_pro', history, refImages) → Gemini 3 Pro 生图
   * - chatAPI.chat(message, 'imagen', history, refImages) → Imagen 3 生图
   */
  chat: async (message, mode = 'chat', history = [], referenceImages = null, aspectRatio = null, resolution = null, temperature = null) => {
    console.log(`🎯 [chatAPI.chat] 调用参数:`, {
      message: message.substring(0, 50) + (message.length > 50 ? '...' : ''),
      mode,
      history_length: history?.length || 0,
      referenceImages_type: Array.isArray(referenceImages) ? 'Array' : (referenceImages instanceof File ? 'File' : typeof referenceImages),
      referenceImages_length: Array.isArray(referenceImages) ? referenceImages.length : 'N/A',
      referenceImages_value: referenceImages
    })
    
    const hasImages = referenceImages && (
      (Array.isArray(referenceImages) && referenceImages.length > 0) ||
      (!Array.isArray(referenceImages) && referenceImages)
    )
    
    console.log(`📌 [chatAPI.chat] hasImages = ${hasImages}`)
    
    const options = { aspectRatio, resolution, temperature, history }
    
    // 使用模式映射表查找对应的模型函数
    const modelFnName = MODE_TO_MODEL[mode] || MODE_TO_MODEL['chat']
    const modelFn = chatAPI[modelFnName]
    
    if (!modelFn) {
      throw new Error(`❌ 未知的生成模式: "${mode}"。支持的模式: ${Object.keys(MODE_TO_MODEL).join(', ')}`)
    }
    
    // 聊天模式下将参考图片传入
    if (modelFnName === 'chatOnly') {
      return await modelFn(message, hasImages ? referenceImages : null, options)
    }
    
    // 调用对应的模型函数
    return await modelFn(message, hasImages ? referenceImages : null, options)
  },
  
  // 导出具体模型函数，供精细控制和直接调用
  gemini25,
  gemini3Pro,
  imagen,
  chatOnly,
}

export default chatAPI
