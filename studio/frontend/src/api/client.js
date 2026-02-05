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
