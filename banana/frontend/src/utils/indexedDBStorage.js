/**
 * IndexedDB 存储方案
 * 
 * 使用 IndexedDB 存储会话历史数据，避免 localStorage 的 5MB 限制
 * 数据库名称: GuojieChatData
 * 版本: 1
 * 
 * ObjectStores:
 * - projects: 项目列表
 * - messages: 消息列表（按 projectId 索引）
 * - images: 图片数据（Blob 格式）
 */

const DB_NAME = 'GuojieChatData'
const DB_VERSION = 1
const STORE_PROJECTS = 'projects'
const STORE_MESSAGES = 'messages'
const STORE_IMAGES = 'images'

let db = null
let initPromise = null

/**
 * 初始化 IndexedDB 数据库
 */
function initDB() {
  if (initPromise) {
    return initPromise
  }

  initPromise = new Promise((resolve, reject) => {
    if (db) {
      resolve(db)
      return
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => {
      console.error('❌ IndexedDB 打开失败:', request.error)
      reject(new Error('数据库打开失败: ' + request.error))
    }

    request.onsuccess = () => {
      db = request.result
      console.log('✅ IndexedDB 数据库已打开:', DB_NAME)
      resolve(db)
    }

    request.onupgradeneeded = (event) => {
      const database = event.target.result

      // 创建 projects 存储
      if (!database.objectStoreNames.contains(STORE_PROJECTS)) {
        const projectStore = database.createObjectStore(STORE_PROJECTS, {
          keyPath: 'id',
          autoIncrement: false
        })
        projectStore.createIndex('updatedAt', 'updatedAt', { unique: false })
        projectStore.createIndex('createdAt', 'createdAt', { unique: false })
        console.log('✅ 创建 projects 存储')
      }

      // 创建 messages 存储
      if (!database.objectStoreNames.contains(STORE_MESSAGES)) {
        const messageStore = database.createObjectStore(STORE_MESSAGES, {
          keyPath: 'id',
          autoIncrement: false
        })
        messageStore.createIndex('projectId', 'projectId', { unique: false })
        messageStore.createIndex('timestamp', 'timestamp', { unique: false })
        console.log('✅ 创建 messages 存储')
      }

      // 创建 images 存储
      if (!database.objectStoreNames.contains(STORE_IMAGES)) {
        const imageStore = database.createObjectStore(STORE_IMAGES, {
          keyPath: 'id',
          autoIncrement: false
        })
        imageStore.createIndex('projectId', 'projectId', { unique: false })
        imageStore.createIndex('messageId', 'messageId', { unique: false })
        console.log('✅ 创建 images 存储')
      }
    }
  })

  return initPromise
}

/**
 * 获取数据库实例（确保已初始化）
 */
async function getDB() {
  if (!db) {
    await initDB()
  }
  return db
}

/**
 * 工具函数：执行事务
 */
async function executeTransaction(storeNames, mode, callback) {
  const database = await getDB()
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(storeNames, mode)
    transaction.onerror = () => {
      console.error('❌ 事务执行失败:', transaction.error)
      reject(transaction.error)
    }
    transaction.oncomplete = () => {
      resolve()
    }
    
    const result = callback(transaction)
    if (result instanceof Promise) {
      result.then(() => {
        // Promise 完成后，事务会自动提交
      }).catch(reject)
    }
  })
}

// ==================== 项目相关操作 ====================

/**
 * 获取所有项目
 */
export async function getAllProjects() {
  try {
    const database = await getDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_PROJECTS], 'readonly')
      const store = transaction.objectStore(STORE_PROJECTS)
      const index = store.index('updatedAt')
      const request = index.openCursor(null, 'prev') // 倒序排列

      const projects = []
      request.onsuccess = (event) => {
        const cursor = event.target.result
        if (cursor) {
          projects.push(cursor.value)
          cursor.continue()
        } else {
          console.log('📋 从 IndexedDB 读取项目列表，共', projects.length, '个项目')
          resolve(projects)
        }
      }
      request.onerror = () => {
        console.error('❌ 读取项目列表失败:', request.error)
        reject(request.error)
      }
    })
  } catch (e) {
    console.error('❌ 获取项目列表失败:', e)
    return []
  }
}

/**
 * 获取项目详情
 */
