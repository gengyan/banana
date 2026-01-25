import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { chatAPI } from '../api'
import { useProject } from '../hooks/useProject'
import { saveChatHistory, saveChatHistoryWithError } from '../utils/chatHistorySaver'
import ImageEditor from '../components/ImageEditor'

function Working() {
  const location = useLocation()
  const [message, setMessage] = useState('')
  const [mode, setMode] = useState('banana')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([])
  const [referenceImage, setReferenceImage] = useState(null)
  const [referenceImagePreview, setReferenceImagePreview] = useState(null)
  const [editingImage, setEditingImage] = useState(null)
  const [isSaving, setIsSaving] = useState(false) // 防重复保存标记
  const { currentProjectId, createNewProject, saveMessageToProject, clearProject } = useProject()

  // 监听清空标志
  useEffect(() => {
    if (location.state?.clear) {
      // 清空所有状态
      setMessage('')
      setMode('chat')
      setMessages([])
      setReferenceImage(null)
      setReferenceImagePreview(null)
      setEditingImage(null)
      setLoading(false)
      // 清空当前项目，下次提交时会创建新项目
      clearProject()
      // 清除 location state，避免重复清空
      window.history.replaceState({}, document.title)
    }
  }, [location.state, clearProject])

  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      // 创建预览并打开编辑界面
      const reader = new FileReader()
      reader.onloadend = () => {
        setEditingImage(reader.result)
      }
      reader.readAsDataURL(file)
      // 清空 input
      e.target.value = ''
    }
  }

  const handleImageEditorSave = (file, preview) => {
    setReferenceImage(file)
    setReferenceImagePreview(preview)
    setEditingImage(null)
  }

  const handleImageEditorCancel = () => {
    setEditingImage(null)
  }

  const handleRemoveImage = () => {
    setReferenceImage(null)
    setReferenceImagePreview(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!message.trim()) return

    const userMessage = { 
      role: 'user', 
      content: message,
      image: referenceImagePreview || null
    }
    setMessages([...messages, userMessage])
    setMessage('')
    setLoading(true)

    try {
      const history = messages.map(msg => ({
        role: msg.role === 'user' ? 'user' : 'model',
        parts: [{ text: msg.content }]
      }))

      // 调试：打印参考图片信息
      console.log('提交时的状态:', {
        mode,
        hasReferenceImage: !!referenceImage,
        referenceImageType: referenceImage?.type,
        referenceImageSize: referenceImage?.size,
        message
      })
      
      const result = await chatAPI.chat(message, mode, history, referenceImage)
      
      // 检查返回结果
      if (!result) {
        throw new Error('API 返回结果为空')
      }
      
      // 检查是否有 response 字段
      if (!result.response) {
        console.warn('⚠️ [Working] result.response 为空，使用默认消息')
        console.warn('⚠️ [Working] result 内容:', result)
      }
      
      const aiMessage = { role: 'assistant', content: result.response || '图片生成成功，但未返回文本消息' }
      setMessages([...messages, userMessage, aiMessage])
      
      // 在生成图片后统一保存聊天记录以及生成的图片（一次会话只保存一次）
      // 防重复保存：如果已经在保存中，跳过
      if (isSaving) {
        console.warn('⚠️ [Working] 正在保存中，跳过重复保存')
        return
      }
      
      try {
        setIsSaving(true) // 设置保存标记，防止重复保存
        
        // 准备参考图片数据
        const referenceImageData = referenceImagePreview || null

        // 准备AI生成的图片数据
        // ⚠️ 重要：IndexedDB 支持存储大图片，直接传递图片数据
        // saveMessage 会自动处理：大图片存储到独立的 images 存储，小图片直接存储在消息中
        let aiImageData = result.image_data || result.image_url || null
        if (aiImageData && typeof aiImageData === 'string' && !aiImageData.startsWith('data:')) {
          // 如果不是 Data URL，构建 Data URL
          const format = result.image_format || 'jpeg'
          aiImageData = `data:image/${format};base64,${aiImageData}`
        }
        if (aiImageData) {
          console.log(`🖼️ [Working] AI图片数据已准备，大小: ${(aiImageData.length / 1024).toFixed(2)} KB`)
        }

        // 使用统一的保存模块
        const saveResult = await saveChatHistory({
          currentProjectId,
          createNewProject,
          userMessage: message,
          referenceImage: referenceImageData,
          aiImageData: aiImageData,
          aiResponse: result.response || '无响应',
          source: 'Working'
        })

        if (!saveResult.success) {
          console.error('❌ [Working] 保存返回失败:', saveResult)
          throw new Error(saveResult.error || '保存失败')
        }
        console.log('✅ [Working] 保存成功，项目ID:', saveResult.projectId)
      } catch (error) {
        console.error('❌ [Working] 保存消息失败:', error)
        console.error('❌ [Working] 错误类型:', error.name)
        console.error('❌ [Working] 错误消息:', error.message)
        console.error('❌ [Working] 错误堆栈:', error.stack)
        console.error('❌ [Working] 完整错误对象:', error)
        alert(`保存聊天记录失败: ${error.message || '未知错误'}。请检查控制台查看详细信息。`)
      } finally {
        setIsSaving(false) // 清除保存标记
      }
      
      // 清除参考图片
      setReferenceImage(null)
      setReferenceImagePreview(null)
    } catch (error) {
      console.error('❌ [Working] 请求错误:', error)
      console.error('❌ [Working] 错误类型:', error.name)
      console.error('❌ [Working] 错误消息:', error.message)
      console.error('❌ [Working] 错误堆栈:', error.stack)
      console.error('❌ [Working] 完整错误对象:', error)
      
      // 检查是否是 axios 错误，可能包含后端返回的错误信息
      let errorMessage = '抱歉，发生了错误。请稍后重试。'
      if (error.response && error.response.data) {
        const errorData = error.response.data
        errorMessage = errorData.error_message || errorData.detail || errorData.response || errorMessage
        console.error('后端错误详情:', {
          error_code: errorData.error_code,
          error_message: errorData.error_message,
          error_detail: errorData.error_detail,
          detail: errorData.detail
        })
      } else if (error.message) {
        errorMessage = error.message
      }
      
      const errorMsg = { role: 'assistant', content: errorMessage }
      setMessages([...messages, userMessage, errorMsg])
    } finally {
      setLoading(false)
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
        />
      )}
      
      <div className="flex h-full w-full">
        {/* 主工作区 */}
      <div className="flex-1 p-4">
        <div className="h-full rounded-3xl bg-[#121212] p-6">
          <h2 className="mb-4 text-2xl font-semibold text-white">工作区</h2>
          <div className="h-[calc(100%-100px)] overflow-y-auto">
            {/* 这里可以显示生成的图片或工作内容 */}
            <div className="flex h-full items-center justify-center text-white/40">
              工作区内容将在这里显示
            </div>
          </div>
        </div>
      </div>

      {/* 聊天侧边栏 */}
      <div className="gradient-border absolute left-4 top-3 bottom-3 z-50 flex min-w-0 w-[480px] flex-col overflow-hidden rounded-[32px] bg-[#040404] max-md:inset-x-2 max-md:w-[calc(100vw-16px)]">
        <div className="flex h-full flex-col">
          <div className="flex h-12 w-full items-center justify-between border-b border-white/[12%] p-3">
            <span className="max-w-[214px] truncate text-lg font-medium text-white">
              对话窗口
            </span>
          </div>

          <div className="relative grow overflow-y-auto px-2 py-4">
            <div className="space-y-4">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[412px] rounded-2xl p-4 text-sm ${
                      msg.role === 'user'
                        ? 'bg-white/[8%] text-white/70'
                        : 'bg-white/[4%] text-white/70'
                    }`}
                  >
                    {msg.image && (
                      <div className="mb-2">
                        <img 
                          src={msg.image} 
                          alt="参考图" 
                          className="max-w-full max-h-[200px] rounded-lg object-cover"
                        />
                      </div>
                    )}
                    {msg.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="max-w-[412px] rounded-2xl bg-white/[4%] p-4 text-sm text-white/70">
                    正在处理...
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-white/[12%] p-3">
            <form onSubmit={handleSubmit} className="space-y-2">
              <div className="flex items-center gap-x-2">
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                  className="h-10 rounded-xl border-none bg-white/[12%] px-2.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/20"
                >
                  <option value="chat">聊天模式</option>
                  <option value="image_generation">图片生成</option>
                </select>
              </div>
              {/* 参考图片预览 */}
              {referenceImagePreview && (
                <div className="relative inline-block mb-2">
                  <img 
                    src={referenceImagePreview} 
                    alt="参考图预览" 
                    className="max-w-[120px] max-h-[120px] rounded-xl object-cover"
                  />
                  <button
                    type="button"
                    onClick={handleRemoveImage}
                    className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center"
                  >
                    <svg 
                      className="w-4 h-4" 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                      strokeWidth={3}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}
              
              <div className="flex items-center gap-x-2">
                {/* 图片选择按钮 */}
                <label className="flex-shrink-0 cursor-pointer">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="hidden"
                    disabled={loading}
                  />
                  <div className="flex h-[100px] w-[100px] items-center justify-center rounded-xl bg-white/[12%] hover:bg-white/[20%] transition">
                    <svg 
                      className="h-6 w-6 text-white/70" 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path 
                        strokeLinecap="round" 
                        strokeLinejoin="round" 
                        strokeWidth={2} 
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" 
                      />
                    </svg>
                  </div>
                </label>
                
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="输入消息..."
                  className="h-20 grow resize-none rounded-xl border-none bg-white/[12%] p-3 text-sm text-white/70 focus:outline-none focus:ring-2 focus:ring-white/20"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !message.trim()}
                  className="rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 px-4 py-2 font-bold text-white transition hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.97]"
                >
                  发送
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
    </>
  )
}

export default Working

