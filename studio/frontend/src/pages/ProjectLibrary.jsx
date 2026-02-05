import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getAllProjects, deleteProject, createSampleProject, getLastMessage, clearAllHistory } from '../utils/storage'

function ProjectLibrary() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)
  const [clearing, setClearing] = useState(false)
  const [previewUrls, setPreviewUrls] = useState({}) // 保存 Blob 生成的 ObjectURL，避免列表空白

  useEffect(() => {
    loadProjects()
  }, [])

  // 当项目列表更新时，为 Blob 预览生成 ObjectURL，并清理旧的 URL
  useEffect(() => {
    const newUrls = {}
    projects.forEach((project) => {
      if (project.preview instanceof Blob) {
        const url = URL.createObjectURL(project.preview)
        newUrls[project.id] = url
      }
    })

    // 清理已废弃的 URL，更新映射
    setPreviewUrls((prev) => {
      Object.entries(prev).forEach(([id, url]) => {
        if (!newUrls[id]) {
          URL.revokeObjectURL(url)
        }
      })
      return newUrls
    })

    // 组件卸载或 projects 变化时清理本次生成的 URL
    return () => {
      Object.values(newUrls).forEach((url) => URL.revokeObjectURL(url))
    }
  }, [projects])

  const loadProjects = async () => {
    try {
      setLoading(true)
      let allProjects = await getAllProjects()
      
      console.log('📋 当前项目数量:', allProjects.length)
      
      // 如果没有项目，创建示例项目
      if (allProjects.length === 0) {
        console.log('📦 项目库为空，开始创建Demo示例项目...')
        try {
          const demoProject = await createSampleProject()
          if (demoProject) {
            console.log('✅ Demo示例项目创建成功:', demoProject.id, demoProject.title)
            // 重新加载项目列表
            allProjects = await getAllProjects()
            console.log('📋 重新加载后的项目数量:', allProjects.length)
          } else {
            console.log('ℹ️ Demo项目已存在，跳过创建')
          }
        } catch (error) {
          console.error('❌ 创建示例项目失败:', error)
          console.error('错误详情:', error.message, error.stack)
        }
      } else {
        console.log('✅ 项目库已有项目，无需创建Demo')
      }
      
      // 为每个项目获取最后一条消息预览（用于会话列表展示）
      // 如果获取最后一条消息失败，不影响项目列表的显示
      const projectsWithLastMessage = await Promise.all(
        allProjects.map(async (project) => {
          try {
            const lastMessage = await getLastMessage(project.id)
            return {
              ...project,
              lastMessage: lastMessage ? {
                content: lastMessage.content,
                role: lastMessage.role,
                timestamp: lastMessage.timestamp
              } : null
            }
          } catch (error) {
            console.warn(`⚠️ 获取项目 ${project.id} 的最后一条消息失败:`, error)
            // 即使获取最后一条消息失败，也返回项目（不包含 lastMessage）
            return { ...project, lastMessage: null }
          }
        })
      )
      
      console.log('📋 最终项目列表:', projectsWithLastMessage.length, '个项目')
      setProjects(projectsWithLastMessage)
    } catch (error) {
      console.error('❌ 加载项目列表失败:', error)
      console.error('错误详情:', error.message, error.stack)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (e, projectId) => {
    e.stopPropagation()
    if (!confirm(t('projectLibrary.deleteConfirm'))) {
      return
    }

    try {
      setDeletingId(projectId)
      await deleteProject(projectId)
      await loadProjects()
    } catch (error) {
      console.error('删除项目失败:', error)
      alert(t('projectLibrary.deleteError'))
    } finally {
      setDeletingId(null)
    }
  }

  const handleProjectClick = (projectId) => {
    navigate(`/projects/${projectId}`)
  }

  const handleClearAll = async () => {
    if (!confirm(t('projectLibrary.clearConfirm'))) {
      return
    }

    try {
      setClearing(true)
      await clearAllHistory()
      await loadProjects()
      alert(t('projectLibrary.clearSuccess'))
    } catch (error) {
      console.error('清空历史记录失败:', error)
      alert(t('projectLibrary.clearError'))
    } finally {
      setClearing(false)
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    
    return `${t('projectLibrary.updatedAt')} ${year}-${month}-${day} ${hours}:${minutes}`
  }

  if (loading) {
    return (
      <div className="container mx-auto mt-20 max-w-7xl px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-white/60">{t('projectLibrary.loading')}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto mt-20 max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="mb-2 text-4xl font-bold text-white">{t('projectLibrary.title')}</h1>
          <p className="text-white/60">{t('projectLibrary.subtitle')}</p>
        </div>
        {projects.length > 0 && (
          <button
            onClick={handleClearAll}
            disabled={clearing}
            className="px-4 py-2 rounded-xl bg-red-500/80 hover:bg-red-600 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {clearing ? (
              <>
                <svg className="animate-spin h-5 w-5 inline-block mr-2" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {t('projectLibrary.clearing')}
              </>
            ) : (
              <>
                <svg className="h-5 w-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                {t('projectLibrary.clearHistory')}
              </>
            )}
          </button>
        )}
      </div>

      {projects.length === 0 ? (
        <div className="rounded-3xl bg-white/[8%] p-12 text-center">
          <svg
            className="mx-auto h-16 w-16 text-white/40 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <p className="text-white/60 text-lg">{t('projectLibrary.noProjects')}</p>
          <p className="text-white/40 text-sm mt-2">{t('projectLibrary.noProjectsHint')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              onClick={() => handleProjectClick(project.id)}
              className="group relative rounded-3xl bg-white/[8%] overflow-hidden cursor-pointer hover:bg-white/[12%] transition-all duration-300 hover:scale-[1.02]"
            >
              {/* 预览图 */}
              <div className="aspect-video bg-white/[4%] relative overflow-hidden">
                {project.preview ? (
                  <img
                    src={previewUrls[project.id] || project.preview}
                    alt={project.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <svg
                      className="h-12 w-12 text-white/20"
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
                )}
                
                {/* 删除按钮 */}
                <button
                  onClick={(e) => handleDelete(e, project.id)}
                  disabled={deletingId === project.id}
                  className="absolute top-2 right-2 p-2 rounded-xl bg-black/60 hover:bg-red-500/80 text-white opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
                  title={t('projectLibrary.deleteProject')}
                >
                  {deletingId === project.id ? (
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  )}
                </button>
              </div>

              {/* 项目信息（会话信息） */}
              <div className="p-4">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="flex-1 text-lg font-semibold text-white truncate">
                    {project.title}
                  </h3>
                  <span className="text-xs text-white/40 whitespace-nowrap">{formatDate(project.updatedAt)}</span>
                </div>
                
                {/* 最后一条消息预览（类似聊天列表） */}
                {project.lastMessage && (
                  <p className="mb-2 line-clamp-2 text-sm text-white/60">
                    {project.lastMessage.role === 'user' ? `${t('projectLibrary.me')}: ` : `${t('projectLibrary.ai')}: `}
                    {project.lastMessage.content || t('projectLibrary.image')}
                  </p>
                )}
                
                <div className="flex items-center gap-3 text-xs text-white/40">
                  {project.messageCount > 0 && (
                    <span className="flex items-center gap-1">
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      {project.messageCount}
                    </span>
                  )}
                  {project.imageCount > 0 && (
                    <span className="flex items-center gap-1">
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      {project.imageCount}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ProjectLibrary