export async function getProject(projectId) {
  try {
    const database = await getDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_PROJECTS], 'readonly')
      const store = transaction.objectStore(STORE_PROJECTS)
      const request = store.get(projectId)

      request.onsuccess = () => {
        resolve(request.result || null)
      }
      request.onerror = () => {
        console.error('❌ 读取项目详情失败:', request.error)
        reject(request.error)
      }
    })
  } catch (e) {
    console.error('❌ 获取项目详情失败:', e)
    return null
  }
}

/**
 * 创建新项目
 */
export async function createProject(title = '新项目') {
  try {
    const project = {
      id: Date.now().toString(),
      title,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messageCount: 0,
      imageCount: 0,
      preview: null
    }

    const database = await getDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_PROJECTS], 'readwrite')
      const store = transaction.objectStore(STORE_PROJECTS)
      const request = store.add(project)

      request.onsuccess = () => {
        console.log('✅ 项目已创建:', project.id, project.title)
        resolve(project)
      }
      request.onerror = () => {
        console.error('❌ 创建项目失败:', request.error)
        reject(new Error('创建项目失败: ' + request.error))
      }
    })
  } catch (e) {
    console.error('❌ 创建项目失败:', e)
    throw new Error('创建项目失败: ' + e.message)
  }
}

/**
 * 更新项目信息
 */
export async function updateProject(projectId, updates) {
  try {
    const database = await getDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_PROJECTS], 'readwrite')
      const store = transaction.objectStore(STORE_PROJECTS)
      const getRequest = store.get(projectId)

      getRequest.onsuccess = () => {
        const project = getRequest.result
        if (!project) {
          reject(new Error('项目不存在'))
          return
        }

        const updatedProject = {
          ...project,
          ...updates,
          updatedAt: new Date().toISOString()
        }

        const putRequest = store.put(updatedProject)
        putRequest.onsuccess = () => {
          console.log('✅ 项目已更新:', projectId)
          resolve(updatedProject)
        }
        putRequest.onerror = () => {
          console.error('❌ 更新项目失败:', putRequest.error)
          reject(new Error('更新项目失败: ' + putRequest.error))
        }
      }
      getRequest.onerror = () => {
        console.error('❌ 读取项目失败:', getRequest.error)
        reject(new Error('读取项目失败: ' + getRequest.error))
      }
    })
  } catch (e) {
    console.error('❌ 更新项目失败:', e)
    throw new Error('更新项目失败: ' + e.message)
  }
}

/**
 * 删除项目
 */
export async function deleteProject(projectId) {
  try {
    const database = await getDB()
    
    // 删除项目及其相关消息和图片
    return new Promise((resolve, reject) => {
      const transaction = database.transaction(
        [STORE_PROJECTS, STORE_MESSAGES, STORE_IMAGES],
        'readwrite'
      )

      // 删除项目
      const projectStore = transaction.objectStore(STORE_PROJECTS)
      const deleteProjectRequest = projectStore.delete(projectId)

      // 删除项目的所有消息
      const messageStore = transaction.objectStore(STORE_MESSAGES)
      const messageIndex = messageStore.index('projectId')
      const messageCursor = messageIndex.openCursor(IDBKeyRange.only(projectId))

      messageCursor.onsuccess = (event) => {
        const cursor = event.target.result
        if (cursor) {
          cursor.delete()
          cursor.continue()
        }
      }

      // 删除项目的所有图片
      const imageStore = transaction.objectStore(STORE_IMAGES)
      const imageIndex = imageStore.index('projectId')
      const imageCursor = imageIndex.openCursor(IDBKeyRange.only(projectId))

      imageCursor.onsuccess = (event) => {
        const cursor = event.target.result
        if (cursor) {
          cursor.delete()
          cursor.continue()
        }
      }

      transaction.oncomplete = () => {
        console.log('✅ 项目已删除:', projectId)
        resolve()
      }
      transaction.onerror = () => {
        console.error('❌ 删除项目失败:', transaction.error)
        reject(new Error('删除项目失败: ' + transaction.error))
      }
    })
  } catch (e) {
    console.error('❌ 删除项目失败:', e)
    throw new Error('删除项目失败: ' + e.message)
  }
}

/**
 * 清空所有历史记录
 */
