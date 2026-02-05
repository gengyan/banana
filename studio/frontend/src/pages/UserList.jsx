import { useState, useEffect } from 'react'
import { getAllUsers } from '../utils/userStorage'
import adminAPI from '../api/admin'

function UserList() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [resettingUserId, setResettingUserId] = useState(null)

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      setLoading(true)
      setError('')
      const userList = await getAllUsers()
      // 按注册时间倒序排列
      userList.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
      setUsers(userList)
    } catch (err) {
      setError(err.message || '加载用户列表失败')
      console.error('加载用户列表失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
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
      setError(err.response?.data?.detail || err.message || '密码重置失败')
      setTimeout(() => setError(''), 5000)
    } finally {
      setResettingUserId(null)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto mt-20 max-w-6xl px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-white">加载中...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto mt-20 max-w-6xl px-4 py-8">
      <div className="rounded-3xl bg-white/[8%] p-8 backdrop-blur-sm">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-white">用户列表</h1>
          <button
            onClick={loadUsers}
            className="rounded-xl bg-white/10 px-4 py-2 text-sm font-medium text-white hover:bg-white/15 transition"
          >
            刷新
          </button>
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
                <th className="text-left py-3 px-4 text-sm font-medium text-white/70">注册时间</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-white/70">更新时间</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-white/70">操作</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-white/60">
                    暂无用户
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="py-3 px-4">
                      <div className="w-10 h-10 rounded-full overflow-hidden bg-white/10 border border-white/20 flex items-center justify-center">
                        {user.avatar ? (
                          <img
                            src={user.avatar}
                            alt={user.nickname}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span className="text-sm text-white/80">
                            {user.nickname?.charAt(0)?.toUpperCase() || 'U'}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-white">{user.nickname || '-'}</td>
                    <td className="py-3 px-4 text-white/90 font-mono text-sm">{user.account}</td>
                    <td className="py-3 px-4 text-white/70 text-sm">{getAccountType(user.account)}</td>
                    <td className="py-3 px-4 text-white/70 text-sm">{formatDate(user.createdAt)}</td>
                    <td className="py-3 px-4 text-white/70 text-sm">{formatDate(user.updatedAt)}</td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleResetPassword(user.id, user.account)}
                        disabled={resettingUserId === user.id || user.account === 'manager'}
                        className="rounded-lg bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/50 px-3 py-1.5 text-xs font-medium text-orange-400 transition disabled:opacity-50 disabled:cursor-not-allowed"
                        title={user.account === 'manager' ? '无法重置管理员密码' : '重置密码为 123456'}
                      >
                        {resettingUserId === user.id ? '重置中...' : '重置密码'}
                      </button>
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
  )
}

export default UserList

