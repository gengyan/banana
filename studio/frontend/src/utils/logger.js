/**
 * 前端日志工具
 * 统一添加 [前端] 前缀，便于区分前后端日志
 */

// 日志级别
const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
}

// 当前日志级别（生产环境只显示 WARN 和 ERROR，开发环境显示所有）
const currentLogLevel = import.meta.env.PROD ? LOG_LEVELS.WARN : LOG_LEVELS.DEBUG

// 日志前缀
const PREFIX = '[前端]'

/**
 * 格式化日志消息
 */
const formatMessage = (level, ...args) => {
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
  return [`${PREFIX} ${timestamp} [${level}]`, ...args]
}

/**
 * 日志工具对象
 */
export const logger = {
  /**
   * 调试日志（仅在开发环境显示）
   */
  debug: (...args) => {
    if (currentLogLevel <= LOG_LEVELS.DEBUG) {
      console.log(...formatMessage('DEBUG', ...args))
    }
  },

  /**
   * 信息日志
   */
  info: (...args) => {
    if (currentLogLevel <= LOG_LEVELS.INFO) {
      console.log(...formatMessage('INFO', ...args))
    }
  },

  /**
   * 警告日志
   */
  warn: (...args) => {
    if (currentLogLevel <= LOG_LEVELS.WARN) {
      console.warn(...formatMessage('WARN', ...args))
    }
  },

  /**
   * 错误日志
   */
  error: (...args) => {
    if (currentLogLevel <= LOG_LEVELS.ERROR) {
      console.error(...formatMessage('ERROR', ...args))
    }
  },

  /**
   * 分组日志（开发环境）
   */
  group: (label) => {
    if (currentLogLevel <= LOG_LEVELS.DEBUG) {
      console.group(`${PREFIX} ${label}`)
    }
  },

  /**
   * 结束分组
   */
  groupEnd: () => {
    if (currentLogLevel <= LOG_LEVELS.DEBUG) {
      console.groupEnd()
    }
  }
}

export default logger