export async function clearAllHistory() {
  try {
    const database = await getDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction(
        [STORE_PROJECTS, STORE_MESSAGES, STORE_IMAGES],
        'readwrite'
      )

      // 清空所有存储
      transaction.objectStore(STORE_PROJECTS).clear()
      transaction.objectStore(STORE_MESSAGES).clear()
      transaction.objectStore(STORE_IMAGES).clear()

      transaction.oncomplete = () => {
        console.log('✅ 所有历史记录已清空')
        resolve()
      }
      transaction.onerror = () => {
        console.error('❌ 清空历史记录失败:', transaction.error)
        reject(new Error('清空历史记录失败: ' + transaction.error))
      }
    })
  } catch (e) {
    console.error('❌ 清空历史记录失败:', e)
    throw new Error('清空历史记录失败: ' + e.message)
  }
}

// ==================== 消息相关操作 ====================

/**
 * 保存消息到项目
 */
export async function saveMessage(projectId, message) {
  try {
    const messageId = Date.now()
    
    // 判断是否有图片数据
    const hasImage = !!message.imageData
    let imageRef = null
    
    // ⚠️ 重要：如果图片数据很大（超过 100KB），存储到独立的 images 存储中
    // ⚠️ 支持 Blob 对象（process-json3 返回二进制图片流）
    if (hasImage && message.imageData) {
      // 检查是否是 Blob 对象（process-json3 返回）
      if (message.imageData instanceof Blob) {
        // Blob 对象：直接存储到 images 存储中
        try {
          const imageId = `img_${projectId}_${messageId}`
          const database = await getDB()
          await new Promise((resolve, reject) => {
            const transaction = database.transaction([STORE_IMAGES], 'readwrite')
            const store = transaction.objectStore(STORE_IMAGES)
            const imageData = {
              id: imageId,
              projectId,
              messageId,
              image: message.imageData,  // 直接使用 Blob 对象
              mimeType: message.imageData.type || 'image/jpeg',
              timestamp: new Date().toISOString()
            }
            const request = store.add(imageData)
            request.onsuccess = () => resolve()
            request.onerror = () => reject(request.error)
          })
          
          imageRef = imageId
          console.log('📸 Blob 图片已存储到 IndexedDB:', imageId, `大小: ${(message.imageData.size / 1024).toFixed(2)} KB`)
        } catch (imgError) {
          console.warn('⚠️ Blob 图片存储失败，跳过图片:', imgError.message)
        }
      } else {
        // 字符串格式（Data URL 或 Base64）
        const isBase64Image = typeof message.imageData === 'string' && 
                              (message.imageData.startsWith('data:image') || 
                               message.imageData.startsWith('blob:') ||
                               message.imageData.length > 100000)
        
        if (isBase64Image && message.imageData.length > 100000 && message.imageData.startsWith('data:')) {
          // 大图片（Data URL）：存储到 images 存储中
          try {
            // 将 base64 转换为 Blob
            const base64Data = message.imageData.split(',')[1] || message.imageData
            const byteCharacters = atob(base64Data)
            const byteNumbers = new Array(byteCharacters.length)
            for (let i = 0; i < byteCharacters.length; i++) {
              byteNumbers[i] = byteCharacters.charCodeAt(i)
            }
            const byteArray = new Uint8Array(byteNumbers)
            const mimeType = message.imageData.match(/data:([^;]+)/)?.[1] || 'image/png'
            const blob = new Blob([byteArray], { type: mimeType })
            
            // 保存到 images 存储
            const imageId = `img_${projectId}_${messageId}`
            const database = await getDB()
            await new Promise((resolve, reject) => {
              const transaction = database.transaction([STORE_IMAGES], 'readwrite')
              const store = transaction.objectStore(STORE_IMAGES)
              const imageData = {
                id: imageId,
                projectId,
                messageId,
                image: blob,
                mimeType,
                timestamp: new Date().toISOString()
              }
              const request = store.add(imageData)
              request.onsuccess = () => resolve()
              request.onerror = () => reject(request.error)
            })
            
            imageRef = imageId
            console.log('📸 大图片已存储到 IndexedDB:', imageId)
          } catch (imgError) {
            console.warn('⚠️ 图片存储失败，跳过图片:', imgError.message)
          }
        } else if (isBase64Image && message.imageData.startsWith('data:')) {
          // 小图片（Data URL）：直接存储在消息中
          imageRef = message.imageData
          console.log('📸 小图片直接存储在消息中')
        } else if (message.imageData.startsWith('blob:')) {
          // Blob URL：这是临时 URL，实际数据应该在 IndexedDB 中
          // 如果 Blob URL 存在，说明 Blob 已经在 IndexedDB 中，这里只保存引用
          imageRef = message.imageData
          console.log('📸 Blob URL 引用（实际数据在 IndexedDB 中）')
        }
      }
    }
    
    // 消息数据
    const messageData = {
      id: messageId,
      projectId,
      role: message.role,
      content: message.content,
      hasImage: hasImage,
      imageRef: imageRef,
      timestamp: new Date().toISOString()
    }
    
    // 保存消息
    const database = await getDB()
    await new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_MESSAGES], 'readwrite')
      const store = transaction.objectStore(STORE_MESSAGES)
      const request = store.add(messageData)
      
      request.onsuccess = () => {
        console.log('✅ 消息已保存:', projectId, '图片引用:', imageRef)
        resolve(messageId)
      }
      request.onerror = () => {
        console.error('❌ 保存消息失败:', request.error)
        reject(new Error('保存消息失败: ' + request.error))
      }
    })
    
    // 更新项目消息计数
    const messages = await getProjectMessages(projectId)
    await updateProject(projectId, { messageCount: messages.length })
    
    // 如果是第一张图片，设置为预览图
    if (hasImage) {
      const project = await getProject(projectId)
      if (!project.preview) {
        try {
          let imageDataForPreview = null
          
          // 如果图片引用是 img_ 开头（大图片存储在 images 存储中），需要先读取
          if (imageRef && imageRef.startsWith('img_')) {
            const database = await getDB()
            const imageData = await new Promise((resolve, reject) => {
              const transaction = database.transaction([STORE_IMAGES], 'readonly')
              const store = transaction.objectStore(STORE_IMAGES)
              const request = store.get(imageRef)
              
              request.onsuccess = () => {
                resolve(request.result)
              }
              request.onerror = () => {
                reject(request.error)
              }
            })
            
            if (imageData && imageData.image) {
              // 直接使用 Blob 对象，不转换为 Base64
              if (imageData.image instanceof Blob) {
                console.log(`📸 [updateProject] 读取到 Blob 对象，大小: ${(imageData.image.size / 1024).toFixed(2)} KB`)
                // 直接使用 Blob，前端会在需要时创建 URL
                imageDataForPreview = imageData.image
              } else if (typeof imageData.image === 'string') {
                // 字符串类型（Base64 或 URL）
                imageDataForPreview = imageData.image
              }
            }
          } else if (message.imageData && typeof message.imageData === 'string' && 
                     (message.imageData.startsWith('data:') || message.imageData.length > 100)) {
            // 小图片直接存储在消息中（base64 字符串）
            imageDataForPreview = message.imageData
          }
          
          // 生成预览图：如果是 Blob 直接存为预览，字符串则走缩略图
          if (imageDataForPreview) {
            if (imageDataForPreview instanceof Blob) {
              console.log('🖼️ [saveMessage] 直接使用 Blob 作为预览，大小:', (imageDataForPreview.size / 1024).toFixed(2), 'KB')
              await updateProject(projectId, { preview: imageDataForPreview })
            } else {
              console.log('🖼️ [saveMessage] 准备生成预览图，数据类型:', typeof imageDataForPreview)
              try {
                const thumbnail = await createThumbnail(imageDataForPreview, 800)
                await updateProject(projectId, { preview: thumbnail })
                console.log('✅ 预览图已生成并保存（Base64）')
              } catch (thumbnailError) {
                console.error('❌ 生成预览图失败:', thumbnailError)
                console.log('📌 使用原图数据作为预览')
                await updateProject(projectId, { preview: imageDataForPreview })
              }
            }
          } else {
            console.warn('⚠️ 无法获取图片数据用于生成预览图')
          }
        } catch (e) {
          console.warn('⚠️ 生成预览图失败:', e)
        }
      }
    }
    
    return messageId
  } catch (e) {
    console.error('❌ 保存消息失败:', e)
    throw new Error('保存消息失败: ' + e.message)
  }
}

