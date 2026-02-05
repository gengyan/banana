import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ImageEditor from '../components/ImageEditor'

function Profile() {
  const { t } = useTranslation()
  const { user, updateUserInfo, logout } = useAuth()
  const navigate = useNavigate()
  const [nickname, setNickname] = useState(user?.nickname || '')
  const [avatar, setAvatar] = useState(user?.avatar || null)
  const [gender, setGender] = useState(user?.gender || '')
  const [age, setAge] = useState(user?.age ? String(user.age) : '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [editingImage, setEditingImage] = useState(null)
  const fileInputRef = useRef(null)

  // 当user更新时，同步更新表单数据
  useEffect(() => {
    if (user) {
      setNickname(user.nickname || '')
      setAvatar(user.avatar || null)
      setGender(user.gender || '')
      setAge(user.age ? String(user.age) : '')
    }
  }, [user])

  const handleAvatarChange = (e) => {
    const file = e.target.files[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setError('请选择图片文件')
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      setError('图片大小不能超过5MB')
      return
    }

    // 打开编辑界面
    const reader = new FileReader()
    reader.onloadend = () => {
      setEditingImage(reader.result)
      setError('')
    }
    reader.onerror = () => {
      setError('图片读取失败')
    }
    reader.readAsDataURL(file)
    // 清空 input
    e.target.value = ''
  }

  const handleImageEditorSave = (file, preview) => {
    setAvatar(preview)
    setEditingImage(null)
  }

  const handleImageEditorCancel = () => {
    setEditingImage(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!nickname.trim()) {
      setError('昵称不能为空')
      return
    }

    if (nickname.trim().length > 20) {
      setError('昵称长度不能超过20个字符')
      return
    }

    // 验证年龄
    if (age && (isNaN(age) || parseInt(age) < 1 || parseInt(age) > 150)) {
      setError('请输入有效的年龄（1-150）')
      return
    }

    setLoading(true)
    try {
      const updates = {
        nickname: nickname.trim()
      }
      if (avatar) {
        updates.avatar = avatar
      }
      if (gender) {
        updates.gender = gender
      }
      if (age) {
        updates.age = parseInt(age)
      } else {
        updates.age = null
      }

      const result = await updateUserInfo(updates)
      if (result.success) {
        setSuccess(t('profile.updateSuccess', '信息更新成功'))
        setTimeout(() => setSuccess(''), 3000)
      } else {
        setError(result.error || '更新失败，请稍后重试')
      }
    } catch (err) {
      setError(err.message || '更新失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    if (window.confirm('确定要退出登录吗？')) {
      await logout()
      navigate('/login')
    }
  }

  return (
    <>
      {/* 图片编辑器 */}
      {editingImage && (
        <ImageEditor
          imageSrc={editingImage}
          onSave={handleImageEditorSave}
          onCancel={handleImageEditorCancel}
          aspectRatio={1}
        />
      )}
      
      <div className="container mx-auto mt-20 max-w-2xl px-4 py-8">
        <div className="rounded-3xl bg-white/[8%] p-8 backdrop-blur-sm">
        <h1 className="mb-6 text-3xl font-bold text-white">我的信息</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 头像 */}
          <div className="flex flex-col items-center mb-6">
            <div className="relative">
              <div className="w-32 h-32 rounded-full overflow-hidden bg-white/10 border-4 border-white/20 mb-4">
                {avatar ? (
                  <img
                    src={avatar}
                    alt="头像"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-white/60 text-4xl">
                    {user?.nickname?.charAt(0)?.toUpperCase() || 'U'}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="absolute bottom-0 right-0 bg-purple-500 hover:bg-purple-600 text-white rounded-full p-2 transition"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleAvatarChange}
                className="hidden"
              />
            </div>
            <p className="text-sm text-white/60">{t('profile.avatarHint', '点击图标更换头像')}</p>
          </div>

          {/* 账号信息（只读） */}
          <div className="rounded-xl bg-white/[4%] p-4">
            <label className="block text-sm font-medium text-white/70 mb-2">
              {t('profile.account', '账号')}
            </label>
            <input
              type="text"
              value={user?.account || ''}
              disabled
              className="w-full rounded-xl border-none bg-white/[8%] px-4 py-3 text-white/60 cursor-not-allowed"
            />
          </div>

          {/* 昵称 */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">
              {t('profile.nickname', '昵称')} <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder={t('profile.nickname', '请输入昵称')}
              maxLength={20}
              className="w-full rounded-xl border-none bg-white/[12%] px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-white/20"
              required
            />
          </div>

          {/* 性别 */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">
              {t('profile.gender', '性别')}
            </label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="w-full rounded-xl border-none bg-white/[12%] px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-white/20"
            >
              <option value="">{t('profile.genderPlaceholder', '请选择')}</option>
              <option value="male">{t('profile.genderMale', '男')}</option>
              <option value="female">{t('profile.genderFemale', '女')}</option>
              <option value="other">{t('profile.genderOther', '其他')}</option>
            </select>
          </div>

          {/* 年龄 */}
          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">
              {t('profile.age', '年龄')}
            </label>
            <input
              type="number"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder={t('profile.agePlaceholder', '请输入年龄')}
              min="1"
              max="150"
              className="w-full rounded-xl border-none bg-white/[12%] px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-white/20"
            />
          </div>

          {error && (
            <div className="rounded-xl bg-red-500/20 border border-red-500/50 p-4 text-red-400 text-sm">
              {error}
            </div>
          )}

          {success && (
            <div className="rounded-xl bg-green-500/20 border border-green-500/50 p-4 text-green-400 text-sm">
              {success}
            </div>
          )}

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 px-6 py-3 text-lg font-bold text-white transition hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('profile.saving', '保存中...') : t('profile.save', '保存修改')}
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-xl bg-red-500/20 border border-red-500/50 px-6 py-3 text-lg font-bold text-red-400 transition hover:bg-red-500/30 active:scale-[0.97]"
            >
              退出登录
            </button>
          </div>
        </form>
      </div>
    </div>
    </>
  )
}

export default Profile

