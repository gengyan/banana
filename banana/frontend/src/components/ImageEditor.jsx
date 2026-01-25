import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

function ImageEditor({ imageSrc, onSave, onCancel, aspectRatio = null }) {
  const { t } = useTranslation()
  const canvasRef = useRef(null)
  const imageRef = useRef(null)
  const containerRef = useRef(null)
  
  const [scale, setScale] = useState(1)
  const [cropStart, setCropStart] = useState(null)
  const [cropArea, setCropArea] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isMoving, setIsMoving] = useState(false)
  const [moveOffset, setMoveOffset] = useState({ x: 0, y: 0 })
  const [imageLoaded, setImageLoaded] = useState(false)
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const img = new Image()
    let isMounted = true
    img.onload = () => {
      if (!isMounted) return
      setImageSize({ width: img.width, height: img.height })
      setImageLoaded(true)
      // 计算初始缩放比例，使图片适应容器
      if (containerRef.current) {
        const container = containerRef.current
        const containerWidth = container.clientWidth - 40
        const containerHeight = container.clientHeight - 200
        const scaleX = containerWidth / img.width
        const scaleY = containerHeight / img.height
        const initialScale = Math.min(scaleX, scaleY, 1)
        setScale(initialScale)
        
        // 如果有固定宽高比，初始化一个默认的正方形裁切区域
        if (aspectRatio) {
          setTimeout(() => {
            if (!isMounted || !containerRef.current) return
            const displaySize = {
              width: img.width * initialScale,
              height: img.height * initialScale
            }
            const offsetX = (container.clientWidth - displaySize.width) / 2
            const offsetY = (container.clientHeight - displaySize.height) / 2
            
            // 计算一个合适的正方形大小（取图片显示大小的80%或300px，取较小值）
            const maxSize = Math.min(displaySize.width, displaySize.height) * 0.8
            const defaultSize = Math.min(maxSize, 300)
            const centerX = offsetX + displaySize.width / 2
            const centerY = offsetY + displaySize.height / 2
            
            setCropArea({
              x: centerX - defaultSize / 2,
              y: centerY - defaultSize / 2,
              width: defaultSize,
              height: defaultSize
            })
          }, 100)
        }
      }
    }
    img.src = imageSrc
    imageRef.current = img
    
    return () => {
      isMounted = false
    }
  }, [imageSrc, aspectRatio])

  const getDisplaySize = () => {
    if (!imageLoaded) return { width: 0, height: 0 }
    return {
      width: imageSize.width * scale,
      height: imageSize.height * scale
    }
  }

  const isPointInCropArea = (x, y) => {
    if (!cropArea) return false
    return x >= cropArea.x && x <= cropArea.x + cropArea.width &&
           y >= cropArea.y && y <= cropArea.y + cropArea.height
  }

  const constrainCropArea = (area, displaySize, offsetX, offsetY) => {
    let { x, y, width, height } = area
    
    // 如果超出图片边界，调整位置
    if (x < offsetX) x = offsetX
    if (y < offsetY) y = offsetY
    if (x + width > offsetX + displaySize.width) {
      x = offsetX + displaySize.width - width
    }
    if (y + height > offsetY + displaySize.height) {
      y = offsetY + displaySize.height - height
    }
    
    // 确保在图片范围内
    if (x < offsetX) {
      width = width - (offsetX - x)
      x = offsetX
    }
    if (y < offsetY) {
      height = height - (offsetY - y)
      y = offsetY
    }
    if (x + width > offsetX + displaySize.width) {
      width = offsetX + displaySize.width - x
    }
    if (y + height > offsetY + displaySize.height) {
      height = offsetY + displaySize.height - y
    }
    
    return { x, y, width, height }
  }

  const handleMouseDown = (e) => {
    if (!imageLoaded) return
    const rect = containerRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    
    const displaySize = getDisplaySize()
    const offsetX = (containerRef.current.clientWidth - displaySize.width) / 2
    const offsetY = (containerRef.current.clientHeight - displaySize.height) / 2
    
    // 检查是否在图片范围内
    if (x < offsetX || x > offsetX + displaySize.width ||
        y < offsetY || y > offsetY + displaySize.height) {
      return
    }
    
    // 检查是否点击在裁切区域内
    if (cropArea && isPointInCropArea(x, y)) {
      // 移动模式
      setIsMoving(true)
      setMoveOffset({
        x: x - cropArea.x,
        y: y - cropArea.y
      })
    } else {
      // 创建新裁切区域
      setCropStart({ x, y })
      setIsDragging(true)
    }
  }

  const handleMouseMove = (e) => {
    if (!imageLoaded) return
    
    const rect = containerRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    
    const displaySize = getDisplaySize()
    const offsetX = (containerRef.current.clientWidth - displaySize.width) / 2
    const offsetY = (containerRef.current.clientHeight - displaySize.height) / 2
    
    if (isMoving && cropArea) {
      // 移动裁切区域
      let newX = x - moveOffset.x
      let newY = y - moveOffset.y
      
      const newArea = {
        ...cropArea,
        x: newX,
        y: newY
      }
      
      const constrained = constrainCropArea(newArea, displaySize, offsetX, offsetY)
      setCropArea(constrained)
    } else if (isDragging && cropStart) {
      // 创建新裁切区域
      const startX = Math.max(offsetX, Math.min(cropStart.x, offsetX + displaySize.width))
      const startY = Math.max(offsetY, Math.min(cropStart.y, offsetY + displaySize.height))
      let endX = Math.max(offsetX, Math.min(x, offsetX + displaySize.width))
      let endY = Math.max(offsetY, Math.min(y, offsetY + displaySize.height))
      
      let width = Math.abs(endX - startX)
      let height = Math.abs(endY - startY)
      
      // 如果有固定宽高比，强制保持比例
      if (aspectRatio) {
        const ratio = aspectRatio
        if (width > height * ratio) {
          width = height * ratio
        } else {
          height = width / ratio
        }
        
        // 调整结束点以保持比例
        if (endX > startX) {
          endX = startX + width
        } else {
          endX = startX - width
        }
        if (endY > startY) {
          endY = startY + height
        } else {
          endY = startY - height
        }
      }
      
      const cropX = Math.min(startX, endX)
      const cropY = Math.min(startY, endY)
      
      let newArea = {
        x: cropX,
        y: cropY,
        width: width,
        height: height
      }
      
      // 确保最小尺寸
      const minSize = 50
      if (newArea.width < minSize) newArea.width = minSize
      if (newArea.height < minSize) newArea.height = minSize
      
      // 如果有固定宽高比，再次调整
      if (aspectRatio) {
        const ratio = aspectRatio
        if (newArea.width > newArea.height * ratio) {
          newArea.width = newArea.height * ratio
        } else {
          newArea.height = newArea.width / ratio
        }
      }
      
      // 约束在图片范围内
      newArea = constrainCropArea(newArea, displaySize, offsetX, offsetY)
      
      setCropArea(newArea)
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
    setIsMoving(false)
    setCropStart(null)
  }

  const handleScaleChange = (e) => {
    setScale(parseFloat(e.target.value))
  }

  const handleSave = () => {
    if (!imageLoaded || !imageRef.current) return

    const canvas = canvasRef.current
    if (!canvas) return

    const img = imageRef.current
    const displaySize = getDisplaySize()
    
    const ctx = canvas.getContext('2d')
    
    if (cropArea && cropArea.width > 10 && cropArea.height > 10) {
      // 有裁切区域，计算源图片的裁切区域
      const offsetX = (containerRef.current.clientWidth - displaySize.width) / 2
      const offsetY = (containerRef.current.clientHeight - displaySize.height) / 2
      
      const srcX = Math.max(0, (cropArea.x - offsetX) / scale)
      const srcY = Math.max(0, (cropArea.y - offsetY) / scale)
      const srcWidth = Math.min(img.width - srcX, cropArea.width / scale)
      const srcHeight = Math.min(img.height - srcY, cropArea.height / scale)
      
      const finalWidth = Math.round(cropArea.width)
      const finalHeight = Math.round(cropArea.height)
      
      canvas.width = finalWidth
      canvas.height = finalHeight
      
      ctx.drawImage(
        img,
        srcX, srcY, srcWidth, srcHeight,
        0, 0, finalWidth, finalHeight
      )
    } else {
      // 没有裁切，直接缩放
      const finalWidth = Math.round(imageSize.width * scale)
      const finalHeight = Math.round(imageSize.height * scale)
      
      canvas.width = finalWidth
      canvas.height = finalHeight
      
      ctx.drawImage(img, 0, 0, finalWidth, finalHeight)
    }
    
    // 转换为blob并回调
    canvas.toBlob((blob) => {
      const reader = new FileReader()
      reader.onloadend = () => {
        // 创建File对象
        const file = new File([blob], `edited-image-${Date.now()}.png`, { type: 'image/png' })
        onSave(file, reader.result)
      }
      reader.readAsDataURL(blob)
    }, 'image/png')
  }

  const displaySize = getDisplaySize()
  const offsetX = imageLoaded ? (containerRef.current?.clientWidth - displaySize.width) / 2 : 0
  const offsetY = imageLoaded ? (containerRef.current?.clientHeight - displaySize.height) / 2 : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#1a1a1a] rounded-3xl p-6 m-4 flex flex-col">
        <h2 className="text-2xl font-bold text-white mb-4">{t('imageEditor.title', '编辑图片')}</h2>
        
        {/* 图片显示区域 */}
        <div 
          ref={containerRef}
          className="flex-1 min-h-[400px] bg-black/50 rounded-xl overflow-hidden relative"
          style={{ cursor: isMoving ? 'move' : (cropArea && isPointInCropArea(0, 0) ? 'move' : 'crosshair') }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {imageLoaded && (
            <img
              src={imageSrc}
              alt="编辑中"
              style={{
                width: `${displaySize.width}px`,
                height: `${displaySize.height}px`,
                position: 'absolute',
                left: `${offsetX}px`,
                top: `${offsetY}px`,
                userSelect: 'none',
                pointerEvents: 'none'
              }}
            />
          )}
          
          {/* 裁切区域遮罩和边框 */}
          {cropArea && cropArea.width > 10 && cropArea.height > 10 && (
            <>
              {/* 上方遮罩 */}
              {cropArea.y > offsetY && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${offsetX}px`,
                    top: `${offsetY}px`,
                    width: `${displaySize.width}px`,
                    height: `${cropArea.y - offsetY}px`,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    pointerEvents: 'none'
                  }}
                />
              )}
              {/* 下方遮罩 */}
              {cropArea.y + cropArea.height < offsetY + displaySize.height && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${offsetX}px`,
                    top: `${cropArea.y + cropArea.height}px`,
                    width: `${displaySize.width}px`,
                    height: `${offsetY + displaySize.height - (cropArea.y + cropArea.height)}px`,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    pointerEvents: 'none'
                  }}
                />
              )}
              {/* 左侧遮罩 */}
              {cropArea.x > offsetX && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${offsetX}px`,
                    top: `${cropArea.y}px`,
                    width: `${cropArea.x - offsetX}px`,
                    height: `${cropArea.height}px`,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    pointerEvents: 'none'
                  }}
                />
              )}
              {/* 右侧遮罩 */}
              {cropArea.x + cropArea.width < offsetX + displaySize.width && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${cropArea.x + cropArea.width}px`,
                    top: `${cropArea.y}px`,
                    width: `${offsetX + displaySize.width - (cropArea.x + cropArea.width)}px`,
                    height: `${cropArea.height}px`,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    pointerEvents: 'none'
                  }}
                />
              )}
              {/* 裁切区域边框 */}
              <div
                style={{
                  position: 'absolute',
                  left: `${cropArea.x}px`,
                  top: `${cropArea.y}px`,
                  width: `${cropArea.width}px`,
                  height: `${cropArea.height}px`,
                  border: '2px solid #3b82f6',
                  pointerEvents: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </>
          )}
        </div>

        {/* 控制面板 */}
        <div className="mt-4 space-y-4">
          {/* 缩放控制 */}
          <div>
            <label className="block text-sm text-white/70 mb-2">
              {t('imageEditor.scale', '缩放')}: {Math.round(scale * 100)}%
            </label>
            <input
              type="range"
              min="0.1"
              max="3"
              step="0.1"
              value={scale}
              onChange={handleScaleChange}
              className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-xs text-white/50 mt-1">
              <span>10%</span>
              <span>300%</span>
            </div>
          </div>

          {/* 提示信息 */}
          <div className="text-sm text-white/60">
            {aspectRatio 
              ? t('imageEditor.hintSquare', '提示：拖动裁切框可以移动位置，拖动空白区域创建新的裁切区域，使用滑块调整缩放')
              : t('imageEditor.hint', '提示：拖动鼠标选择裁切区域，使用滑块调整缩放')}
          </div>

          {/* 按钮 */}
          <div className="flex gap-3">
            <button
              onClick={onCancel}
              className="flex-1 px-6 py-3 rounded-xl bg-white/10 text-white hover:bg-white/20 transition font-medium"
            >
              {t('imageEditor.cancel', '取消')}
            </button>
            <button
              onClick={handleSave}
              className="flex-1 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 text-white font-bold hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 transition"
            >
              {t('imageEditor.save', '保存')}
            </button>
          </div>
        </div>

        {/* 隐藏的canvas用于处理图片 */}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </div>
  )
}

export default ImageEditor