/**
 * 获取项目的所有消息
 */
export async function getProjectMessages(projectId) {
  try {
    const database = await getDB()
    
    // 第一步：读取所有消息
    const messages = await new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_MESSAGES], 'readonly')
      const messageStore = transaction.objectStore(STORE_MESSAGES)
      const index = messageStore.index('projectId')
      const request = index.openCursor(IDBKeyRange.only(projectId))

      const msgs = []
      request.onsuccess = (event) => {
        const cursor = event.target.result
        if (cursor) {
          msgs.push(cursor.value)
          cursor.continue()
        } else {
          resolve(msgs)
        }
      }
      request.onerror = () => {
        console.error('❌ 读取消息失败:', request.error)
        reject(request.error)
      }
    })
    
    // 第二步：为每条消息加载图片数据（如果需要）
    const messagesWithImages = await Promise.all(messages.map(async (msg) => {
      if (msg.imageRef && msg.hasImage) {
        // 如果图片引用是 img_ 开头，从 images 存储中读取
        if (msg.imageRef.startsWith('img_')) {
          try {
            const imageData = await new Promise((resolve, reject) => {
              const transaction = database.transaction([STORE_IMAGES], 'readonly')
              const store = transaction.objectStore(STORE_IMAGES)
              const request = store.get(msg.imageRef)
              
              request.onsuccess = () => {
                resolve(request.result)
              }
              request.onerror = () => {
                reject(request.error)
              }
            })
            
            if (imageData && imageData.image) {
              // 直接返回 Blob 对象，让前端在需要时创建 URL
              if (imageData.image instanceof Blob) {
                console.log(`📸 [getProjectMessages] 读取到 Blob 对象，大小: ${(imageData.image.size / 1024).toFixed(2)} KB`)
                return {
                  ...msg,
                  imageData: imageData.image,  // 返回原始 Blob 对象
                  _isBlobObject: true
                }
              } else if (typeof imageData.image === 'string') {
                // 字符串类型（Base64 或 URL）
                return {
                  ...msg,
                  imageData: imageData.image
                }
              }
            } else {
              console.warn(`⚠️ [getProjectMessages] imageData 不存在或无 image 属性`)
              return msg
            }
          } catch (e) {
            console.warn(`⚠️ 读取图片 ${msg.imageRef} 失败:`, e)
          }
        } else if (typeof msg.imageRef === 'string' && msg.imageRef.startsWith('data:')) {
          // 小图片直接存储在消息中
          return {
            ...msg,
            imageData: msg.imageRef
          }
        }
      }
      return msg
    }))
    
    // 按时间戳排序
    messagesWithImages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    console.log(`📋 从 IndexedDB 读取项目 ${projectId} 的消息，共 ${messagesWithImages.length} 条`)
    return messagesWithImages
  } catch (e) {
    console.error('❌ 读取消息失败:', e)
    return []
  }
}

