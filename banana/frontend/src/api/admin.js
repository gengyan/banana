/**
 * 管理员相关 API
 */

import client, { checkAuth, getAuthHeaders } from './client'

const adminAPI = {
  /**
   * 获取所有用户列表（管理员功能）
   * @returns {Promise<Object>} 用户列表
   */
  getAllUsers: async () => {
    checkAuth() // 检查是否已登录
    const response = await client.get('/api/admin/users', {
      headers: getAuthHeaders()
    })
    return response.data
  },

  /**
   * 更新用户信息（管理员功能）
   * @param {string} userId - 用户ID
   * @param {Object} updates - 要更新的字段
   * @returns {Promise<Object>} 更新后的用户信息
   */
  updateUser: async (userId, updates) => {
    checkAuth() // 检查是否已登录
    const sessionToken = localStorage.getItem('session_token')
    const response = await client.put(`/api/admin/users/${userId}`, {
      ...updates,
      session_token: sessionToken
    }, {
      headers: getAuthHeaders()
    })
    return response.data
  },

  /**
   * 获取所有反馈列表（管理员功能）
   * @returns {Promise<Object>} 反馈列表
   */
  getAllFeedbacks: async () => {
    checkAuth() // 检查是否已登录
    const response = await client.get('/api/feedback/admin/all', {
      headers: getAuthHeaders()
    })
    return response.data
  },

  /**
   * 管理员回复反馈
   * @param {string} feedbackId - 反馈ID
   * @param {string} reply - 回复内容
   * @returns {Promise<Object>} 回复结果
   */
  replyFeedback: async (feedbackId, reply) => {
    checkAuth() // 检查是否已登录
    const response = await client.post(`/api/feedback/admin/${feedbackId}/reply`, {
      reply
    }, {
      headers: getAuthHeaders()
    })
    return response.data
  },

  /**
   * 重置用户密码为 123456（管理员功能）
   * @param {string} userId - 用户ID
   * @returns {Promise<Object>} 重置结果
   */
  resetUserPassword: async (userId) => {
    checkAuth() // 检查是否已登录
    const response = await client.post(`/api/admin/users/${userId}/reset-password`, {}, {
      headers: getAuthHeaders()
    })
    return response.data
  },
}

export default adminAPI
