/**
 * 用户存储工具
 * 使用IndexedDB存储用户信息
 */

const DB_NAME = 'GuojieUserData'
const DB_VERSION = 2
const STORE_USERS = 'users'

let db = null

/**
 * 初始化数据库
 */
function initDB() {
  return new Promise((resolve, reject) => {
    if (db) {
      resolve(db)
      return
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => {
      reject(new Error('数据库打开失败'))
    }

    request.onsuccess = () => {
      db = request.result
      resolve(db)
    }

    request.onupgradeneeded = (event) => {
      const database = event.target.result

      // 创建用户存储
      if (!database.objectStoreNames.contains(STORE_USERS)) {
        const userStore = database.createObjectStore(STORE_USERS, {
          keyPath: 'id',
          autoIncrement: false
        })
        userStore.createIndex('account', 'account', { unique: true })
        userStore.createIndex('createdAt', 'createdAt', { unique: false })
      }
    }
  })
}

/**
 * 生成用户ID
 */
function generateUserId() {
  return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * 简单密码哈希（实际应用中应使用更安全的方法）
 */
function hashPassword(password) {
  // 这是一个简单的哈希，实际应用中应该使用bcrypt等
  let hash = 0
  for (let i = 0; i < password.length; i++) {
    const char = password.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32bit integer
  }
  return hash.toString()
}

/**
 * 验证账号格式（邮箱或手机号）
 */
function validateAccount(account) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const phoneRegex = /^1[3-9]\d{8,9}$/ // 允许10-11位手机号：1 + [3-9] + 8-9位数字
  return emailRegex.test(account) || phoneRegex.test(account)
}

/**
 * 获取当前用户
 */
export async function getUser() {
  try {
    const userId = localStorage.getItem('currentUserId')
    if (!userId) return null

    // manager 账号特殊处理（不在数据库中存储）
    if (userId === 'manager_user') {
      return {
        id: 'manager_user',
        account: 'manager',
        nickname: '管理员',
        avatar: null,
        level: 'enterprise',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    }

    const database = await initDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_USERS], 'readonly')
      const store = transaction.objectStore(STORE_USERS)
      const request = store.get(userId)

      request.onsuccess = () => {
        resolve(request.result || null)
      }

      request.onerror = () => {
        reject(new Error('获取用户信息失败'))
      }
    })
  } catch (error) {
    console.error('getUser error:', error)
    return null
  }
}

/**
 * 保存用户信息
 */
export async function saveUser(userData) {
  try {
    const database = await initDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_USERS], 'readwrite')
      const store = transaction.objectStore(STORE_USERS)
      const request = store.put(userData)

      request.onsuccess = () => {
        localStorage.setItem('currentUserId', userData.id)
        resolve(userData)
      }

      request.onerror = () => {
        reject(new Error('保存用户信息失败'))
      }
    })
  } catch (error) {
    console.error('saveUser error:', error)
    throw error
  }
}

/**
 * 注册用户（调用后端API）
 */
export async function registerUser(account, password, nickname) {
  // manager 账号特殊处理（不需要验证邮箱/手机号格式）
  const isManager = account.trim() === 'manager'
  
  if (!isManager && !validateAccount(account)) {
    throw new Error('账号格式不正确，请输入邮箱或手机号')
  }

  if (!password || password.length < 6) {
    throw new Error('密码长度至少6位')
  }

  if (!nickname || nickname.trim().length === 0) {
    throw new Error('昵称不能为空')
  }

  try {
    // 导入 API 客户端
    const { default: authAPI } = await import('../api/auth')
    
    // 调用后端注册API
    const result = await authAPI.register(account.trim(), password, nickname.trim())
    
    if (result.success && result.user && result.session_token) {
      // 保存 session_token
      localStorage.setItem('session_token', result.session_token)
      
      // 保存用户信息到本地存储（用于离线访问）
      const userData = {
        ...result.user,
        updatedAt: new Date().toISOString()
      }
      
      // 保存当前用户ID
      localStorage.setItem('currentUserId', userData.id)
      
      // 同时保存到 IndexedDB（用于兼容）
      try {
        await saveUser(userData)
      } catch (dbError) {
        console.warn('保存用户到本地数据库失败（不影响注册）:', dbError)
      }
      
      return userData
    } else {
      throw new Error(result.detail || '注册失败')
    }
  } catch (error) {
    console.error('registerUser error:', error)
    // 如果是网络错误，提供更友好的错误信息
    if (error.response?.status === 400) {
      throw new Error(error.response.data?.detail || '输入信息有误')
    } else if (error.message) {
      throw error
    } else {
      throw new Error('注册失败，请检查网络连接')
    }
  }
}

/**
 * 登录用户（调用后端API）
 */