/**
 * 获取最后一条消息
 */
export async function getLastMessage(projectId) {
  try {
    const messages = await getProjectMessages(projectId)
    return messages.length > 0 ? messages[messages.length - 1] : null
  } catch (e) {
    console.error('❌ 读取最后一条消息失败:', e)
    return null
  }
}

/**
 * 获取消息数量
 */
export async function getMessageCount(projectId) {
  try {
    const messages = await getProjectMessages(projectId)
    return messages.length
  } catch (e) {
    return 0
  }
}

// ==================== 图片相关操作 ====================

/**
 * 创建缩略图
 */
async function createThumbnail(imageInput, maxSize = 800) {
  return new Promise((resolve, reject) => {
    try {
      // Blob 直接返回，不做额外处理，预览由外部控制
      if (imageInput instanceof Blob) {
        console.log('🖼️ [createThumbnail] 输入为 Blob，直接返回原始 Blob')
        resolve(imageInput)
        return
      }

      const img = new Image()
      let objectUrl = null
      
      // 设置超时，避免永久挂起
      const timeout = setTimeout(() => {
        if (objectUrl) URL.revokeObjectURL(objectUrl)
        console.error('❌ [createThumbnail] 图片加载超时')
        reject(new Error('图片加载超时'))
      }, 10000)
      
      img.onload = () => {
        clearTimeout(timeout)
        
        try {
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')
          
          // 如果图片尺寸已经小于等于最大尺寸，直接返回原图
          if (img.width <= maxSize && img.height <= maxSize) {
            console.log(`✅ [createThumbnail] 图片尺寸合适，无需缩略，尺寸: ${img.width}x${img.height}`)
            if (objectUrl) URL.revokeObjectURL(objectUrl)
            resolve(imageInput)  // 返回原始输入（Blob 或 Base64）
            return
          }
          
          // 计算缩略图尺寸
          let width = img.width
          let height = img.height
          if (width > height) {
            if (width > maxSize) {
              height = Math.round(height * maxSize / width)
              width = maxSize
            }
          } else {
            if (height > maxSize) {
              width = Math.round(width * maxSize / height)
              height = maxSize
            }
          }
          
          console.log(`🔄 [createThumbnail] 生成缩略图，原尺寸: ${img.width}x${img.height}，新尺寸: ${width}x${height}`)
          
          canvas.width = width
          canvas.height = height
          
          ctx.imageSmoothingEnabled = true
          ctx.imageSmoothingQuality = 'high'
          ctx.drawImage(img, 0, 0, width, height)
          
          // 如果原始输入是 Blob，返回 Blob；否则返回 Base64
          if (imageInput instanceof Blob) {
            canvas.toBlob((blob) => {
              if (objectUrl) URL.revokeObjectURL(objectUrl)
              if (blob) {
                console.log(`✅ [createThumbnail] 缩略图生成成功（Blob），大小: ${(blob.size / 1024).toFixed(2)} KB`)
                resolve(blob)
              } else {
                reject(new Error('生成缩略图 Blob 失败'))
              }
            }, imageInput.type || 'image/jpeg', 0.8)
          } else {
            const hasAlpha = typeof imageInput === 'string' && (imageInput.includes('image/png') || imageInput.includes('image/webp'))
            const thumbnail = hasAlpha 
              ? canvas.toDataURL('image/png', 0.6)
              : canvas.toDataURL('image/jpeg', 0.6)
            if (objectUrl) URL.revokeObjectURL(objectUrl)
            console.log(`✅ [createThumbnail] 缩略图生成成功（Base64），大小: ${(thumbnail.length / 1024).toFixed(2)} KB`)
            resolve(thumbnail)
          }
        } catch (canvasError) {
          clearTimeout(timeout)
          if (objectUrl) URL.revokeObjectURL(objectUrl)
          console.error('❌ [createThumbnail] Canvas 处理失败:', canvasError)
          reject(canvasError)
        }
      }
      
      img.onerror = (e) => {
        clearTimeout(timeout)
        if (objectUrl) URL.revokeObjectURL(objectUrl)
        console.error('❌ [createThumbnail] 图片加载失败')
        if (imageInput instanceof Blob) {
          console.error('   Blob 类型:', imageInput.type, '大小:', (imageInput.size / 1024).toFixed(2), 'KB')
        } else {
          console.error('   Base64 前缀:', imageInput?.substring(0, 100))
        }
        console.error('   错误事件:', e)
        reject(new Error('图片加载失败'))
      }
      
      // 加载图片：如果是 Blob，创建 Object URL；否则直接使用
      if (imageInput instanceof Blob) {
        objectUrl = URL.createObjectURL(imageInput)
        img.src = objectUrl
        console.log('🖼️ [createThumbnail] 使用 Blob 创建预览，大小:', (imageInput.size / 1024).toFixed(2), 'KB')
      } else {
        img.src = imageInput
        console.log('🖼️ [createThumbnail] 使用 Base64 创建预览')
      }
    } catch (e) {
      console.error('❌ [createThumbnail] 异常:', e)
      reject(e)
    }
  })
}

