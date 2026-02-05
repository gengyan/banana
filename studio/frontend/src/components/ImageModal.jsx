import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import logger from '../utils/logger'

/**
 * 图片显示弹框组件
 */
export default function ImageModal({ 
  show, 
  imageData, 
  imageBlobUrl,
  response,
  onClose,
  onDownload 
}) {
  const { t } = useTranslation()
  const blobUrlRef = useRef(null)
  const [displayUrl, setDisplayUrl] = useState(null)
  const [imageLoadError, setImageLoadError] = useState(null)

  // 管理 Blob URL 的创建和清理
  useEffect(() => {
    // 清理旧的 Blob URL
    if (blobUrlRef.current) {
      console.log('🧹 [ImageModal] 清理旧的 Blob URL:', blobUrlRef.current.substring(0, 50))
      URL.revokeObjectURL(blobUrlRef.current)
      blobUrlRef.current = null
    }

    if (!show || !imageData) {
      setDisplayUrl(null)
      setImageLoadError(null)
      return
    }

    // 为 Blob 创建 URL
    if (imageData instanceof Blob) {
      console.log('🖼️ [ImageModal] 创建 Blob URL，类型:', imageData.type, '大小:', (imageData.size / 1024).toFixed(2), 'KB')
      const url = URL.createObjectURL(imageData)
      blobUrlRef.current = url
      setDisplayUrl(url)
      console.log('✅ [ImageModal] Blob URL 已创建:', url)
    } else if (typeof imageData === 'string') {
      // 字符串类型（Base64、HTTP URL 或已有的 blob: URL）
      setDisplayUrl(imageBlobUrl || imageData)
    } else {
      setDisplayUrl(null)
    }

    // 组件卸载或 imageData 变化时清理
    return () => {
      if (blobUrlRef.current) {
        console.log('🧹 [ImageModal] 组件清理，撤销 Blob URL')
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
    }
  }, [show, imageData, imageBlobUrl])

  // ESC 键关闭弹框
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && show) {
        console.log('⌨️ [ImageModal] 按下 ESC，关闭弹框')
        onClose()
      }
    }
    
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [show, onClose])

  if (!show || !imageData) return null

  // 检查是否可以显示图片
  const canDisplay = imageData !== 'prompt_only' && imageData !== 'error' && (
    (imageData instanceof Blob) ||
    (typeof imageData === 'string' && (
      imageData.startsWith('data:image') || 
      imageData.startsWith('data:') || 
      imageData.startsWith('http') ||
      imageData.startsWith('blob:') ||
      imageData.length > 100
    ))
  )

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm max-md:p-4"
      onClick={onClose}
    >
      <div 
        className="relative max-w-4xl max-h-[90vh] max-md:max-h-[95vh] max-md:w-full bg-[#1a1a1a] rounded-3xl max-md:rounded-2xl p-6 max-md:p-4 m-4 max-md:m-0"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 max-md:top-2 max-md:right-2 text-white/70 hover:text-white text-2xl max-md:text-xl font-bold w-10 h-10 max-md:w-8 max-md:h-8 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition"
        >
          ×
        </button>

        <div className="mt-4 max-md:mt-2">
          {imageData === 'error' || imageData === 'prompt_only' ? (
            /* 错误或仅提示词 */
            <div className="text-white p-6 max-md:p-4 max-w-2xl max-md:max-w-full">
              <h3 className="text-xl max-md:text-lg font-bold mb-4 max-md:mb-3 text-center text-red-400">
                {imageData === 'error' ? t('error.imageGenerationFailed') : t('modal.promptOnly')}
              </h3>
              <div className="bg-white/5 rounded-xl max-md:rounded-lg p-4 max-md:p-3 max-h-[60vh] max-md:max-h-[50vh] overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm max-md:text-xs text-white/80">{response || t('modal.noErrorInfo')}</pre>
              </div>
              {imageData === 'error' && (
                <p className="mt-4 max-md:mt-3 text-sm max-md:text-xs text-orange-400 text-center">
                  {t('error.checkBackendLogs')}
                </p>
              )}
            </div>
          ) : canDisplay ? (
            /* 显示图片 */
            <div>
              <div className="relative">
                <img 
                  src={displayUrl} 
                  alt="生成的图片" 
                  className="max-w-full max-h-[80vh] max-md:max-h-[70vh] rounded-xl max-md:rounded-lg mx-auto block"
                  style={{ 
                    display: 'block',
                    maxWidth: '100%',
                    height: 'auto'
                  }}
                  onLoad={() => {
                    console.log('✅ [ImageModal] 图片加载成功')
                    setImageLoadError(null)
                  }}
                  onError={(e) => {
                    const errorInfo = {
                      src: e.target.src,
                      imageDataType: imageData instanceof Blob ? 'Blob' : typeof imageData,
                      blobType: imageData instanceof Blob ? imageData.type : 'N/A',
                      blobSize: imageData instanceof Blob ? `${(imageData.size / 1024).toFixed(2)} KB` : 'N/A',
                      displayUrl: displayUrl?.substring(0, 100)
                    }
                    console.error('❌ [ImageModal] 图片加载失败')
                    console.error('   详细信息:', errorInfo)
                    setImageLoadError(errorInfo)

                    // 🔁 Fallback: 若 Blob URL 加载失败，尝试将 Blob 转为 dataURL 再显示
                    if (imageData instanceof Blob && imageData.type?.startsWith('image/')) {
                      try {
                        const reader = new FileReader()
                        reader.onloadend = () => {
                          const dataUrl = reader.result
                          if (typeof dataUrl === 'string' && dataUrl.startsWith('data:image')) {
                            console.warn('⚠️ [ImageModal] Blob URL 加载失败，已回退为 dataURL 显示')
                            setDisplayUrl(dataUrl)
                            setImageLoadError(null)
                          }
                        }
                        reader.readAsDataURL(imageData)
                      } catch (fallbackErr) {
                        console.error('❌ [ImageModal] Blob→dataURL 回退失败', fallbackErr)
                      }
                    }
                  }}
                />
                
                {/* 调试信息：图片加载错误时显示 */}
                {imageLoadError && (
                  <div className="mt-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-white text-xs">
                    <p className="font-bold mb-2">🔍 图片加载失败调试信息：</p>
                    <pre className="whitespace-pre-wrap">{JSON.stringify(imageLoadError, null, 2)}</pre>
                  </div>
                )}

                {/* 下载按钮 */}
                <div className="mt-4 flex justify-center">
                  <button
                    onClick={onDownload}
                    className="inline-flex items-center gap-2 px-6 py-3 max-md:px-4 max-md:py-2.5 max-md:text-sm rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 text-white font-bold hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 transition active:scale-[0.97]"
                  >
                    <svg 
                      className="w-5 h-5 max-md:w-4 max-md:h-4" 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path 
                        strokeLinecap="round" 
                        strokeLinejoin="round" 
                        strokeWidth={2} 
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" 
                      />
                    </svg>
                    {t('modal.download', '下载图片')}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* 数据准备中 */
            <div className="text-white/70 p-8 text-center">
              <p className="mb-4">图片数据准备中...</p>
              {response && (
                <div className="mt-4 text-xs text-white/50">
                  <p>后端响应: {response.substring(0, 100)}...</p>
                </div>
              )}
              <div className="mt-4 text-xs text-white/40">
                <p>imageData 值: {imageData ? (typeof imageData === 'string' ? imageData.substring(0, 50) + '...' : 'Blob Object') : 'null'}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
