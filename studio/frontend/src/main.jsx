// BUILD: 2025-12-17-11-31-12
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import './i18n/config'
import { AuthProvider } from './contexts/AuthContext'
// 导入构建信息，确保 BUILD_ID 被包含在代码中
import { BUILD_ID, BUILD_TIME } from './build-info.js'

// 将构建信息赋值给 window 对象，确保代码必须存在
if (typeof window !== 'undefined') {
  window.__BUILD_ID__ = BUILD_ID
  window.__BUILD_TIME__ = BUILD_TIME
}

// 确保 BUILD_ID 和 BUILD_TIME 被使用，避免被 tree-shaking 优化掉
// 使用字符串拼接，确保即使被 minify，内容也会不同
const buildInfo = `build:${BUILD_ID}:${BUILD_TIME}`
void (buildInfo)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
)

