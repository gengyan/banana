// 构建ID：每次构建时这个文件都会被重新生成，确保文件内容变化
// 使用时间戳确保每次构建都不同（这个文件会在构建时被 vite.config.js 替换）
export const BUILD_ID = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
export const BUILD_TIME = new Date().toISOString()

