/**
 * API 模块统一导出入口
 * 
 * 使用方式：
 * import { authAPI, chatAPI, paymentAPI, feedbackAPI, adminAPI } from '../api'
 * 或
 * import authAPI from '../api/auth'
 */

// 导出各个 API 模块
export { default as authAPI } from './auth'
export { default as chatAPI } from './chat'
export { default as paymentAPI } from './payment'
export { default as feedbackAPI } from './feedback'
export { default as adminAPI } from './admin'
export { default as sdAPI } from './sd'

// 导出基础客户端（如果需要直接使用 axios 实例）
export { default as apiClient } from './client'

// 导出工具函数
export { getSessionToken, getAuthHeaders, checkAuth } from './client'