export async function loginUser(account, password) {
  try {
    console.group('🔐 [登录] 开始登录流程');
    console.log('📝 账号:', account);
    console.log('⏰ 开始时间:', new Date().toISOString());
    console.groupEnd();
    
    // 导入 API 客户端
    const { default: authAPI } = await import('../api/auth')
    
    // 调用后端登录API
    const result = await authAPI.login(account.trim(), password)
    
    console.group('✅ [登录] 登录API调用成功');
    console.log('📦 返回结果:', {
      success: result.success,
      hasUser: !!result.user,
      hasToken: !!result.session_token,
      userId: result.user?.id,
      account: result.user?.account
    });
    console.groupEnd();
    
    if (result.success && result.user && result.session_token) {
      // 保存 session_token
      localStorage.setItem('session_token', result.session_token)
      console.log('💾 [登录] 已保存 session_token');
      
      // 保存用户信息到本地存储（用于离线访问）
      const userData = {
        ...result.user,
        updatedAt: new Date().toISOString()
      }
      
      // 保存当前用户ID
      localStorage.setItem('currentUserId', userData.id)
      console.log('💾 [登录] 已保存用户ID:', userData.id);
      
      // 同时保存到 IndexedDB（用于兼容）
      try {
        await saveUser(userData)
        console.log('💾 [登录] 已保存用户信息到 IndexedDB');
      } catch (dbError) {
        console.warn('⚠️ [登录] 保存用户到本地数据库失败（不影响登录）:', dbError)
      }
      
      console.group('🎉 [登录] 登录成功完成');
      console.log('👤 用户信息:', {
        id: userData.id,
        account: userData.account,
        nickname: userData.nickname,
        level: userData.level
      });
      console.log('⏰ 完成时间:', new Date().toISOString());
      console.groupEnd();
      
      return userData
    } else {
      console.group('❌ [登录] 登录响应格式错误');
      console.error('📦 返回结果:', result);
      console.error('💡 可能原因:');
      console.error('   - 后端返回格式不符合预期');
      console.error('   - 缺少 user 或 session_token 字段');
      console.error('   - success 字段为 false');
      console.groupEnd();
      
      // 尝试从返回结果中提取错误信息
      const errorMsg = result.detail || result.error || result.message || '登录失败：响应格式错误'
      throw new Error(errorMsg)
    }
  } catch (error) {
    console.group('❌ [登录] 登录流程失败');
    console.error('📝 账号:', account);
    console.error('🔴 错误类型:', error?.response ? '服务器错误' : '网络/其他错误');
    console.error('📚 完整错误对象:', error);
    
    // 如果是网络错误，提供更友好的错误信息
    if (error?.response?.status === 401) {
      console.error('📊 HTTP 401: 账号或密码错误');
      console.groupEnd();
      throw new Error('账号或密码错误')
    } else if (error?.response?.status === 400) {
      console.error('📊 HTTP 400: 请求参数错误');
      console.error('📄 错误详情:', error.response.data?.detail);
      console.groupEnd();
      throw new Error(error.response.data?.detail || '输入信息有误')
    } else if (error?.response?.status >= 500) {
      console.error('📊 HTTP 500+: 服务器内部错误');
      console.error('📄 错误详情:', error.response.data);
      console.error('💡 建议: 检查后端日志');
      console.groupEnd();
      throw new Error('服务器错误，请稍后重试')
    } else if (error?.networkError || error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
      console.error('📡 网络错误: 无法连接到后端服务');
      console.error('🌐 后端地址:', error?.config?.baseURL || '未知');
      console.error('💡 建议: 检查后端服务是否运行');
      console.groupEnd();
      throw new Error('无法连接到服务器，请检查后端服务是否已启动')
    } else if (error?.message) {
      console.error('📝 错误消息:', error.message);
      console.groupEnd();
      // 确保抛出的是 Error 对象
      if (error instanceof Error) {
        throw error
      } else {
        throw new Error(error.message)
      }
    } else {
      console.error('❓ 未知错误:', error);
      console.error('❓ 错误类型:', typeof error);
      console.groupEnd();
      throw new Error(error?.toString() || '登录失败，请检查网络连接')
    }
  }
}

/**
 * 更新用户信息
 */
export async function updateUser(userId, updates) {
  try {
    const database = await initDB()
    
    // 获取当前用户
    const user = await new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_USERS], 'readonly')
      const store = transaction.objectStore(STORE_USERS)
      const request = store.get(userId)

      request.onsuccess = () => {
        resolve(request.result || null)
      }

      request.onerror = () => {
        reject(new Error('获取用户信息失败'))
      }
    })

    if (!user) {
      throw new Error('用户不存在')
    }

    // 合并更新
    const updatedUser = {
      ...user,
      ...updates,
      updatedAt: new Date().toISOString()
    }

    await saveUser(updatedUser)

    // 返回用户数据（不包含密码）
    const { password: _, ...userWithoutPassword } = updatedUser
    return userWithoutPassword
  } catch (error) {
    console.error('updateUser error:', error)
    throw error
  }
}

/**
 * 清除当前用户
 */
/**
 * 清除用户信息
 */
export async function clearUser() {
  // 清除 session_token
  localStorage.removeItem('session_token')
  localStorage.removeItem('currentUserId')
}

/**
 * 获取所有用户（管理员功能）
 */
export async function getAllUsers() {
  try {
    const database = await initDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_USERS], 'readonly')
      const store = transaction.objectStore(STORE_USERS)
      const request = store.getAll()

      request.onsuccess = () => {
        // 移除密码字段，返回用户列表
        const users = request.result.map(({ password: _, ...user }) => user)
        resolve(users)
      }

      request.onerror = () => {
        reject(new Error('获取用户列表失败'))
      }
    })
  } catch (error) {
    console.error('getAllUsers error:', error)
    throw error
  }
}

