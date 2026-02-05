/**
 * 认证相关 API
 */

import client, { getSessionToken } from './client'

const authAPI = {
  /**
   * 用户登录
   * @param {string} account - 账号
   * @param {string} password - 密码
   * @returns {Promise<Object>} 登录结果，包含 user 和 session_token
   */
  login: async (account, password) => {
    const loginUrl = '/api/auth/login';
    const requestData = { account, password };
    
    // 详细的请求日志
    console.group('📤 [登录] 发送登录请求');
    console.log('📍 请求 URL:', loginUrl);
    console.log('🔧 请求方法: POST');
    console.log('📝 账号:', account);
    console.log('🔒 密码:', '*'.repeat(password.length));
    console.log('🌐 API 基础地址:', client.defaults.baseURL);
    console.log('⏰ 请求时间:', new Date().toISOString());
    console.groupEnd();
    
    try {
      const response = await client.post(loginUrl, requestData);
      
      // 详细的响应日志
      console.group('📥 [登录] 登录响应成功');
      console.log('📍 响应 URL:', response.config.url);
      console.log('📊 状态码:', response.status);
      console.log('📦 响应数据:', {
        success: response.data?.success,
        hasUser: !!response.data?.user,
        hasToken: !!response.data?.session_token,
        userId: response.data?.user?.id,
        account: response.data?.user?.account
      });
      console.groupEnd();
      
      return response.data;
    } catch (error) {
      // 详细的错误日志
      console.group('❌ [登录] 登录失败');
      console.error('🔴 错误类型:', error?.response ? '服务器错误' : error?.request ? '网络错误' : '其他错误');
      console.error('📍 请求 URL:', loginUrl);
      console.error('📝 账号:', account);
      
      if (error?.response) {
        // 服务器返回了响应
        console.error('📊 HTTP 状态码:', error.response.status);
        console.error('📝 HTTP 状态文本:', error.response.statusText);
        console.error('📋 响应头:', error.response.headers);
        console.error('📄 错误响应体:', error.response.data);
        console.error('💡 可能原因:');
        if (error.response.status === 401) {
          console.error('   - 账号或密码错误');
        } else if (error.response.status === 400) {
          console.error('   - 请求参数错误');
          console.error('   - 账号或密码为空');
        } else if (error.response.status === 500) {
          console.error('   - 服务器内部错误');
          console.error('   - 检查后端日志');
        }
      } else if (error?.request) {
        // 请求已发送但没有收到响应
        console.error('📡 网络错误: 请求已发送但未收到响应');
        console.error('💡 可能原因:');
        console.error('   - 后端服务未运行');
        console.error('   - 网络连接问题');
        console.error('   - CORS 配置问题');
        console.error('   - 后端地址错误:', client.defaults.baseURL);
      } else {
        // 请求配置错误或其他错误
        console.error('⚙️ 请求配置错误:', error?.message || error);
      }
      console.error('📚 完整错误信息:', error);
      console.error('📚 错误堆栈:', error?.stack);
      console.groupEnd();
      
      // 确保错误对象有 message 属性
      if (!error.message && error?.response?.data?.detail) {
        error.message = error.response.data.detail
      } else if (!error.message) {
        error.message = '登录失败，请稍后重试'
      }
      
      throw error;
    }
  },

  /**
   * 用户注册
   * @param {string} account - 账号
   * @param {string} password - 密码
   * @param {string} nickname - 昵称
   * @returns {Promise<Object>} 注册结果，包含 user 和 session_token
   */
  register: async (account, password, nickname) => {
    const response = await client.post('/api/auth/register', {
      account,
      password,
      nickname
    })
    return response.data
  },
}

export default authAPI
