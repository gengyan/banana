/**
 * API 客户端基础配置
 * 提供 axios 实例和通用工具函数
 */

import axios from 'axios'
import { API_BASE_URL } from '../config/api'
import logger from '../utils/logger'

// 创建 axios 实例（不全局强制 Content-Type，避免 Blob 请求被错误认定为 JSON）
const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10分钟超时（600秒，图片生成可能需要较长时间，特别是复杂场景和多参考图）
  withCredentials: true, // 启用跨域凭证（Cookie、HTTP 认证等），必须与后端 CORS allow_credentials=true 配合
})

// 添加请求拦截器
client.interceptors.request.use(
  (config) => {
    logger.debug('API 请求:', { method: config.method?.toUpperCase(), url: config.url })
    return config
  },
  (error) => {
    logger.error('请求拦截器错误:', error)
    return Promise.reject(error)
  }
)

// 添加响应拦截器（用于错误处理）
client.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 网络错误处理
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      logger.error('网络错误:', error.message, error.config?.url)
      error.networkError = true
      error.friendlyMessage = '无法连接到后端服务，请检查后端服务是否已启动'
    }
    
    // ⚠️ 关键修复：捕获错误的 response headers 并保存到 error 对象中
    // 这样即使在后续处理中丢失了 response 对象，我们仍然能访问到 headers
    if (error.response?.headers) {
      const headers = error.response.headers
      
      // 尝试所有可能的键名格式
      const errorMessage = 
        headers['x-error-message'] || 
        headers['X-Error-Message'] ||
        headers['X-ERROR-MESSAGE'] ||
        headers['x-error-message'.toLowerCase()] ||
        null
      
      const errorCode = 
        headers['x-error-code'] || 
        headers['X-Error-Code'] ||
        headers['X-ERROR-CODE'] ||
        null
      
      const requestId = 
        headers['x-request-id'] || 
        headers['X-Request-ID'] ||
        null
      
      // 保存到 error 对象以便后续访问
      error.errorHeaders = {
        code: errorCode,
        message: errorMessage,
        requestId: requestId
      }
      
      // 调试日志：显示原始headers对象和提取的值
      console.log('[axios响应拦截器] 捕获到HTTP错误', {
        'status': error.response.status,
        'statusText': error.response.statusText,
        'allHeaderKeys': Object.keys(headers),
        'errorHeaders': error.errorHeaders,
        'rawHeaders': JSON.stringify(headers)
      })
    } else {
      console.log('[axios响应拦截器] 错误中没有response.headers')
    }
    
    return Promise.reject(error)
  }
)

/**
 * 获取当前会话令牌
 */
export function getSessionToken() {
  return localStorage.getItem('session_token')
}

/**
 * 创建带认证头的请求配置
 */
export function getAuthHeaders(additionalHeaders = {}) {
  const sessionToken = getSessionToken()
  return {
    ...additionalHeaders,
    ...(sessionToken && { 'Authorization': `Bearer ${sessionToken}` })
  }
}

/**
 * 检查是否已登录
 * 如果未登录，会抛出错误并提供调试信息
 */
export function checkAuth() {
  const token = getSessionToken()
  if (!token) {
    logger.error('登录检查失败 - session_token 不存在')
    
    // 检查是否有用户信息但缺少 session_token（可能是 token 丢失）
    if (localStorage.getItem('currentUserId')) {
      logger.warn('检测到用户ID但缺少 session_token，可能是 token 过期或被清除')
    }
    
    throw new Error('未登录，请先登录')
  }
  return token
}

export default client