/**
 * 保存图片
 */
export async function saveImage(projectId, messageId, imageBlob, mimeType = 'image/png') {
  try {
    const imageId = `img_${projectId}_${messageId || Date.now()}`
    const database = await getDB()
    
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_IMAGES], 'readwrite')
      const store = transaction.objectStore(STORE_IMAGES)
      const imageData = {
        id: imageId,
        projectId,
        messageId,
        image: imageBlob,
        mimeType,
        timestamp: new Date().toISOString()
      }
      const request = store.add(imageData)
      
      request.onsuccess = () => {
        // 更新项目图片计数
        getProject(projectId).then(project => {
          if (project) {
            updateProject(projectId, { imageCount: (project.imageCount || 0) + 1 })
          }
        })
        resolve(imageId)
      }
      request.onerror = () => {
        console.error('❌ 保存图片失败:', request.error)
        reject(new Error('保存图片失败: ' + request.error))
      }
    })
  } catch (e) {
    console.error('❌ 保存图片失败:', e)
    throw new Error('保存图片失败: ' + e.message)
  }
}

/**
 * 获取项目图片
 */
export async function getProjectImages(projectId) {
  try {
    const database = await getDB()
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_IMAGES], 'readonly')
      const store = transaction.objectStore(STORE_IMAGES)
      const index = store.index('projectId')
      const request = index.openCursor(IDBKeyRange.only(projectId))

      const images = []
      request.onsuccess = (event) => {
        const cursor = event.target.result
        if (cursor) {
          const imageData = cursor.value
          // 将 Blob 转换为 base64
          const reader = new FileReader()
          reader.onloadend = () => {
            images.push({
              id: imageData.id,
              projectId: imageData.projectId,
              messageId: imageData.messageId,
              imageData: reader.result,
              timestamp: imageData.timestamp
            })
            cursor.continue()
          }
          reader.readAsDataURL(imageData.image)
        } else {
          resolve(images)
        }
      }
      request.onerror = () => {
        console.error('❌ 读取图片失败:', request.error)
        reject(request.error)
      }
    })
  } catch (e) {
    console.error('❌ 读取图片失败:', e)
    return []
  }
}

