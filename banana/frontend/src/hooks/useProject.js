import { useState, useEffect } from 'react'
import { createProject, saveMessage } from '../utils/storage'

/**
 * 管理当前项目的 Hook
 * 用于在工作区中管理项目状态和保存聊天记录
 */
export function useProject(projectId = null) {
  const [currentProjectId, setCurrentProjectId] = useState(projectId)
  const [isCreating, setIsCreating] = useState(false)

  // 如果传入 projectId，使用它
  useEffect(() => {
    if (projectId) {
      setCurrentProjectId(projectId)
    }
  }, [projectId])

  // 创建新项目
  const createNewProject = async (title = '新项目') => {
    setIsCreating(true)
    try {
      const project = await createProject(title)
      setCurrentProjectId(project.id)
      return project
    } catch (error) {
      console.error('创建项目失败:', error)
      throw error
    } finally {
      setIsCreating(false)
    }
  }

  // 保存消息到当前项目
  const saveMessageToProject = async (message) => {
    try {
      console.log('📝 saveMessageToProject 被调用:', {
        hasCurrentProjectId: !!currentProjectId,
        currentProjectId: currentProjectId,
        messageRole: message.role,
        messageContentLength: message.content?.length || 0,
        hasImageData: !!message.imageData
      })
      
      let targetProjectId = currentProjectId
      
      if (!targetProjectId) {
        // 如果没有当前项目，先创建一个
        console.log('📦 没有当前项目，创建新项目...')
        const project = await createNewProject(message.content?.substring(0, 30) || '新项目')
        targetProjectId = project.id
        console.log('✅ 新项目已创建:', targetProjectId)
      }
      
      console.log('💾 开始保存消息到项目:', targetProjectId)
      const result = await saveMessage(targetProjectId, message)
      console.log('✅ 消息已成功保存:', targetProjectId)
      return result
    } catch (error) {
      console.error('❌ saveMessageToProject 失败:', error)
      throw error
    }
  }

  // 清空当前项目（用于新建画布）
  const clearProject = () => {
    setCurrentProjectId(null)
  }

  return {
    currentProjectId,
    createNewProject,
    saveMessageToProject,
    clearProject,
    isCreating
  }
}

