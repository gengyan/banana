import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * 灵感发现/模板图片画廊组件
 */
export default function InspirationGallery({ templates, onTemplateClick }) {
  const { t } = useTranslation()

  if (!templates || templates.length === 0) {
    return null
  }

  return (
    <div className="mt-12 w-full max-w-[1400px] max-md:w-full">
      <div className="flex items-center gap-2 mb-6 max-md:mb-4">
        <h2 className="text-2xl max-md:text-xl font-bold text-white">
          {t('home.inspirationDiscovery', '灵感发现')}
        </h2>
        <span className="text-2xl max-md:text-xl">🔥</span>
      </div>

      {/* 瀑布流布局 - PC端5列，移动端1列，高度自适应 */}
      <div className="columns-1 md:columns-2 lg:columns-3 xl:columns-5 gap-4 max-md:gap-3">
        {templates.map((template, index) => (
          <div
            key={index}
            className="break-inside-avoid mb-4 max-md:mb-3 cursor-pointer group"
            onClick={() => onTemplateClick && onTemplateClick(template)}
          >
            <div className="relative rounded-2xl max-md:rounded-xl overflow-hidden bg-white/[4%] hover:bg-white/[8%] transition-all duration-300">
              <TemplateImage imageResult={template.image} alt={template.prompt} />
              
              {/* 悬浮提示词 */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4 max-md:p-3">
                <p className="text-white text-sm max-md:text-xs line-clamp-3">
                  {template.prompt}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// 模板图片组件：自动尝试多种扩展名
function TemplateImage({ imageResult, alt }) {
  const [imageUrl, setImageUrl] = useState(null)
  const [hasError, setHasError] = useState(false)
  
  useEffect(() => {
    if (!imageResult) return
    
    setImageUrl(null)
    setHasError(false)
    
    const hasExtension = /\.(jpg|jpeg|png|jfif|JPG|JPEG|PNG|JFIF)$/i.test(imageResult)
    
    if (hasExtension) {
      const url = `/images/${imageResult}`
      fetch(url, { method: 'HEAD', cache: 'no-cache' })
        .then(response => {
          if (response.ok) {
            const contentType = response.headers.get('content-type')
            if (contentType && contentType.startsWith('image/')) {
              setImageUrl(url)
            } else {
              setHasError(true)
            }
          } else {
            setHasError(true)
          }
        })
        .catch(() => setHasError(true))
      return
    }
    
    const extensions = ['.jpg', '.png', '.jfif', '.jpeg', '.JPG', '.PNG', '.JFIF', '.JPEG']
    let currentIndex = 0
    let cancelled = false
    
    const tryNextExtension = async () => {
      if (cancelled || currentIndex >= extensions.length) {
        if (currentIndex >= extensions.length && !cancelled) {
          setHasError(true)
        }
        return
      }
      
      const url = `/images/${imageResult}${extensions[currentIndex]}`
      
      try {
        const response = await fetch(url, { method: 'HEAD', cache: 'no-cache' })
        if (response.ok) {
          const contentType = response.headers.get('content-type')
          if (contentType && contentType.startsWith('image/')) {
            if (!cancelled) setImageUrl(url)
            return
          }
        }
      } catch (e) {
        // 继续尝试
      }
      
      currentIndex++
      tryNextExtension()
    }
    
    tryNextExtension()
    
    return () => { cancelled = true }
  }, [imageResult])
  
  if (hasError) {
    return (
      <div className="w-full h-48 bg-gray-200 flex items-center justify-center">
        <span className="text-gray-400 text-sm">图片加载失败</span>
      </div>
    )
  }
  
  if (!imageUrl) {
    return <div className="w-full h-48 bg-gray-100 animate-pulse"></div>
  }
  
  return (
    <img
      src={imageUrl}
      alt={alt}
      className="w-full h-auto object-cover"
      onError={() => setHasError(true)}
    />
  )
}