/**
 * 获取图片数量
 */
export async function getImageCount(projectId) {
  try {
    const images = await getProjectImages(projectId)
    return images.length
  } catch (e) {
    return 0
  }
}

// ==================== 工具函数 ====================

/**
 * base64 转 Blob
 */
export function base64ToBlob(base64DataUrl) {
  const [header, base64] = base64DataUrl.split(',')
  const mimeMatch = header.match(/data:([^;]+)/)
  const mimeType = mimeMatch ? mimeMatch[1] : 'image/png'

  const byteCharacters = atob(base64)
  const byteNumbers = new Array(byteCharacters.length)
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i)
  }
  const byteArray = new Uint8Array(byteNumbers)
  return new Blob([byteArray], { type: mimeType })
}

/**
 * Blob 转 base64
 */
export function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    if (!blob || !(blob instanceof Blob)) {
      console.error('❌ [blobToBase64] 输入不是有效的 Blob 对象:', blob)
      reject(new Error('输入不是有效的 Blob 对象'))
      return
    }
    
    const reader = new FileReader()
    
    reader.onloadend = () => {
      const result = reader.result
      if (!result || typeof result !== 'string') {
        console.error('❌ [blobToBase64] FileReader 返回无效结果')
        reject(new Error('FileReader 返回无效结果'))
        return
      }
      
      console.log(`✅ [blobToBase64] 转换成功，大小: ${(result.length / 1024).toFixed(2)} KB`)
      resolve(result)
    }
    
    reader.onerror = (e) => {
      console.error('❌ [blobToBase64] FileReader 错误:', e)
      reject(reader.error || new Error('FileReader 读取失败'))
    }
    
    try {
      reader.readAsDataURL(blob)
    } catch (e) {
      console.error('❌ [blobToBase64] 调用 readAsDataURL 失败:', e)
      reject(e)
    }
  })
}

/**
 * 创建示例项目（兼容性函数）
 * 
 * 注意：此函数暂时返回 null，避免重复创建示例项目
 * 如果需要创建示例项目，可以在此实现具体逻辑
 */
export async function createSampleProject() {
  // 暂时返回 null，避免重复创建
  return null
}

// ==================== Blob 图片存储（新架构）====================

/**
 * 保存图片 Blob 到 IndexedDB
 * @param {Blob} blob - 图片 Blob 对象
 * @param {Object} metadata - 元数据
 * @returns {Promise<string>} imageId
 */
