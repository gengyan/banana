import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { feedbackAPI } from '../api'

function CustomerService() {
  const { t } = useTranslation()
  const [feedback, setFeedback] = useState('')
  const [contact, setContact] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [showQrModal, setShowQrModal] = useState(false)
  const [feedbacks, setFeedbacks] = useState([])
  const [loadingFeedbacks, setLoadingFeedbacks] = useState(false)
  const [selectedFeedback, setSelectedFeedback] = useState(null)
  const [showDialogModal, setShowDialogModal] = useState(false)

  // 加载反馈记录
  useEffect(() => {
    loadFeedbacks()
  }, [])

  const loadFeedbacks = async () => {
    setLoadingFeedbacks(true)
    try {
      const result = await feedbackAPI.getMyFeedbacks()
      if (result.success) {
        setFeedbacks(result.feedbacks || [])
      }
    } catch (err) {
      console.error('加载反馈记录失败:', err)
      // 如果是 "未登录，请先登录" 错误（来自 checkAuth），提供更友好的提示
      if (err.message === '未登录，请先登录' || err.message?.includes('未登录')) {
        console.error('❌ 检测到登录状态丢失:', {
          error: err.message,
          session_token: localStorage.getItem('session_token'),
          currentUserId: localStorage.getItem('currentUserId'),
          suggestion: '请重新登录'
        })
        // 不显示错误，避免干扰用户体验（因为可能是 token 过期）
      } else if (err.response?.status !== 401) {
        console.warn('加载反馈记录时出现错误:', err.response?.data || err.message)
      }
    } finally {
      setLoadingFeedbacks(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    
    if (!feedback.trim()) {
      setError(t('customerService.feedbackRequired', '反馈意见不能为空'))
      return
    }
    
    if (!contact.trim()) {
      setError(t('customerService.contactRequired', '联系方式不能为空'))
      return
    }
    
    setLoading(true)
    
    try {
      const result = await feedbackAPI.submitFeedback(feedback.trim(), contact.trim())
      if (result.success) {
        setSuccess(t('customerService.submitSuccess', '反馈提交成功，我们会尽快与您联系！'))
        setFeedback('')
        setContact('')
        // 重新加载反馈列表
        loadFeedbacks()
        // 3秒后清除成功消息
        setTimeout(() => {
          setSuccess('')
        }, 3000)
      } else {
        setError(result.message || t('customerService.submitError', '提交失败，请稍后重试'))
      }
    } catch (err) {
      console.error('提交反馈失败:', err)
      console.error('错误详情:', {
        status: err.response?.status,
        data: err.response?.data,
        message: err.message
      })
      
      let errorMessage = t('customerService.submitError', '提交失败，请稍后重试')
      
      // 检查是否是 checkAuth 抛出的错误
      if (err.message === '未登录，请先登录' || err.message?.includes('未登录')) {
        errorMessage = '登录状态已失效，请刷新页面或重新登录'
        console.error('❌ 提交反馈时检测到登录状态丢失，建议用户重新登录')
      } else if (err.response?.status === 401) {
        errorMessage = '未登录或会话已过期，请重新登录'
      } else if (err.response?.status === 400) {
        errorMessage = err.response?.data?.detail || '输入信息有误，请检查后重试'
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail
      } else if (err.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleViewFeedback = (feedbackItem) => {
    setSelectedFeedback(feedbackItem)
    setShowDialogModal(true)
  }

  const formatDate = (dateString) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="container mx-auto mt-20 max-w-4xl px-4 py-8">
      <div className="mb-8 text-center">
        <h1 className="mb-2 text-4xl font-bold text-white">
          {t('customerService.title', '客户服务')}
        </h1>
        <p className="text-white/60">
          {t('customerService.subtitle', '我们随时为您提供帮助和支持')}
        </p>
      </div>

      <div className="space-y-6">
        {/* 反馈表单 */}
        <div className="rounded-3xl bg-white/[8%] backdrop-blur-sm p-8 border border-white/10">
          <h2 className="mb-6 text-2xl font-bold text-white">
            {t('customerService.submitFeedback', '提交反馈')}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="feedback" className="block mb-2 text-sm font-medium text-white">
                {t('customerService.feedbackLabel', '反馈意见')}
              </label>
              <textarea
                id="feedback"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={6}
                className="w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                placeholder={t('customerService.feedbackPlaceholder', '请输入您的反馈意见...')}
              />
            </div>

            <div>
              <label htmlFor="contact" className="block mb-2 text-sm font-medium text-white">
                {t('customerService.contactLabel', '联系方式')}
              </label>
              <input
                type="text"
                id="contact"
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                className="w-full rounded-xl bg-white/10 border border-white/20 px-4 py-3 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder={t('customerService.contactPlaceholder', '请输入您的微信号、QQ号或手机号')}
              />
            </div>

            {error && (
              <div className="rounded-xl bg-red-500/20 border border-red-500/30 px-4 py-3 text-red-200">
                {error}
              </div>
            )}

            {success && (
              <div className="rounded-xl bg-green-500/20 border border-green-500/30 px-4 py-3 text-green-200">
                {success}
              </div>
            )}

            <div className="flex gap-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 px-6 py-3 font-bold text-white transition hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.97]"
              >
                {loading ? t('customerService.submitting', '提交中...') : t('customerService.submit', '提交反馈')}
              </button>
              
              <button
                type="button"
                onClick={() => setShowQrModal(true)}
                className="flex-1 rounded-xl bg-white/10 border border-white/20 px-6 py-3 font-bold text-white transition hover:bg-white/15 active:scale-[0.97]"
              >
                {t('customerService.contactService', '联系客服')}
              </button>
            </div>
          </form>
        </div>

        {/* 反馈记录列表 */}
        <div className="rounded-3xl bg-white/[8%] backdrop-blur-sm p-8 border border-white/10">
          <h2 className="mb-6 text-2xl font-bold text-white">
            {t('customerService.myFeedbacks', '我的反馈记录')}
          </h2>
          
          {loadingFeedbacks ? (
            <div className="text-center py-8 text-white/60">
              {t('customerService.loading', '加载中...')}
            </div>
          ) : feedbacks.length === 0 ? (
            <div className="text-center py-8 text-white/60">
              {t('customerService.noFeedbacks', '暂无反馈记录')}
            </div>
          ) : (
            <div className="space-y-4">
              {feedbacks.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleViewFeedback(item)}
                  className="rounded-xl bg-white/5 border border-white/10 p-4 cursor-pointer hover:bg-white/10 transition"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-white line-clamp-2 mb-2">{item.feedback}</p>
                      <div className="flex items-center gap-4 text-sm text-white/60">
                        <span>{formatDate(item.createdAt)}</span>
                        {item.reply && (
                          <span className="text-green-400">
                            {t('customerService.replied', '已回复')}
                          </span>
                        )}
                      </div>
                    </div>
                    {item.reply && (
                      <div className="ml-4">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
                          {t('customerService.hasReply', '已回复')}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 二维码弹框 */}
      {showQrModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
          onClick={() => setShowQrModal(false)}
        >
          <div 
            className="relative rounded-3xl bg-white/10 backdrop-blur-lg border border-white/20 p-8 max-w-md mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowQrModal(false)}
              className="absolute top-4 right-4 text-white/60 hover:text-white transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            <div className="text-center">
              <h3 className="mb-4 text-2xl font-bold text-white">
                {t('customerService.scanQRCode', '扫描二维码添加客服微信')}
              </h3>
              <div className="mb-4 flex justify-center">
                <img
                  src="/customerservice.jpg"
                  alt={t('customerService.qrCode', '客服微信二维码')}
                  className="rounded-xl border-2 border-white/20 max-w-full h-auto"
                />
              </div>
              <p className="text-white/60 text-sm">
                {t('customerService.qrHint', '使用微信扫一扫添加客服微信')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 对话弹框 */}
      {showDialogModal && selectedFeedback && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          onClick={() => setShowDialogModal(false)}
        >
          <div 
            className="relative rounded-3xl bg-white/10 backdrop-blur-lg border border-white/20 p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowDialogModal(false)}
              className="absolute top-4 right-4 text-white/60 hover:text-white transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            <h3 className="mb-6 text-2xl font-bold text-white">
              {t('customerService.feedbackDetail', '反馈详情')}
            </h3>
            
            <div className="space-y-4">
              {/* 用户反馈 */}
              <div className="rounded-xl bg-purple-500/20 border border-purple-500/30 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-medium text-purple-300">
                    {t('customerService.you', '您')}
                  </span>
                  <span className="text-xs text-white/60">
                    {formatDate(selectedFeedback.createdAt)}
                  </span>
                </div>
                <p className="text-white whitespace-pre-wrap">{selectedFeedback.feedback}</p>
                <p className="mt-2 text-sm text-white/60">
                  {t('customerService.contact', '联系方式')}: {selectedFeedback.contact}
                </p>
              </div>

              {/* 客服回复 */}
              {selectedFeedback.reply ? (
                <div className="rounded-xl bg-blue-500/20 border border-blue-500/30 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-blue-300">
                      {t('customerService.service', '客服')}
                    </span>
                    <span className="text-xs text-white/60">
                      {formatDate(selectedFeedback.repliedAt)}
                    </span>
                  </div>
                  <p className="text-white whitespace-pre-wrap">{selectedFeedback.reply}</p>
                </div>
              ) : (
                <div className="rounded-xl bg-white/5 border border-white/10 p-4 text-center text-white/60">
                  {t('customerService.noReplyYet', '客服尚未回复，请耐心等待')}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CustomerService
