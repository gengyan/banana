import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { USER_LEVELS } from '../components/UserLevelBadge'
import { useAuth } from '../contexts/AuthContext'
import { adminAPI } from '../api'

function ManagerPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [userFeedbacks, setUserFeedbacks] = useState([])
  const [loadingFeedbacks, setLoadingFeedbacks] = useState(false)
  const [selectedFeedback, setSelectedFeedback] = useState(null)
  const [showReplyModal, setShowReplyModal] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [submittingReply, setSubmittingReply] = useState(false)
  const [resettingUserId, setResettingUserId] = useState(null)

  // 检查是否是 manager 用户
  useEffect(() => {
    if (!user) {
      navigate('/login')
      return
    }
    
    if (user.account !== 'manager') {
      navigate('/')
      return
    }
    
    // 在加载用户列表前，检查 session_token 是否存在
    const sessionToken = localStorage.getItem('session_token')
    if (!sessionToken) {
      console.error('❌ ManagerPage: 检测到用户已登录但缺少 session_token')
      console.error('调试信息:', {
        user: user,
        session_token: sessionToken,
        currentUserId: localStorage.getItem('currentUserId'),
        localStorage_keys: Object.keys(localStorage)
      })
      console.warn('⚠️ 登录状态失效，自动跳转到登录页面')
      // 清除本地存储
      localStorage.removeItem('session_token')
      localStorage.removeItem('currentUserId')
      // 跳转到登录页
      navigate('/login')
      return
    }
    
    loadUsers()
  }, [user, navigate])

  const loadUsers = async () => {
    try {
      setLoading(true)
      setError('')
      const result = await adminAPI.getAllUsers()
      if (result.success) {
        const userList = result.users || []
        userList.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
        setUsers(userList)
      }
    } catch (err) {
      console.error('加载用户列表失败:', err)
      console.error('错误详情:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        code: err.code,
        session_token: localStorage.getItem('session_token'),
        currentUserId: localStorage.getItem('currentUserId'),
        user: user
      })
      
      // 检查是否是网络错误（后端服务未运行）
      if (err.message === 'Network Error' || err.code === 'ERR_NETWORK' || err.message?.includes('Network')) {
        console.error('❌ 网络错误：无法连接到后端服务')
        setError('无法连接到后端服务，请检查后端服务是否已启动（http://localhost:8000）')
        return
      }
      
      // 检查是否是 "未登录，请先登录" 错误（来自 checkAuth）
      if (err.message === '未登录，请先登录' || err.message?.includes('未登录')) {
        console.error('❌ 检测到登录状态丢失，但用户信息存在:', {
          user: user,
          session_token: localStorage.getItem('session_token'),
          suggestion: '可能是后端重启导致 session 丢失，请重新登录'
        })
        console.warn('⚠️ 登录状态失效，自动跳转到登录页面')
        // 清除本地存储
        localStorage.removeItem('session_token')
        localStorage.removeItem('currentUserId')
        // 跳转到登录页
        navigate('/login')
        return
      } else if (err.response?.status === 401) {
        console.warn('⚠️ 会话已过期（401），自动跳转到登录页面')
        // 清除本地存储
        localStorage.removeItem('session_token')
        localStorage.removeItem('currentUserId')
        // 跳转到登录页
        navigate('/login')
        return
      } else {
        setError(err.response?.data?.detail || err.message || '加载用户列表失败')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadUserFeedbacks = async (userId, userAccount) => {
    try {
      setLoadingFeedbacks(true)
      const allFeedbacks = await adminAPI.getAllFeedbacks()
      if (allFeedbacks.success) {
        // 特殊处理 manager 账号：如果账号是 manager，使用 'manager_user' 作为 user_id 来过滤
        const targetUserId = (userAccount === 'manager') ? 'manager_user' : userId
        console.log('加载用户反馈:', {
          userId,
          userAccount,
          targetUserId,
          totalFeedbacks: allFeedbacks.feedbacks?.length || 0
        })
        
        const filteredFeedbacks = (allFeedbacks.feedbacks || []).filter(f => f.user_id === targetUserId)
        console.log('过滤后的反馈:', filteredFeedbacks.length)
        setUserFeedbacks(filteredFeedbacks)
      }
    } catch (err) {
      console.error('加载用户反馈失败:', err)
      // 如果是登录状态丢失，记录详细信息
      if (err.message === '未登录，请先登录' || err.message?.includes('未登录')) {
        console.error('❌ 加载反馈时检测到登录状态丢失')
      }
      setUserFeedbacks([])
    } finally {
      setLoadingFeedbacks(false)
    }
  }

  const handleLevelChange = async (userId, newLevel) => {
    try {
      setError('')
      setSuccess('')
      const result = await adminAPI.updateUser(userId, { level: newLevel })
      if (result.success) {
        setSuccess(`用户等级已更新为 ${USER_LEVELS[newLevel]?.name || newLevel}`)
        await loadUsers()
        setTimeout(() => setSuccess(''), 3000)
      }
    } catch (err) {
      console.error('更新用户等级失败:', err)
      // 检查是否是登录状态丢失
      if (err.message === '未登录，请先登录' || err.message?.includes('未登录') || err.response?.status === 401) {
        console.warn('⚠️ 登录状态失效，自动跳转到登录页面')
        localStorage.removeItem('session_token')
        localStorage.removeItem('currentUserId')
        navigate('/login')
        return
      } else {
        setError(err.response?.data?.detail || err.message || '更新用户等级失败')
      }
    }
  }

  const handleViewFeedbacks = async (userItem) => {
    setSelectedUser(userItem)
    setShowFeedbackModal(true)
    await loadUserFeedbacks(userItem.id, userItem.account)
  }

  const handleReplyFeedback = (feedbackItem) => {
    setSelectedFeedback(feedbackItem)
    setReplyText('')
    setShowReplyModal(true)
  }

  const handleSubmitReply = async () => {
    if (!replyText.trim()) {
      setError('回复内容不能为空')
      return
    }

    try {
      setSubmittingReply(true)
      setError('')
      const result = await adminAPI.replyFeedback(selectedFeedback.id, replyText.trim())
      if (result.success) {
        setSuccess('回复成功')
        setShowReplyModal(false)
        // 重新加载反馈列表
        await loadUserFeedbacks(selectedUser.id, selectedUser.account)
        setTimeout(() => setSuccess(''), 3000)
      }
    } catch (err) {
      console.error('回复失败:', err)
      // 检查是否是登录状态丢失
      if (err.message === '未登录，请先登录' || err.message?.includes('未登录') || err.response?.status === 401) {
        console.warn('⚠️ 登录状态失效，自动跳转到登录页面')
        localStorage.removeItem('session_token')
        localStorage.removeItem('currentUserId')
        navigate('/login')
        return
      } else {
        setError(err.response?.data?.detail || err.message || '回复失败')
      }
    } finally {
      setSubmittingReply(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getAccountType = (account) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(account) ? '邮箱' : '手机号'
  }

  const handleResetPassword = async (userId, account) => {
    if (!confirm(`确定要将用户 "${account}" 的密码重置为 123456 吗？`)) {
      return
    }

    try {
      setResettingUserId(userId)
      setError('')
      setSuccess('')
      
      const result = await adminAPI.resetUserPassword(userId)
      
      if (result.success) {
        setSuccess(`用户 "${account}" 的密码已重置为 123456`)
        setTimeout(() => setSuccess(''), 5000)
      } else {
        setError(result.message || '密码重置失败')
        setTimeout(() => setError(''), 5000)
      }
    } catch (err) {
      console.error('重置密码失败:', err)
      // 检查是否是登录状态丢失
      if (err.message === '未登录，请先登录' || err.message?.includes('未登录') || err.response?.status === 401) {
        console.warn('⚠️ 登录状态失效，自动跳转到登录页面')
        localStorage.removeItem('session_token')
        localStorage.removeItem('currentUserId')
        navigate('/login')
        return
      } else {
        setError(err.response?.data?.detail || err.message || '密码重置失败')
        setTimeout(() => setError(''), 5000)
      }
    } finally {
      setResettingUserId(null)
    }
  }

  if (!user || user.account !== 'manager') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0e0e0e]">
        <div className="text-white">加载中...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0e0e0e]">
      <div className="container mx-auto max-w-7xl px-4 py-8">
        <div className="rounded-3xl bg-white/[8%] p-8 backdrop-blur-sm">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-3xl font-bold text-white">用户管理</h1>
            <div className="flex gap-3">
              <button
                onClick={loadUsers}
                disabled={loading}
                className="rounded-xl bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/15 transition disabled:opacity-50"
              >
                {loading ? '加载中...' : '刷新'}
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-6 rounded-xl bg-red-500/20 border border-red-500/50 p-4 text-red-400 text-sm">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-6 rounded-xl bg-green-500/20 border border-green-500/50 p-4 text-green-400 text-sm">
              {success}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/70">头像</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/70">昵称</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/70">账号</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/70">账号类型</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/70">用户等级</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/70">反馈</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/70">注册时间</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-white/70">操作</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="py-8 text-center text-white/60">
                      {loading ? '加载中...' : '暂无用户'}
                    </td>
                  </tr>
                ) : (
                  users.map((userItem) => (
                    <tr key={userItem.id} className="border-b border-white/5 hover:bg-white/5 transition">
                      <td className="py-3 px-4">
                        <div className="w-10 h-10 rounded-full overflow-hidden bg-white/10 border border-white/20 flex items-center justify-center">
                          {userItem.avatar ? (
                            <img
                              src={userItem.avatar}
                              alt={userItem.nickname}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <span className="text-sm text-white/80">
                              {userItem.nickname?.charAt(0)?.toUpperCase() || 'U'}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-white">{userItem.nickname || '-'}</td>
                      <td className="py-3 px-4 text-white/90 font-mono text-sm">{userItem.account}</td>
                      <td className="py-3 px-4 text-white/70 text-sm">{getAccountType(userItem.account)}</td>
                      <td className="py-3 px-4">
                        <span
                          className="inline-block px-3 py-1 rounded-full text-xs font-medium"
                          style={{
                            backgroundColor: USER_LEVELS[userItem.level]?.bgColor || USER_LEVELS.normal.bgColor,
                            color: USER_LEVELS[userItem.level]?.color || USER_LEVELS.normal.color,
                            border: `1px solid ${USER_LEVELS[userItem.level]?.borderColor || USER_LEVELS.normal.borderColor}`,
                          }}
                        >
                          {USER_LEVELS[userItem.level]?.name || USER_LEVELS.normal.name}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {userItem.feedbackCount > 0 ? (
                          <button
                            onClick={() => handleViewFeedbacks(userItem)}
                            className="text-blue-400 hover:text-blue-300 underline text-sm"
                          >
                            {userItem.feedbackCount} 条反馈
                          </button>
                        ) : (
                          <span className="text-white/40 text-sm">无反馈</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-white/70 text-sm">{formatDate(userItem.createdAt)}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <select
                            value={userItem.level || 'normal'}
                            onChange={(e) => handleLevelChange(userItem.id, e.target.value)}
                            className="rounded-lg bg-white/10 border border-white/20 px-2.5 py-1.5 text-xs text-white focus:outline-none focus:ring-2 focus:ring-white/20 flex-1"
                          >
                            <option value="normal">普通用户</option>
                            <option value="basic">基础版</option>
                            <option value="professional">专业版</option>
                            <option value="enterprise">企业版</option>
                          </select>
                          <button
                            onClick={() => handleResetPassword(userItem.id, userItem.account)}
                            disabled={resettingUserId === userItem.id || userItem.account === 'manager'}
                            className="rounded-lg bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/50 px-2.5 py-1.5 text-xs font-medium text-orange-400 transition disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                            title={userItem.account === 'manager' ? '无法重置管理员密码' : '重置密码为 123456'}
                          >
                            {resettingUserId === userItem.id ? '重置中...' : '重置密码'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-6 text-sm text-white/60">
            共 {users.length} 个用户
          </div>
        </div>
      </div>

      {/* 用户反馈列表弹框 */}
      {showFeedbackModal && selectedUser && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          onClick={() => setShowFeedbackModal(false)}
        >
          <div 
            className="relative rounded-3xl bg-white/10 backdrop-blur-lg border border-white/20 p-6 max-w-3xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowFeedbackModal(false)}
              className="absolute top-4 right-4 text-white/60 hover:text-white transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            <h3 className="mb-6 text-2xl font-bold text-white">
              {selectedUser.nickname || selectedUser.account} 的反馈记录
            </h3>
            
            {loadingFeedbacks ? (
              <div className="text-center py-8 text-white/60">加载中...</div>
            ) : userFeedbacks.length === 0 ? (
              <div className="text-center py-8 text-white/60">该用户暂无反馈记录</div>
            ) : (
              <div className="space-y-4">
                {userFeedbacks.map((feedback) => (
                  <div
                    key={feedback.id}
                    className="rounded-xl bg-white/5 border border-white/10 p-4"
                  >
                    <div className="mb-3">
                      <p className="text-white whitespace-pre-wrap mb-2">{feedback.feedback}</p>
                      <div className="flex items-center justify-between text-sm text-white/60">
                        <span>联系方式: {feedback.contact}</span>
                        <span>{formatDate(feedback.createdAt)}</span>
                      </div>
                    </div>
                    {feedback.reply ? (
                      <div className="mt-3 pt-3 border-t border-white/10">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-blue-300">管理员回复</span>
                          <span className="text-xs text-white/60">{formatDate(feedback.repliedAt)}</span>
                        </div>
                        <p className="text-white/90 whitespace-pre-wrap">{feedback.reply}</p>
                      </div>
                    ) : (
                      <div className="mt-3">
                        <button
                          onClick={() => handleReplyFeedback(feedback)}
                          className="rounded-xl bg-blue-500/20 border border-blue-500/30 px-4 py-2 text-sm font-medium text-blue-300 hover:bg-blue-500/30 transition"
                        >
                          回复反馈
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 回复反馈弹框 */}
      {showReplyModal && selectedFeedback && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          onClick={() => setShowReplyModal(false)}
        >
          <div 
            className="relative rounded-3xl bg-white/10 backdrop-blur-lg border border-white/20 p-6 max-w-2xl w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowReplyModal(false)}
              className="absolute top-4 right-4 text-white/60 hover:text-white transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            <h3 className="mb-4 text-2xl font-bold text-white">回复反馈</h3>
            
            <div className="mb-4 rounded-xl bg-white/5 border border-white/10 p-4">
              <p className="text-white/90 mb-2">{selectedFeedback.feedback}</p>
              <p className="text-sm text-white/60">联系方式: {selectedFeedback.contact}</p>
            </div>
            
            <div className="mb-4">
              <label className="block mb-2 text-sm font-medium text-white">回复内容</label>
              <textarea
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                rows={6}
                className="w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="请输入回复内容..."
              />
            </div>
            
            <div className="flex gap-4">
              <button
                onClick={handleSubmitReply}
                disabled={submittingReply || !replyText.trim()}
                className="flex-1 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 px-6 py-3 font-bold text-white transition hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.97]"
              >
                {submittingReply ? '提交中...' : '提交回复'}
              </button>
              <button
                onClick={() => setShowReplyModal(false)}
                className="px-6 py-3 rounded-xl bg-white/10 border border-white/20 text-white hover:bg-white/15 transition"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ManagerPage