export async function saveImageBlob(blob, metadata = {}) {
  try {
    if (!blob || !(blob instanceof Blob)) {
      throw new Error('输入不是有效的 Blob 对象')
    }

    const database = await getDB()
    const imageId = `img_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_IMAGES], 'readwrite')
      const store = transaction.objectStore(STORE_IMAGES)
      
      const imageRecord = {
        id: imageId,
        blob: blob,  // 直接存储 Blob 对象
        format: metadata.format || 'jpeg',
        width: metadata.width || 0,
        height: metadata.height || 0,
        modelVersion: metadata.modelVersion || '3_pro',
        timestamp: Date.now(),
        projectId: metadata.projectId || null,
        messageId: metadata.messageId || null,
        mimeType: metadata.mimeType || blob.type || 'image/jpeg'
      }
      
      const request = store.add(imageRecord)
      
      request.onsuccess = () => {
        console.log(`✅ [saveImageBlob] 图片已存储到 IndexedDB: ${imageId}`)
        console.log(`   大小: ${(blob.size / 1024).toFixed(2)} KB`)
        console.log(`   格式: ${imageRecord.format}`)
        console.log(`   尺寸: ${imageRecord.width}x${imageRecord.height}`)
        resolve(imageId)
      }
      
      request.onerror = () => {
        console.error('❌ [saveImageBlob] 存储失败:', request.error)
        reject(new Error('存储图片 Blob 失败: ' + request.error))
      }
    })
  } catch (e) {
    console.error('❌ [saveImageBlob] 异常:', e)
    throw new Error('存储图片 Blob 失败: ' + e.message)
  }
}

/**
 * 从 IndexedDB 读取图片 Blob
 * @param {string} imageId
 * @returns {Promise<Blob>}
 */
export async function getImageBlob(imageId) {
  try {
    if (!imageId) {
      throw new Error('imageId 不能为空')
    }

    const database = await getDB()
    
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_IMAGES], 'readonly')
      const store = transaction.objectStore(STORE_IMAGES)
      const request = store.get(imageId)
      
      request.onsuccess = () => {
        const record = request.result
        if (record && record.blob) {
          console.log(`✅ [getImageBlob] 读取成功: ${imageId}`)
          console.log(`   大小: ${(record.blob.size / 1024).toFixed(2)} KB`)
          resolve(record.blob)
        } else {
          console.warn(`⚠️ [getImageBlob] 图片不存在: ${imageId}`)
          reject(new Error('Image not found'))
        }
      }
      
      request.onerror = () => {
        console.error('❌ [getImageBlob] 读取失败:', request.error)
        reject(new Error('读取图片 Blob 失败: ' + request.error))
      }
    })
  } catch (e) {
    console.error('❌ [getImageBlob] 异常:', e)
    throw new Error('读取图片 Blob 失败: ' + e.message)
  }
}

/**
 * 获取图片元数据（不读取 Blob）
 * @param {string} imageId
 * @returns {Promise<Object>}
 */
export async function getImageMetadata(imageId) {
  try {
    if (!imageId) {
      throw new Error('imageId 不能为空')
    }

    const database = await getDB()
    
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_IMAGES], 'readonly')
      const store = transaction.objectStore(STORE_IMAGES)
      const request = store.get(imageId)
      
      request.onsuccess = () => {
        const record = request.result
        if (record) {
          const { blob, ...metadata } = record
          resolve(metadata)
        } else {
          reject(new Error('Image not found'))
        }
      }
      
      request.onerror = () => {
        reject(new Error('读取图片元数据失败: ' + request.error))
      }
    })
  } catch (e) {
    console.error('❌ [getImageMetadata] 异常:', e)
    throw new Error('读取图片元数据失败: ' + e.message)
  }
}

/**
 * 删除图片 Blob
 * @param {string} imageId
 * @returns {Promise<void>}
 */
export async function deleteImageBlob(imageId) {
  try {
    if (!imageId) {
      throw new Error('imageId 不能为空')
    }

    const database = await getDB()
    
    return new Promise((resolve, reject) => {
      const transaction = database.transaction([STORE_IMAGES], 'readwrite')
      const store = transaction.objectStore(STORE_IMAGES)
      const request = store.delete(imageId)
      
      request.onsuccess = () => {
        console.log(`✅ [deleteImageBlob] 图片已删除: ${imageId}`)
        resolve()
      }
      
      request.onerror = () => {
        console.error('❌ [deleteImageBlob] 删除失败:', request.error)
        reject(new Error('删除图片 Blob 失败: ' + request.error))
      }
    })
  } catch (e) {
    console.error('❌ [deleteImageBlob] 异常:', e)
    throw new Error('删除图片 Blob 失败: ' + e.message)
  }
}
