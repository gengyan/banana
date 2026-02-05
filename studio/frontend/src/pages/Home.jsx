import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { chatAPI } from '../api'
import { restoreOldPhoto } from '../api/sd'
import { useProject } from '../hooks/useProject'
import { saveChatHistory, saveChatHistoryWithError } from '../utils/chatHistorySaver'
import logger from '../utils/logger'
import ImageModal from '../components/ImageModal'
import InspirationGallery from '../components/InspirationGallery'
import MainForm from '../components/MainForm'
import OldPhotoRestore from '../components/OldPhotoRestore'

const MAX_REFERENCE_IMAGES = 14
const DEFAULT_TEMPERATURE = 0.4

const Home = () => {
  const { t } = useTranslation()
  const { currentProjectId, createNewProject } = useProject()

  const [message, setMessage] = useState('')
  const [response, setResponse] = useState('')
  const [mode, setMode] = useState('banana')
  const [aspectRatio, setAspectRatio] = useState('auto')
  const [resolution, setResolution] = useState('1K')
  const [temperature, setTemperature] = useState(DEFAULT_TEMPERATURE)
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState([])
  const [referenceImages, setReferenceImages] = useState([])

  const [showImageModal, setShowImageModal] = useState(false)
  const [imageData, setImageData] = useState(null)
  const [imageBlobUrl, setImageBlobUrl] = useState(null)
  const [imageFormat, setImageFormat] = useState('jpeg')

  const imageBlobUrlRef = useRef(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isRequesting, setIsRequesting] = useState(false)
  const requestIdRef = useRef(null)

  const [oldPhotoFile, setOldPhotoFile] = useState(null)
  const [oldPhotoPreview, setOldPhotoPreview] = useState(null)
  const [oldPhotoPrompt, setOldPhotoPrompt] = useState('high quality, sharp focus, clean skin')
  const [oldPhotoLoading, setOldPhotoLoading] = useState(false)
  const [restoredImage, setRestoredImage] = useState(null)

  // 当切换到banana模式时，自动重置分辨率为1K（banana模式只支持1K）
  useEffect(() => {
    if (mode === 'banana' && resolution !== '1K') {
      setResolution('1K')
    }
  }, [mode, resolution])

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const res = await fetch('/demo.json', { cache: 'no-cache' })
        if (res.ok) {
          const data = await res.json()
          const normalized = Array.isArray(data)
            ? data.map((item) => ({
                ...item,
                image: item.image || item.image_result || item.image_name
              }))
            : []
          setTemplates(normalized)
        }
      } catch (err) {
        logger.warn('加载模板列表失败', err)
      }
    }
    loadTemplates()
  }, [])

  const handleTemplateClick = async (template) => {
    setMessage(template?.introduction || '')

    if (!template?.image_name) {
      setReferenceImages([])
      return
    }

    try {
      const response = await fetch(`/images/${template.image_name}`)
      if (!response.ok) throw new Error('图片不存在')

      const blob = await response.blob()
      const file = new File([blob], template.image_name, { type: blob.type || 'image/jpeg' })

      const reader = new FileReader()
      reader.onloadend = () => {
        setReferenceImages([{ file, preview: reader.result }])
      }
      reader.readAsDataURL(file)
    } catch (error) {
      logger.warn('加载模板参考图失败', error)
      setReferenceImages([])
    }
  }

  const handleImageSelect = async (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    const items = await Promise.all(
      files.map(
        (file) =>
          new Promise((resolve) => {
            const reader = new FileReader()
            reader.onload = () => resolve({ file, preview: reader.result })
            reader.readAsDataURL(file)
          })
      )
    )

    // 追加到已有图片列表，而不是覆盖，并限制在最大数量内
    setReferenceImages((prev) => [...prev, ...items].slice(0, MAX_REFERENCE_IMAGES))
  }

  const handleRemoveImage = (index) => {
    setReferenceImages((prev) => prev.filter((_, i) => i !== index))
  }

  const handleCloseModal = () => {
    setShowImageModal(false)
    if (imageBlobUrlRef.current) {
      URL.revokeObjectURL(imageBlobUrlRef.current)
      imageBlobUrlRef.current = null
    }
  }

  const handleDownloadImage = () => {
    try {
      let urlForDownload = imageBlobUrlRef.current || imageBlobUrl
      
      // 生成文件名：DSC_YYMMDD###.ext 格式
      const generateFileName = (blobType = 'image/jpeg') => {
        const now = new Date()
        const year = String(now.getFullYear()).slice(-2)  // 最后两位年份 (26 for 2026)
        const month = String(now.getMonth() + 1).padStart(2, '0')
        const day = String(now.getDate()).padStart(2, '0')
        const sequence = String(Math.floor(Math.random() * 1000)).padStart(3, '0')  // 3位随机序号
        
        // 根据 MIME 类型设置扩展名
        let ext = 'jpg'
        if (blobType === 'image/png' || imageFormat === 'png') {
          ext = 'png'
        } else if (blobType.includes('jpeg') || blobType.includes('jpg') || imageFormat === 'jpeg') {
          ext = 'jpg'
        }
        
        return `DSC_${year}${month}${day}${sequence}.${ext}`
      }

      if (!urlForDownload && imageData instanceof Blob) {
        urlForDownload = URL.createObjectURL(imageData)
        // 根据 Blob 的 MIME 类型生成文件名
      } else if (!urlForDownload && typeof imageData === 'string' && imageData.startsWith('data:image')) {
        const mimeMatch = imageData.match(/data:(.*?);base64/)
        const mimeType = mimeMatch?.[1] || `image/${imageFormat || 'jpeg'}`
        
        const byteString = atob(imageData.split(',')[1])
        const ab = new ArrayBuffer(byteString.length)
        const ia = new Uint8Array(ab)
        for (let i = 0; i < byteString.length; i += 1) {
          ia[i] = byteString.charCodeAt(i)
        }
        const blob = new Blob([ab], { type: mimeType })
        urlForDownload = URL.createObjectURL(blob)
      }

      if (!urlForDownload) {
        alert('没有可下载的图片')
        return
      }

      // 根据实际数据类型生成正确的文件名
      let downloadFileName = 'DSC_image.jpg'
      if (imageData instanceof Blob) {
        downloadFileName = generateFileName(imageData.type)
      } else if (typeof imageData === 'string' && imageData.startsWith('data:image')) {
        const mimeMatch = imageData.match(/data:(.*?);base64/)
        downloadFileName = generateFileName(mimeMatch?.[1] || 'image/jpeg')
      } else {
        // 使用 imageFormat 状态（来自后端）
        downloadFileName = generateFileName(imageFormat ? `image/${imageFormat}` : 'image/jpeg')
      }

      const link = document.createElement('a')
      link.href = urlForDownload
      link.download = downloadFileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      if (urlForDownload && urlForDownload !== imageBlobUrlRef.current) {
        setTimeout(() => URL.revokeObjectURL(urlForDownload), 100)
      }
    } catch (error) {
      logger.error('下载图片失败', error)
      alert('下载失败，请重试')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!message.trim() || loading || isRequesting) return

    const currentRequestId = Date.now()
    requestIdRef.current = currentRequestId
    setIsRequesting(true)
    setLoading(true)
    setResponse('')

    try {
      const finalAspectRatio = aspectRatio === 'auto' ? null : aspectRatio
      
      // ⚠️ 调试：检查 referenceImages 的内容
      console.log(`🎬 [Home.jsx] handleGenerate - referenceImages 状态:`, {
        length: referenceImages.length,
        items: referenceImages.map((img, idx) => ({
          index: idx,
          hasFile: !!img.file,
          fileName: img.file?.name,
          fileSize: img.file?.size,
          fileType: img.file?.type,
          hasPreview: !!img.preview
        }))
      })
      
      // 提取文件数组
      const imageFiles = referenceImages.map((img) => img.file)
      console.log(`📦 [Home.jsx] 提取的 imageFiles:`, {
        length: imageFiles.length,
        items: imageFiles.map((f, idx) => ({
          index: idx,
          name: f?.name,
          size: f?.size,
          type: f?.type,
          isFile: f instanceof File
        }))
      })
      
      const result = await chatAPI.chat(
        message,
        mode,
        [],
        imageFiles,
        finalAspectRatio,
        resolution,
        temperature
      )

      // ⚠️ 调试：检查返回结果
      console.log(`🔍 [Home.jsx] 收到聊天结果:`, {
        resultType: typeof result,
        keys: Object.keys(result || {}),
        isBlob: result?.is_blob,
        hasImageBlob: result?.image_blob instanceof Blob,
        imageBlobSize: result?.image_blob?.size,
        hasImageData: !!result?.image_data,
        imageFormat: result?.image_format,
        response: result?.response
      })

      let aiImageForSave = null

      if (result?.is_blob && result.image_blob instanceof Blob) {
        console.log(`✅ [Home.jsx] Blob 响应处理 - 大小: ${result.image_blob.size} bytes`)
        if (imageBlobUrlRef.current) {
          URL.revokeObjectURL(imageBlobUrlRef.current)
          imageBlobUrlRef.current = null
        }
        const tempUrl = URL.createObjectURL(result.image_blob)
        imageBlobUrlRef.current = tempUrl
        setImageBlobUrl(tempUrl)
        setImageData(result.image_blob)
        setImageFormat(result.image_format || 'jpeg')
        aiImageForSave = result.image_blob
        setShowImageModal(true)
        console.log(`📸 [Home.jsx] 已显示图片，URL: ${tempUrl}`)
      } else if (result?.image_data) {
        const dataUrl = result.image_data.startsWith('data:')
          ? result.image_data
          : `data:image/${result.image_format || 'jpeg'};base64,${result.image_data}`
        setImageData(dataUrl)
        setImageFormat(result.image_format || 'jpeg')
        aiImageForSave = dataUrl
        setShowImageModal(true)
      } else if (result?.image_url) {
        setImageData(result.image_url)
        setImageFormat(result.image_format || 'jpeg')
        aiImageForSave = result.image_url
        setShowImageModal(true)
      }

      const responseText = result?.response || result?.message || ''
      setResponse(responseText)

      const referenceImageData = referenceImages[0]?.preview || null
      if (!isSaving) {
        setIsSaving(true)
        await saveChatHistory({
          currentProjectId,
          createNewProject,
          userMessage: message,
          referenceImage: referenceImageData,
          aiImageData: aiImageForSave,
          aiResponse: responseText,
          source: 'Home'
        })
      }

      setMessage('')
    } catch (error) {
      logger.error('请求错误', error)
      setResponse(t('modal.error'))
      try {
        await saveChatHistoryWithError({
          currentProjectId,
          createNewProject,
          userMessage: message,
          error: error?.message || 'unknown',
          source: 'Home'
        })
      } catch (saveError) {
        logger.error('保存错误记录失败', saveError)
      }
    } finally {
      setIsSaving(false)
      setLoading(false)
      setIsRequesting(false)
      requestIdRef.current = null
    }
  }

  const handleOldPhotoUpload = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setOldPhotoFile(file)
      const reader = new FileReader()
      reader.onload = (event) => setOldPhotoPreview(event.target.result)
      reader.readAsDataURL(file)
    }
  }

  const handleOldPhotoDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) {
      setOldPhotoFile(file)
      const reader = new FileReader()
      reader.onload = (event) => setOldPhotoPreview(event.target.result)
      reader.readAsDataURL(file)
    }
  }

  const handleOldPhotoDragOver = (e) => {
    e.preventDefault()
  }

  const handleOldPhotoRestore = async (e) => {
    e.preventDefault()
    if (!oldPhotoFile) {
      alert('请先上传老照片')
      return
    }

    setOldPhotoLoading(true)
    setRestoredImage(null)

    try {
      const result = await restoreOldPhoto(oldPhotoFile, oldPhotoPrompt)
      setRestoredImage(result.image_data)
    } catch (error) {
      logger.error('老照片修复失败', error)
      alert(`修复失败: ${error.message}`)
    } finally {
      setOldPhotoLoading(false)
    }
  }

  const handleDownloadRestored = () => {
    if (!restoredImage) return
    const link = document.createElement('a')
    link.href = restoredImage
    link.download = `restored_${Date.now()}.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <>
      {mode === 'old_photo_restore' ? (
        <OldPhotoRestore
          oldPhotoFile={oldPhotoFile}
          oldPhotoPreview={oldPhotoPreview}
          oldPhotoPrompt={oldPhotoPrompt}
          oldPhotoLoading={oldPhotoLoading}
          restoredImage={restoredImage}
          onFileChange={handleOldPhotoUpload}
          onPromptChange={setOldPhotoPrompt}
          onSubmit={handleOldPhotoRestore}
          onDownload={handleDownloadRestored}
          onClearFile={() => {
            setOldPhotoFile(null)
            setOldPhotoPreview(null)
          }}
          onDrop={handleOldPhotoDrop}
          onDragOver={handleOldPhotoDragOver}
        />
      ) : (
        <div className="relative z-10 mt-[60px] flex flex-col items-center justify-center max-md:mt-[5%] px-4">
          <div className="mb-4 text-center max-md:mb-2">
            <img
              src="/icon.png"
              alt={t('app.name')}
              className="mx-auto mb-3 h-[269px] w-[269px] max-md:h-[120px] max-md:w-[120px] max-md:mb-2 object-contain"
            />
            <h1 className="text-[46px] font-medium text-white max-md:text-2xl max-md:mb-2 mb-4">
              {t('app.slogan')}
            </h1>
          </div>

          <MainForm
            message={message}
            setMessage={setMessage}
            mode={mode}
            setMode={setMode}
            aspectRatio={aspectRatio}
            setAspectRatio={setAspectRatio}
            resolution={resolution}
            setResolution={setResolution}
            temperature={temperature}
            setTemperature={setTemperature}
            loading={loading}
            referenceImages={referenceImages}
            onSubmit={handleSubmit}
            onImageSelect={handleImageSelect}
            onRemoveImage={handleRemoveImage}
          />

          {response && (
            <div className="mt-8 max-md:mt-4 w-[min(800px,100%)] max-md:w-full rounded-3xl max-md:rounded-2xl bg-white/[8%] p-6 max-md:p-4 text-white/70 max-md:text-sm">
              <div className="whitespace-pre-wrap break-all">{response}</div>
            </div>
          )}

          <ImageModal
            show={showImageModal}
            imageData={imageData}
            imageBlobUrl={imageBlobUrl}
            response={response}
            onClose={handleCloseModal}
            onDownload={handleDownloadImage}
          />

          <InspirationGallery templates={templates} onTemplateClick={handleTemplateClick} />
        </div>
      )}
    </>
  )
}

export default Home

