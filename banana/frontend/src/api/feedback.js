/**
 * 反馈相关 API（用户端）
 */

import client, { checkAuth, getAuthHeaders } from './client'

const feedbackAPI = {
  /**
   * 提交反馈意见
   * @param {string} feedback - 反馈内容
   * @param {string} contact - 联系方式
   * @returns {Promise<Object>} 提交结果
   */
  submitFeedback: async (feedback, contact) => {
    checkAuth() // 检查是否已登录
    try {
      const response = await client.post('/api/feedback/submit', {
        feedback,
        contact
      }, {
        headers: getAuthHeaders()
      })
      return response.data
    } catch (error) {
      console.error('提交反馈API错误:', error.response?.data || error.message)
      throw error
    }
  },

  /**
   * 获取当前用户的反馈列表
   * @returns {Promise<Object>} 反馈列表
   */
  getMyFeedbacks: async () => {
    checkAuth() // 检查是否已登录
    const response = await client.get('/api/feedback/my', {
      headers: getAuthHeaders()
    })
    return response.data
  },
}

export default feedbackAPI
