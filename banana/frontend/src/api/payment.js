/**
 * 支付相关 API
 */

import client from './client'
import { API_BASE_URL } from '../config/api'

const paymentAPI = {
  /**
   * 创建支付订单
   * @param {string} plan - 套餐名称
   * @param {string|number} price - 价格
   * @returns {Promise<Object>} 订单信息
   */
  createPayment: async (plan, price) => {
    const response = await client.post('/api/payment/create', {
      plan,
      price: parseFloat(price),
    })
    return response.data
  },

  /**
   * 查询支付订单
   * @param {string} orderId - 订单ID
   * @returns {Promise<Object>} 订单信息
   */
  queryPayment: async (orderId) => {
    const response = await client.get(`/api/payment/query/${orderId}`)
    return response.data
  },

  /**
   * 提交支付订单号
   * @param {string} plan - 套餐名称
   * @param {string|number} price - 价格
   * @param {string} account - 用户账号
   * @param {string} orderNumber - 订单号
   * @returns {Promise<Object>} 提交结果
   */
  submitOrder: async (plan, price, account, orderNumber) => {
    const response = await fetch(`${API_BASE_URL}/api/payment/submit-order`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        plan,
        price: parseFloat(price),
        account,
        orderNumber: orderNumber.trim(),
      }),
    })
    const result = await response.json()
    return result
  },
}

export default paymentAPI
