/**
 * 存储工具 - 使用 IndexedDB 存储方案
 * 
 * 使用 IndexedDB 存储会话历史数据，避免 localStorage 的 5MB 限制
 * IndexedDB 可以存储大量数据（通常几GB），更适合存储聊天历史和图片
 */

// 导入并重新导出 IndexedDB 存储
export * from './indexedDBStorage.js'
