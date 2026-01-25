/**
 * API 配置文件
 * 从环境变量读取后端 API 地址
 */

// 从环境变量获取 API 地址
const getApiBaseUrl = () => {
  // Vite 使用 import.meta.env 访问环境变量
  const apiUrl = import.meta.env.VITE_API_BASE_URL;
  
  if (!apiUrl) {
    throw new Error('VITE_API_BASE_URL 环境变量未配置，请检查 .env 文件');
  }
  
  return apiUrl;
};

export const API_BASE_URL = getApiBaseUrl();

// 导出配置对象
export const apiConfig = {
  baseURL: API_BASE_URL,
  timeout: 600000, // 10分钟超时（600秒，统一所有请求超时时间，支持复杂图片生成场景）
};

// 打印配置信息（开发和生产环境都打印，便于调试）
console.log('🔧 API 配置:', {
  baseURL: API_BASE_URL,
  env: import.meta.env.MODE,
  isProd: import.meta.env.PROD,
  viteApiBaseUrl: import.meta.env.VITE_API_BASE_URL || '未设置',
});

