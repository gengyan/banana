/**
 * 聊天和图片生成相关 API
 */

import axios from 'axios'
import client from './client'
import { API_BASE_URL } from '../config/api'
import logger from '../utils/logger'

// 防重复调用：使用 Promise 复用机制
const pendingProcessPromises = new Map()   // process-json 的 Promise 复用映射表

const chatAPI = {


  /**
   * 聊天/图片生成接口
   * @param {string} message - 消息内容
   * @param {string} mode - 模式（'chat' 或 'banana'）
   * @param {Array} history - 历史对话记录
   * @param {File|Array<File>} referenceImages - 参考图片（可选）
   * @param {string} aspectRatio - 图片宽高比（可选）
   * @param {string} resolution - 分辨率（可选）
   * @param {number} temperature - 温度参数（可选，默认 0.3）
   * @returns {Promise<Object>} 处理结果
   */
  chat: async (message, mode = 'chat', history = [], referenceImages = null, aspectRatio = null, resolution = null, temperature = null) => {
    // 支持多张参考图片（可以是单个文件或文件数组）
    const hasImages = referenceImages && (
      (Array.isArray(referenceImages) && referenceImages.length > 0) ||
      (!Array.isArray(referenceImages) && referenceImages)
    )
    
    // 调试：打印参数信息
    console.log('chatAPI.chat 调用:', {
      mode,
      hasImages,
      imageCount: Array.isArray(referenceImages) ? referenceImages.length : (referenceImages ? 1 : 0)
    })
    
    // 生图模式（banana/banana_pro）：根据是否有参考图决定流程
    if (mode === 'banana' || mode === 'banana_pro' || mode === 'image_generation') {
      if (hasImages) {
        // 图生图：直接调用 process 接口，不优化提示词
        console.log(`🎨 [${Date.now()}] 图生图模式：直接调用 process 接口（不优化提示词）`)
        
        try {
          const formData = new FormData()
          formData.append('message', message)
          formData.append('mode', mode)
          formData.append('skip_optimization', 'true')
          
          // 明确标识使用的模式
          const modelInfo = mode === 'banana' ? 'Gemini 2.5 Flash' :
                           mode === 'banana_pro' ? 'Gemini 3 Pro' : mode
          console.log(`🎨 图生图模式 (${mode}): ${modelInfo}`)
          
          if (history && history.length > 0) {
            formData.append('history', JSON.stringify(history))
          }
          if (aspectRatio) {
            formData.append('aspect_ratio', aspectRatio)
          }
          if (resolution) {
            formData.append('resolution', resolution)
          }
          if (temperature !== null && temperature !== undefined) {
            formData.append('temperature', temperature.toString())
          }
          
          // 支持多张图片
          const images = Array.isArray(referenceImages) ? referenceImages : [referenceImages]
          images.forEach((image) => {
            if (image) {
              formData.append('reference_images', image)
            }
          })
          
          // 根据 mode 选择 API 端点
          const apiEndpoint = mode === 'banana_pro' ? '/api/process3' : '/api/process'

          // 统一以 Blob 方式接收响应，兼容二进制/JSON/dataURL/base64
          const response = await axios.post(`${API_BASE_URL}${apiEndpoint}`, formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
              'Accept': 'image/*,application/json,text/plain'
            },
            responseType: 'blob',
            timeout: 300000,
            maxContentLength: 50 * 1024 * 1024,
            maxBodyLength: 50 * 1024 * 1024,
          })
          console.log(`✅ 图生图请求成功，状态: ${response.status}`)

          // 处理 Blob 响应（含嗅探/转换）
          let result
          if (response.data instanceof Blob) {
            const contentType = response.headers['content-type'] || ''
            const mimeType = contentType.split(';')[0].trim().toLowerCase()
            const blobSize = response.data.size || 0
            console.log(`📦 [图生图] Blob 详情: contentType='${contentType}', size=${blobSize} bytes`)

            // 嗅探前缀，识别 JSON / dataURL / 裸 base64
            const headText = await response.data.slice(0, 120).text().catch(() => '')
            const trimmedHead = headText.trim()
            const looksLikeJson = trimmedHead.startsWith('{') || trimmedHead.startsWith('[')
            const looksLikeDataUrl = trimmedHead.startsWith('data:image')
            const looksLikeBase64 = trimmedHead.length > 30 && /^[A-Za-z0-9+/=\s]+$/.test(trimmedHead)
            const isJsonByHeader = mimeType === 'application/json' || mimeType.includes('json')
            const shouldTreatAsText = isJsonByHeader || (trimmedHead.length > 0 && (looksLikeJson || looksLikeDataUrl || looksLikeBase64))

            if (shouldTreatAsText) {
              try {
                const text = await response.data.text()
                if (looksLikeJson || isJsonByHeader) {
                  const jsonData = JSON.parse(text)
                  if (jsonData && jsonData.image_data) {
                    const raw = atob(jsonData.image_data)
                    const view = new Uint8Array(raw.length)
                    for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                    const inferredFormat = jsonData.image_format || 'jpeg'
                    const blob = new Blob([view], { type: `image/${inferredFormat}` })
                    result = {
                      success: true,
                      image_blob: blob,
                      image_format: inferredFormat,
                      model_version: jsonData.model_version || (mode === 'banana' ? '2.5' : '3_pro'),
                      response: jsonData.response || '图片生成成功（本地解码）',
                      is_blob: true
                    }
                  } else {
                    result = jsonData
                  }
                } else if (looksLikeDataUrl) {
                  const [headerPart, dataPart] = text.split(',')
                  const mimeMatch = headerPart.match(/data:([^;]+)/)
                  const inferredFormat = (mimeMatch?.[1] || 'image/jpeg').replace('image/', '')
                  const raw = atob(dataPart)
                  const view = new Uint8Array(raw.length)
                  for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                  const blob = new Blob([view], { type: `image/${inferredFormat}` })
                  result = {
                    success: true,
                    image_blob: blob,
                    image_format: inferredFormat,
                    model_version: mode === 'banana' ? '2.5' : '3_pro',
                    response: '图片生成成功（本地解码）',
                    is_blob: true
                  }
                } else if (looksLikeBase64) {
                  const raw = atob(text.replace(/\s+/g, ''))
                  const view = new Uint8Array(raw.length)
                  for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                  const inferredFormat = mimeType.includes('png') ? 'png' : 'jpeg'
                  const blob = new Blob([view], { type: `image/${inferredFormat}` })
                  result = {
                    success: true,
                    image_blob: blob,
                    image_format: inferredFormat,
                    model_version: mode === 'banana' ? '2.5' : '3_pro',
                    response: '图片生成成功（本地解码）',
                    is_blob: true
                  }
                }
              } catch (textParseError) {
                console.error('❌ 文本嗅探解析失败，回退为原始 Blob', textParseError)
              }
            }

            if (!result) {
              const modelVersion = response.headers['x-model-version'] || (mode === 'banana' ? '2.5' : '3_pro')
              const format = mimeType.includes('png') ? 'png' : (mimeType.includes('jpeg') || mimeType.includes('jpg') ? 'jpeg' : 'jpeg')
              result = {
                success: true,
                image_blob: response.data,
                image_format: format,
                model_version: modelVersion,
                response: `图片生成成功！(Gemini ${modelVersion === '3_pro' ? '3 Pro' : '2.5 Flash'})`,
                is_blob: true
              }
            }
          } else {
            // 非 Blob：尝试解析对象/字符串，转换为 Blob
            const data = response?.data
            if (typeof data === 'string') {
              const maybeBase64 = data.trim()
              const base64Like = maybeBase64.length > 100 && /^[A-Za-z0-9+/=\n\r]+$/.test(maybeBase64)
              try {
                const jsonData = JSON.parse(data)
                if (jsonData.image_data) {
                  const raw = atob(jsonData.image_data)
                  const view = new Uint8Array(raw.length)
                  for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                  const inferredFormat = jsonData.image_format || 'jpeg'
                  const blob = new Blob([view], { type: `image/${inferredFormat}` })
                  result = {
                    success: true,
                    image_blob: blob,
                    image_format: inferredFormat,
                    model_version: jsonData.model_version || (mode === 'banana' ? '2.5' : '3_pro'),
                    response: jsonData.response || '图片生成成功（本地解码）',
                    is_blob: true
                  }
                } else {
                  result = jsonData
                }
              } catch (parseError) {
                if (base64Like) {
                  const raw = atob(maybeBase64)
                  const view = new Uint8Array(raw.length)
                  for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                  const inferredFormat = 'jpeg'
                  const blob = new Blob([view], { type: `image/${inferredFormat}` })
                  result = {
                    success: true,
                    image_blob: blob,
                    image_format: inferredFormat,
                    model_version: mode === 'banana' ? '2.5' : '3_pro',
                    response: '图片生成成功（本地解码）',
                    is_blob: true
                  }
                }
              }
            } else if (data && typeof data === 'object') {
              if (data.image_data) {
                const raw = atob(data.image_data)
                const view = new Uint8Array(raw.length)
                for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                const inferredFormat = data.image_format || 'jpeg'
                const blob = new Blob([view], { type: `image/${inferredFormat}` })
                result = {
                  success: true,
                  image_blob: blob,
                  image_format: inferredFormat,
                  model_version: data.model_version || (mode === 'banana' ? '2.5' : '3_pro'),
                  response: data.response || '图片生成成功（本地解码）',
                  is_blob: true
                }
              } else {
                result = data
              }
            }
          }

          // Banana 路径无效则回退到 /api/process3
          const needFallback = (
            mode === 'banana' && (
              !result || result.success === false || (!result.image_blob && !result.image_data)
            )
          )

          if (!needFallback) {
            return result
          }

          console.warn('🟡 [fallback] /api/process 返回无效结果，回退到 /api/process3')
          try {
            const fbResponse = await axios.post(`${API_BASE_URL}/api/process3`, formData, {
              headers: { 'Content-Type': 'multipart/form-data', 'Accept': 'image/*,application/json,text/plain' },
              responseType: 'blob',
              timeout: 300000,
            })
            const fbData = fbResponse?.data

            if (fbData && fbData.success !== false && fbData.image_data) {
              // 将 base64 转为 Blob，统一走 Blob 展示通道
              const base64 = fbData.image_data
              const fmt = (fbData.image_format || 'jpeg').toLowerCase()
              const raw = atob(base64)
              const view = new Uint8Array(raw.length)
              for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
              const blob = new Blob([view], { type: `image/${fmt}` })
              return {
                success: true,
                image_blob: blob,
                image_format: fmt,
                model_version: '3_pro',
                response: fbData.response || '图片生成成功（Gemini 3 Pro 回退）',
                is_blob: true
              }
            }

            // 回退也失败，则原样返回以便上层显示错误信息
            console.error('❌ [fallback] /api/process3 仍未返回有效 image_data:', fbData)
            return fbData
          } catch (fbErr) {
            console.error('❌ [fallback] 调用 /api/process3 失败:', fbErr)
            throw fbErr
          }
        } catch (error) {
          console.error('❌ 图生图流程出错:', error)
          throw error
        }
      } else {
        // 文生图：直接调用 process-json 接口
        const apiEndpoint = mode === 'banana_pro' ? '/api/process-json3' : '/api/process-json'
        const modelInfo = mode === 'banana' ? 'Gemini 2.5 Flash' :
                         mode === 'banana_pro' ? 'Gemini 3 Pro' : mode
        console.log(`🎨 文生图模式 (${mode}): ${modelInfo} -> ${apiEndpoint}`)
        
        try {
          const finalPrompt = message
          
          // 生成请求键（基于关键参数，避免重复调用）
          const processRequestKey = JSON.stringify({
            message: finalPrompt.substring(0, 2000),
            mode: mode,
            aspectRatio: aspectRatio || null,
            resolution: resolution || null,
            temperature: temperature || null
          })
          
          // 如果已有相同的请求正在进行，复用 Promise
          if (pendingProcessPromises.has(processRequestKey)) {
            const pendingPromise = pendingProcessPromises.get(processRequestKey)
            console.log(`♻️ 复用已存在的请求`)
            return pendingPromise
          }
          
          const processRequestId = Date.now()
          const payload = {
            message: finalPrompt,
            mode: mode,
            history,
            skip_optimization: true,
          }
          if (aspectRatio) {
            payload.aspect_ratio = aspectRatio
          }
          if (resolution) {
            payload.resolution = resolution
          }
          if (temperature !== null && temperature !== undefined) {
            payload.temperature = temperature
          }
          
          // 创建新请求 Promise
          const processPromise = (async () => {
            try {
              console.log(`🚀 [v1.0.4] 发送请求到 ${apiEndpoint}，payload:`, JSON.stringify(payload).substring(0, 200))
              console.log(`🚀 [v1.0.4] 请求配置: responseType='blob', timeout=300s, maxSize=50MB`)
              
              // ⚠️ 强制配置：确保 responseType 为 'blob'，获取原始二进制流
              const response = await client.post(apiEndpoint, payload, {
                responseType: 'blob',  // 强制 Blob 响应，不自动解析为 JSON
                headers: {
                  Accept: 'image/*,application/json,text/plain'
                },
                timeout: 300000,  // 300 秒超时（5 分钟，给 Gemini 3 Pro 生图留足时间）
                maxContentLength: 50 * 1024 * 1024,  // 最大 50MB（支持 4K 高质量图片）
                maxBodyLength: 50 * 1024 * 1024,
                onDownloadProgress: (progressEvent) => {
                  if (progressEvent.lengthComputable) {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                    console.log(`📥 [v1.0.4] 下载进度: ${percentCompleted}% (${(progressEvent.loaded / 1024).toFixed(2)}KB / ${(progressEvent.total / 1024).toFixed(2)}KB)`)
                  } else {
                    console.log(`📥 [v1.0.4] 已下载: ${(progressEvent.loaded / 1024).toFixed(2)}KB`)
                  }
                }
              })
              
              console.log(`✅ [v1.0.4] 收到响应，状态: ${response.status}, headers:`, response.headers)
              console.log(`✅ [v1.0.4] 响应数据类型: ${response.data?.constructor?.name}, 大小: ${response.data?.size} bytes (${(response.data?.size / 1024 / 1024).toFixed(2)}MB)`)
              
              if (response.data instanceof Blob) {
                console.log(`📦 [v1.0.4] 确认收到 Blob 对象`)
                // 获取 Content-Type 信息
                const contentType = response.headers['content-type'] || ''
                const mimeType = contentType.split(';')[0].trim().toLowerCase()
                const blobSize = response.data.size || 0
                console.log(`📦 [v1.0.1] Blob 详情: contentType='${contentType}', mimeType='${mimeType}', size=${blobSize} bytes (${(blobSize/1024).toFixed(2)}KB)`)

                // 嗅探前缀，防止“伪装成 image 的文本/base64/JSON”
                const headText = await response.data.slice(0, 120).text().catch(() => '')
                const trimmedHead = headText.trim()
                const looksLikeJson = trimmedHead.startsWith('{') || trimmedHead.startsWith('[')
                const looksLikeDataUrl = trimmedHead.startsWith('data:image')
                const looksLikeBase64 = trimmedHead.length > 30 && /^[A-Za-z0-9+/=\s]+$/.test(trimmedHead)
                const isJsonByHeader = mimeType === 'application/json' || mimeType.includes('json')
                const shouldTreatAsText = isJsonByHeader || trimmedHead.length > 0 && (looksLikeJson || looksLikeDataUrl || looksLikeBase64)

                if (shouldTreatAsText) {
                  try {
                    const text = await response.data.text()
                    // JSON 情况
                    if (looksLikeJson || isJsonByHeader) {
                      const jsonData = JSON.parse(text)
                      if (jsonData && jsonData.image_data) {
                        const raw = atob(jsonData.image_data)
                        const view = new Uint8Array(raw.length)
                        for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                        const inferredFormat = jsonData.image_format || 'jpeg'
                        const blob = new Blob([view], { type: `image/${inferredFormat}` })
                        console.warn(`⚠️ ${apiEndpoint} 返回 JSON，已本地转换为 Blob (${inferredFormat})`)
                        return {
                          success: true,
                          image_blob: blob,
                          image_format: inferredFormat,
                          model_version: jsonData.model_version || (mode === 'banana' ? '2.5' : '3_pro'),
                          response: jsonData.response || '图片生成成功（本地解码）',
                          is_blob: true
                        }
                      }
                      console.error(`❌ ${apiEndpoint} 返回错误:`, jsonData)
                      return jsonData
                    }
                    // data:image/...;base64,... 直转 Blob
                    if (looksLikeDataUrl) {
                      const [headerPart, dataPart] = text.split(',')
                      const mimeMatch = headerPart.match(/data:([^;]+)/)
                      const inferredFormat = (mimeMatch?.[1] || 'image/jpeg').replace('image/', '')
                      const raw = atob(dataPart)
                      const view = new Uint8Array(raw.length)
                      for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                      const blob = new Blob([view], { type: `image/${inferredFormat}` })
                      console.warn(`⚠️ ${apiEndpoint} 返回 dataURL 文本，已本地转换为 Blob (${inferredFormat})`)
                      return {
                        success: true,
                        image_blob: blob,
                        image_format: inferredFormat,
                        model_version: mode === 'banana' ? '2.5' : '3_pro',
                        response: '图片生成成功（本地解码）',
                        is_blob: true
                      }
                    }
                    // 裸 base64 文本
                    if (looksLikeBase64) {
                      const raw = atob(text.replace(/\s+/g, ''))
                      const view = new Uint8Array(raw.length)
                      for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                      const inferredFormat = mimeType.includes('png') ? 'png' : 'jpeg'
                      const blob = new Blob([view], { type: `image/${inferredFormat}` })
                      console.warn(`⚠️ ${apiEndpoint} 返回裸 base64 文本，已本地转换为 Blob (${inferredFormat})`)
                      return {
                        success: true,
                        image_blob: blob,
                        image_format: inferredFormat,
                        model_version: mode === 'banana' ? '2.5' : '3_pro',
                        response: '图片生成成功（本地解码）',
                        is_blob: true
                      }
                    }
                  } catch (textParseError) {
                    console.error('❌ 文本嗅探解析失败，回退为原始 Blob', textParseError)
                  }
                }
                
                // 成功响应：返回二进制图片流
                const modelVersion = response.headers['x-model-version'] || (mode === 'banana' ? '2.5' : '3_pro')
                const format = mimeType.includes('jpeg') || mimeType.includes('jpg') ? 'jpeg' : 
                              mimeType.includes('png') ? 'png' : 'jpeg'
                const modelName = modelVersion === '2.5' ? 'Gemini 2.5 Flash' : 
                                 modelVersion === '3_pro' ? 'Gemini 3 Pro' : 
                                 `Gemini ${modelVersion}`
                
                console.log(`✅ [v1.0.1] ${apiEndpoint} 收到图片 (${format}, ${(blobSize / 1024).toFixed(2)}KB, ${modelName})`)
                console.log(`📦 [v1.0.1] 返回原始 Blob 对象，类型: ${response.data.constructor.name}, 大小: ${response.data.size} bytes`)
                console.log(`📦 [v1.0.1] Blob 验证: isBlob=${response.data instanceof Blob}, hasSize=${!!response.data.size}, hasType=${!!response.data.type}`)
                
                // ⚠️ 严格要求：直接返回原始 Blob 对象
                // 禁止读取 response.data.image_data，因为响应就是二进制文件本身，直接使用 response.data
                const result = {
                  success: true,
                  image_blob: response.data,  // 原始二进制 Blob 对象（不是 JSON）
                  image_format: format,
                  model_version: modelVersion,
                  response: `图片生成成功！(${modelName})`,
                  is_blob: true
                }
                console.log(`✅ [v1.0.1] 准备返回结果，is_blob=true, image_blob 大小: ${result.image_blob.size} bytes`)
                return result
              } else {
                // 非 Blob 响应，尝试解析为 JSON；如有 base64 也尝试转换
                if (typeof response.data === 'string') {
                  const maybeBase64 = response.data.trim()
                  const base64Like = maybeBase64.length > 100 && /^[A-Za-z0-9+/=\n\r]+$/.test(maybeBase64)
                  try {
                    const jsonData = JSON.parse(response.data)
                    if (jsonData.image_data) {
                      const raw = atob(jsonData.image_data)
                      const view = new Uint8Array(raw.length)
                      for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                      const inferredFormat = jsonData.image_format || 'jpeg'
                      const blob = new Blob([view], { type: `image/${inferredFormat}` })
                      console.warn(`⚠️ ${apiEndpoint} 字符串响应包含 base64，已本地转换为 Blob (${inferredFormat})`)
                      return {
                        success: true,
                        image_blob: blob,
                        image_format: inferredFormat,
                        model_version: jsonData.model_version || (mode === 'banana' ? '2.5' : '3_pro'),
                        response: jsonData.response || '图片生成成功（本地解码）',
                        is_blob: true
                      }
                    }
                    if (jsonData.success === false) {
                      logger.error(`${apiEndpoint} 返回错误:`, jsonData)
                      return jsonData
                    }
                  } catch (parseError) {
                    // 不是 JSON，则检测是否为裸 base64 字符串
                    if (base64Like) {
                      const raw = atob(maybeBase64)
                      const view = new Uint8Array(raw.length)
                      for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                      const inferredFormat = 'jpeg'
                      const blob = new Blob([view], { type: `image/${inferredFormat}` })
                      console.warn(`⚠️ ${apiEndpoint} 返回裸 base64 字符串，已本地转换为 Blob (${inferredFormat})`)
                      return {
                        success: true,
                        image_blob: blob,
                        image_format: inferredFormat,
                        model_version: mode === 'banana' ? '2.5' : '3_pro',
                        response: '图片生成成功（本地解码）',
                        is_blob: true
                      }
                    }
                  }
                }
                
                if (response.data && typeof response.data === 'object') {
                  if (response.data.image_data) {
                    const raw = atob(response.data.image_data)
                    const view = new Uint8Array(raw.length)
                    for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                    const inferredFormat = response.data.image_format || 'jpeg'
                    const blob = new Blob([view], { type: `image/${inferredFormat}` })
                    console.warn(`⚠️ ${apiEndpoint} 对象响应包含 base64，已本地转换为 Blob (${inferredFormat})`)
                    return {
                      success: true,
                      image_blob: blob,
                      image_format: inferredFormat,
                      model_version: response.data.model_version || (mode === 'banana' ? '2.5' : '3_pro'),
                      response: response.data.response || '图片生成成功（本地解码）',
                      is_blob: true
                    }
                  }
                  if (response.data.success === false) {
                    logger.error(`${apiEndpoint} 返回错误:`, response.data)
                    return response.data
                  }
                }
                
                throw new Error(`响应类型错误：期望 Blob，但收到 ${typeof response.data}`)
              }
            } catch (error) {
              console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
              console.error(`❌ [v1.0.1] ${apiEndpoint} 请求失败`)
              console.error(`❌ [v1.0.1] 错误类型: ${error.name}`)
              console.error(`❌ [v1.0.1] 错误信息: ${error.message}`)
              console.error(`❌ [v1.0.1] 错误代码: ${error.code}`)
              if (error.response) {
                console.error(`❌ [v1.0.1] 响应状态: ${error.response.status}`)
                console.error(`❌ [v1.0.1] 响应头:`, error.response.headers)
                console.error(`❌ [v1.0.1] 响应数据类型:`, error.response.data?.constructor?.name)
              } else if (error.request) {
                console.error(`❌ [v1.0.1] 请求已发送但无响应`)
                console.error(`❌ [v1.0.1] 请求详情:`, {
                  readyState: error.request.readyState,
                  status: error.request.status,
                  statusText: error.request.statusText
                })
              }
              console.error(`❌ [v1.0.1] 完整错误堆栈:`, error.stack)
              console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
              
              // 特殊处理：网络连接错误
              if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error') || error.message.includes('CONNECTION_CLOSED')) {
                console.error(`🔴 [v1.0.4] 诊断: 网络连接关闭，可能原因:`)
                console.error(`   1. 后端返回的图片过大，超过前端 50MB 限制`)
                console.error(`   2. Cloud Run 或中间代理强制断开连接（32MB 响应限制）`)
                console.error(`   3. 网络不稳定，长连接被中断`)
                console.error(`   4. 后端处理异常，在发送完整响应前崩溃`)
                console.error(`   建议: 尝试使用较低的分辨率（1K 或 2K），避免 4K 高清图片`)
                throw new Error(`网络连接关闭。可能是生成的图片过大，请尝试使用 1K 或 2K 分辨率。`)
              }
              
              // 特殊处理：超时错误
              if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
                console.error(`⏰ [v1.0.3] 诊断: 请求超时（当前限制: 300秒/5分钟）`)
                console.error(`   可能原因:`)  
                console.error(`   1. Gemini 3 Pro 生图耗时过长（高质量图片需要更多时间）`)
                console.error(`   2. 网络连接不稳定，导致传输缓慢`)
                console.error(`   3. 后端 Cloud Run 实例冷启动（首次请求可能需要 30-60秒）`)
                console.error(`   建议: 稍后重试，或尝试降低图片质量设置`)
                throw new Error(`请求超时（${error.message}）。Gemini 3 Pro 生图需要较长时间，请稍后重试或降低质量设置。`)
              }
              
              // Banana 文生图失败时，自动回退到 Gemini 3 Pro 接口重试一次
              if (mode === 'banana') {
                console.warn(`🟡 [fallback] Banana 文生图失败，自动回退到 /api/process-json3 (Gemini 3 Pro)`)
                try {
                  const fallbackResponse = await client.post('/api/process-json3', payload, {
                    responseType: 'blob',
                    headers: { Accept: 'image/*,application/json,text/plain' },
                    timeout: 300000,
                    maxContentLength: 50 * 1024 * 1024,
                    maxBodyLength: 50 * 1024 * 1024,
                  })

                  console.log(`✅ [fallback] 收到响应，状态: ${fallbackResponse.status}, headers:`, fallbackResponse.headers)
                  if (fallbackResponse.data instanceof Blob) {
                    const contentType = fallbackResponse.headers['content-type'] || ''
                    const mimeType = contentType.split(';')[0].trim().toLowerCase()
                    const blobSize = fallbackResponse.data.size || 0
                    console.log(`📦 [fallback] Blob 详情: contentType='${contentType}', size=${blobSize} bytes`)

                    // 与主路径一致的嗅探与转换
                    const headText = await fallbackResponse.data.slice(0, 120).text().catch(() => '')
                    const trimmedHead = headText.trim()
                    const looksLikeJson = trimmedHead.startsWith('{') || trimmedHead.startsWith('[')
                    const looksLikeDataUrl = trimmedHead.startsWith('data:image')
                    const looksLikeBase64 = trimmedHead.length > 30 && /^[A-Za-z0-9+/=\s]+$/.test(trimmedHead)
                    const isJsonByHeader = mimeType === 'application/json' || mimeType.includes('json')
                    const shouldTreatAsText = isJsonByHeader || trimmedHead.length > 0 && (looksLikeJson || looksLikeDataUrl || looksLikeBase64)

                    if (shouldTreatAsText) {
                      const text = await fallbackResponse.data.text()
                      if (looksLikeJson || isJsonByHeader) {
                        const jsonData = JSON.parse(text)
                        if (jsonData && jsonData.image_data) {
                          const raw = atob(jsonData.image_data)
                          const view = new Uint8Array(raw.length)
                          for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                          const inferredFormat = jsonData.image_format || 'jpeg'
                          const blob = new Blob([view], { type: `image/${inferredFormat}` })
                          return {
                            success: true,
                            image_blob: blob,
                            image_format: inferredFormat,
                            model_version: '3_pro',
                            response: jsonData.response || '图片生成成功（本地解码）',
                            is_blob: true
                          }
                        }
                        return jsonData
                      }
                      if (looksLikeDataUrl) {
                        const [headerPart, dataPart] = text.split(',')
                        const mimeMatch = headerPart.match(/data:([^;]+)/)
                        const inferredFormat = (mimeMatch?.[1] || 'image/jpeg').replace('image/', '')
                        const raw = atob(dataPart)
                        const view = new Uint8Array(raw.length)
                        for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                        const blob = new Blob([view], { type: `image/${inferredFormat}` })
                        return {
                          success: true,
                          image_blob: blob,
                          image_format: inferredFormat,
                          model_version: '3_pro',
                          response: '图片生成成功（本地解码）',
                          is_blob: true
                        }
                      }
                      if (looksLikeBase64) {
                        const raw = atob(text.replace(/\s+/g, ''))
                        const view = new Uint8Array(raw.length)
                        for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i)
                        const inferredFormat = mimeType.includes('png') ? 'png' : 'jpeg'
                        const blob = new Blob([view], { type: `image/${inferredFormat}` })
                        return {
                          success: true,
                          image_blob: blob,
                          image_format: inferredFormat,
                          model_version: '3_pro',
                          response: '图片生成成功（本地解码）',
                          is_blob: true
                        }
                      }
                    }

                    const modelVersion = '3_pro'
                    const format = mimeType.includes('png') ? 'png' : 'jpeg'
                    return {
                      success: true,
                      image_blob: fallbackResponse.data,
                      image_format: format,
                      model_version: modelVersion,
                      response: '图片生成成功！(Gemini 3 Pro 回退)',
                      is_blob: true
                    }
                  }
                } catch (fallbackError) {
                  console.error('❌ [fallback] 回退到 /api/process-json3 仍失败:', fallbackError)
                }
              }

              throw error
            } finally {
              pendingProcessPromises.delete(processRequestKey)
            }
          })()
          
          pendingProcessPromises.set(processRequestKey, processPromise)
          return processPromise
        } catch (error) {
          console.error('❌ 文生图流程出错:', error)
          throw error
        }
      }
    }
    
    // 聊天模式：直接调用 process-json
    const chatRequestKey = JSON.stringify({
      message: message.substring(0, 2000),
      mode: mode || 'chat',
      aspectRatio: aspectRatio || null,
      resolution: resolution || null,
      temperature: temperature || null
    })
    
    // 如果已有相同的请求正在进行，复用 Promise
    if (pendingProcessPromises.has(chatRequestKey)) {
      const pendingPromise = pendingProcessPromises.get(chatRequestKey)
      console.log(`♻️ 复用已存在的聊天请求`)
      return pendingPromise
    }
    
    const payload = {
      message,
      mode,
      history,
    }
    if (aspectRatio) {
      payload.aspect_ratio = aspectRatio
    }
    if (resolution) {
      payload.resolution = resolution
    }
    if (temperature !== null && temperature !== undefined) {
      payload.temperature = temperature
    }
    
    // 创建新请求 Promise
    const chatPromise = (async () => {
      try {
        console.log(`💬 聊天模式 -> /api/process-json`)
        const response = await client.post('/api/process-json', payload)
        console.log(`✅ 聊天请求成功`)
        return response.data
      } catch (error) {
        console.error(`❌ 聊天请求失败:`, error)
        throw error
      } finally {
        pendingProcessPromises.delete(chatRequestKey)
      }
    })()
    
    pendingProcessPromises.set(chatRequestKey, chatPromise)
    return chatPromise
  },
}

export default chatAPI
