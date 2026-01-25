import { createContext, useContext, useState, useEffect } from 'react'
import { getUser, saveUser, loginUser, registerUser, updateUser } from '../utils/userStorage'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // 初始化时从存储中加载用户信息
  useEffect(() => {
    const loadUser = async () => {
      try {
        // 检查是否有 session_token
        const sessionToken = localStorage.getItem('session_token')
        const savedUser = await getUser()
        
        // 如果有 session_token 但没有用户信息，可能是 token 有效但用户信息丢失
        if (sessionToken && !savedUser) {
          console.warn('⚠️ 检测到 session_token 但缺少用户信息，尝试从后端验证')
          try {
            // 尝试从后端获取用户信息
            const { default: authAPI } = await import('../api/auth')
            // 注意：这里需要后端提供 /api/auth/me 接口来验证 token
            // 暂时只记录警告，不阻止用户继续使用
            console.warn('💡 建议：请重新登录以确保 session_token 有效')
          } catch (err) {
            console.warn('验证 session_token 失败:', err)
          }
        }
        
        // 如果有 session_token 但没有用户信息，清除无效的 token
        if (sessionToken && !savedUser) {
          console.warn('🧹 清除无效的 session_token')
          localStorage.removeItem('session_token')
        }
        
        if (savedUser) {
          setUser(savedUser)
        } else if (sessionToken) {
          // 有 token 但没有用户信息，可能是后端重启导致 session 丢失
          console.warn('⚠️ 检测到 session_token 但用户信息不存在，可能是后端重启导致 session 丢失')
          console.warn('💡 建议：请重新登录')
        }
      } catch (error) {
        console.error('加载用户信息失败:', error)
      } finally {
        setLoading(false)
      }
    }
    loadUser()
  }, [])

  // 登录
  const login = async (account, password) => {
    try {
      const userData = await loginUser(account, password)
      setUser(userData)
      return { success: true, user: userData }
    } catch (error) {
      // 确保错误消息总是存在
      const errorMessage = error?.message || error?.toString() || '登录失败，请稍后重试'
      console.error('❌ [AuthContext] 登录失败:', error)
      return { success: false, error: errorMessage }
    }
  }

  // 注册
  const register = async (account, password, nickname) => {
    try {
      const userData = await registerUser(account, password, nickname)
      setUser(userData)
      return { success: true, user: userData }
    } catch (error) {
      // 确保错误消息总是存在
      const errorMessage = error?.message || error?.toString() || '注册失败，请稍后重试'
      console.error('❌ [AuthContext] 注册失败:', error)
      return { success: false, error: errorMessage }
    }
  }

  // 登出
  const logout = async () => {
    try {
      setUser(null)
      // 清除 session_token
      localStorage.removeItem('session_token')
      // 清除本地存储
      const { clearUser } = await import('../utils/userStorage')
      await clearUser()
    } catch (error) {
      console.error('登出失败:', error)
    }
  }

  // 更新用户信息
  const updateUserInfo = async (updates) => {
    try {
      if (!user) throw new Error('用户未登录')
      const updatedUser = await updateUser(user.id, updates)
      setUser(updatedUser)
      return { success: true, user: updatedUser }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    updateUserInfo,
    isAuthenticated: !!user
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

