import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getProject, getProjectMessages } from '../utils/storage'

function ProjectDetail() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedImages, setExpandedImages] = useState({})
  const [activeTab, setActiveTab] = useState('chat') // 'chat' 或 'images'
  const [blobUrls, setBlobUrls] = useState({}) // 存储生成的 Blob URL，用于清理

  useEffect(() => {
    loadProjectData()
    
    // 组件卸载时清理所有 Blob URL
    return () => {
      Object.values(blobUrls).forEach(url => {
        if (url && typeof url === 'string' && url.startsWith('blob:')) {
          URL.revokeObjectURL(url)
        }
      })
    }
  }, [projectId])

  const loadProjectData = async () => {
    try {
      setLoading(true)
      const projectData = await getProject(projectId)
      if (!projectData) {
        navigate('/projects')
        return
      }

      setProject(projectData)

      // 加载消息（getProjectMessages 会自动从 imageRef 读取原图数据）
      const messagesData = await getProjectMessages(projectId)
      
      // ⚠️ 关键修复：处理消息中的图片数据
      // 如果 imageData 是 Blob 对象，使用 URL.createObjectURL 生成预览地址
      // 如果是 Base64 字符串，直接使用
      const newBlobUrls = {}
      const messagesWithImages = messagesData.map((msg, index) => {
        let imageUrl = null
        
        if (msg.imageData) {
          if (msg.imageData instanceof Blob) {
            // Blob 对象：使用 URL.createObjectURL 生成预览地址
            imageUrl = URL.createObjectURL(msg.imageData)
            newBlobUrls[index] = imageUrl  // 保存 Blob URL 用于后续清理
            console.log(`📸 [ProjectDetail] 为 Blob 对象生成预览地址: ${imageUrl.substring(0, 50)}...`)
          } else if (typeof msg.imageData === 'string') {
            // Base64 字符串：直接使用
            imageUrl = msg.imageData
          }
        }
        
        return {
          ...msg,
          imageUrl: imageUrl
        }
      })
      
      // 清理旧的 Blob URL
      Object.values(blobUrls).forEach(url => {
        if (url && typeof url === 'string' && url.startsWith('blob:')) {
          URL.revokeObjectURL(url)
        }
      })
      
      // 保存新的 Blob URL
      setBlobUrls(newBlobUrls)

      setMessages(messagesWithImages)
    } catch (error) {
      console.error('加载项目数据失败:', error)
      alert('加载项目数据失败')
    } finally {
      setLoading(false)
    }
  }

  // 提取所有图片
  const allImages = messages
    .map((msg, index) => ({
      ...msg,
      index,
      imageUrl: msg.imageUrl
    }))
    .filter((msg) => msg.imageUrl)

  const handleImageClick = (index) => {
    setExpandedImages((prev) => ({
      ...prev,
      [index]: !prev[index]
    }))
  }

  const handleDownloadImage = async (imageData, index) => {
    try {
      // 如果是base64数据URL，直接下载
      if (imageData.startsWith('data:')) {
        const link = document.createElement('a')
        link.href = imageData
        link.download = `project-${projectId}-image-${index}.png`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
    } catch (error) {
      console.error('下载图片失败:', error)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="text-white/60">加载中...</div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="text-white/60">项目不存在</div>
      </div>
    )
  }

  return (
    <div className="flex h-full w-full">
      {/* 主内容区 */}
      <div className="flex-1 p-4">
        <div className="h-full rounded-3xl bg-[#121212] p-6">
          {/* 头部 */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <button
                onClick={() => navigate('/projects')}
                className="mb-2 flex items-center gap-2 text-white/60 hover:text-white transition"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                <span>返回会话列表</span>
              </button>
              <h2 className="text-2xl font-semibold text-white">{project.title}</h2>
              <p className="mt-1 text-sm text-white/60">
                会话开始于 {new Date(project.createdAt).toLocaleString('zh-CN')} · 
                最后更新 {new Date(project.updatedAt).toLocaleString('zh-CN')}
              </p>
            </div>
          </div>

          {/* 标签页 */}
          <div className="mb-4 flex gap-4 border-b border-white/10">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 text-sm font-medium transition ${
                activeTab === 'chat'
                  ? 'border-b-2 border-white text-white'
                  : 'text-white/60 hover:text-white/80'
              }`}
            >
              对话记录 ({messages.length})
            </button>
            <button
              onClick={() => setActiveTab('images')}
              className={`px-4 py-2 text-sm font-medium transition ${
                activeTab === 'images'
                  ? 'border-b-2 border-white text-white'
                  : 'text-white/60 hover:text-white/80'
              }`}
            >
              图片 ({allImages.length})
            </button>
          </div>

          {/* 内容区域 */}
          <div className="h-[calc(100%-180px)] overflow-y-auto">
            {activeTab === 'chat' ? (
              // 聊天记录视图
              messages.length === 0 ? (
                <div className="flex h-full items-center justify-center text-white/60">
                  <div className="text-center">
                    <svg
                      className="mx-auto h-16 w-16 mb-4 text-white/40"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                    <p>暂无聊天记录</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4 pr-4">
                  {messages.map((msg, index) => (
                    <div
                      key={index}
                      className={`flex ${
                        msg.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-[70%] rounded-2xl p-4 ${
                          msg.role === 'user'
                            ? 'bg-white/[12%] text-white'
                            : 'bg-white/[6%] text-white/90'
                        }`}
                      >
                        {/* 图片显示 */}
                        {msg.imageUrl && (
                          <div className="mb-3 group">
                            <div
                              className="relative cursor-pointer"
                              onClick={() => handleImageClick(index)}
                            >
                              <img
                                src={msg.imageUrl}
                                alt={`消息图片 ${index + 1}`}
                                className="max-w-full max-h-64 rounded-lg object-cover hover:opacity-90 transition"
                              />
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDownloadImage(msg.imageUrl, index)
                                }}
                                className="absolute top-2 right-2 p-2 rounded-full bg-black/60 hover:bg-black/80 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                                title="下载图片"
                              >
                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                              </button>
                            </div>
                          </div>
                        )}

                        {/* 文本内容 */}
                        {msg.content && (
                          <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                        )}

                        {/* 时间戳 */}
                        <div className="mt-2 text-xs text-white/40">
                          {new Date(msg.timestamp).toLocaleString('zh-CN')}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              // 图片视图
              allImages.length === 0 ? (
                <div className="flex h-full items-center justify-center text-white/60">
                  <div className="text-center">
                    <svg
                      className="mx-auto h-16 w-16 mb-4 text-white/40"
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
                    <p>暂无图片</p>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 pr-4">
                  {allImages.map((msg, index) => (
                    <div
                      key={index}
                      className="group relative aspect-square rounded-xl overflow-hidden bg-white/[4%] cursor-pointer hover:bg-white/[8%] transition"
                      onClick={() => handleImageClick(msg.index)}
                    >
                      <img
                        src={msg.imageUrl}
                        alt={`图片 ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                      {/* 悬浮显示信息 */}
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <div className="text-center text-white text-sm">
                          <p className="mb-2">
                            {new Date(msg.timestamp).toLocaleDateString('zh-CN')}
                          </p>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDownloadImage(msg.imageUrl, index)
                            }}
                            className="px-4 py-2 rounded-lg bg-white/20 hover:bg-white/30 transition"
                          >
                            下载
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        </div>
      </div>

      {/* 图片预览弹窗 */}
      {Object.keys(expandedImages).some((key) => expandedImages[key]) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
          onClick={() => setExpandedImages({})}
        >
          {Object.keys(expandedImages).map((key) => {
            if (!expandedImages[key]) return null
            const msg = messages[parseInt(key)]
            if (!msg?.imageUrl) return null
            return (
              <div key={key} className="relative max-h-[90vh] max-w-[90vw]">
                <img
                  src={msg.imageUrl}
                  alt="预览"
                  className="max-h-[90vh] max-w-[90vw] object-contain rounded-lg"
                  onClick={(e) => e.stopPropagation()}
                />
                <button
                  onClick={() => setExpandedImages({})}
                  className="absolute top-4 right-4 p-2 rounded-full bg-white/20 hover:bg-white/30 text-white"
                >
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default ProjectDetail
