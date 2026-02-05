/**
 * 用户等级皇冠组件
 * 显示在用户头像顶部的等级标识（皇冠）
 * 参考真实皇冠设计：底部基座、珠串装饰、5个尖峰、中央宝石
 */
import React from 'react'

// 用户等级配置
export const USER_LEVELS = {
  normal: {
    name: '普通用户',
    color: '#9CA3AF', // 灰色
    bgColor: 'rgba(156, 163, 175, 0.2)',
    borderColor: 'rgba(156, 163, 175, 0.5)',
  },
  basic: {
    name: '基础版',
    color: '#C0C0C0', // 白银色
    bgColor: 'rgba(192, 192, 192, 0.3)',
    borderColor: 'rgba(192, 192, 192, 0.8)',
  },
  professional: {
    name: '专业版',
    color: '#FFD700', // 黄金色
    bgColor: 'rgba(255, 215, 0, 0.3)',
    borderColor: 'rgba(255, 215, 0, 0.8)',
  },
  enterprise: {
    name: '企业版',
    color: '#B9F2FF', // 钻石色（蓝白色）
    bgColor: 'rgba(185, 242, 255, 0.3)',
    borderColor: 'rgba(185, 242, 255, 0.8)',
  },
}

/**
 * 用户等级皇冠组件
 * @param {string} level - 用户等级 (normal, basic, professional, enterprise)
 * @param {number} size - 皇冠大小（像素），默认16
 */
function UserLevelBadge({ level = 'normal', size = 16 }) {
  const levelConfig = USER_LEVELS[level] || USER_LEVELS.normal

  // SVG皇冠设计（基于真实皇冠样式）
  const getCrownSVG = () => {
    const width = size
    const height = size
    const centerX = width / 2
    
    // 皇冠尺寸参数
    const baseHeight = height * 0.15 // 底部基座高度
    const baseY = height - baseHeight // 基座顶部Y坐标
    const beadY = baseY - height * 0.08 // 珠串位置
    const peakBaseY = beadY - height * 0.03 // 尖峰起点
    
    // 5个尖峰的参数
    const peaks = [
      { x: centerX, height: height * 0.45, isCenter: true }, // 中间最高
      { x: centerX - width * 0.25, height: height * 0.35 }, // 左侧第二个
      { x: centerX + width * 0.25, height: height * 0.35 }, // 右侧第二个
      { x: centerX - width * 0.42, height: height * 0.28 }, // 最左侧
      { x: centerX + width * 0.42, height: height * 0.28 }, // 最右侧
    ]
    
    const peakWidth = width * 0.08 // 尖峰宽度
    const beadSize = width * 0.03 // 珠子大小
    const orbSize = width * 0.04 // 尖峰顶部圆珠大小
    const jewelWidth = width * 0.12 // 中央宝石宽度
    const jewelHeight = height * 0.15 // 中央宝石高度
    
    // 根据等级生成不同的皇冠样式
    switch (level) {
      case 'normal':
        return null
      
      case 'basic':
        // 白银皇冠
        return (
          <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
            <defs>
              <linearGradient id={`silverMetal-${size}`} x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#F8F8F8" stopOpacity="1" />
                <stop offset="50%" stopColor="#E0E0E0" stopOpacity="1" />
                <stop offset="100%" stopColor="#C0C0C0" stopOpacity="1" />
              </linearGradient>
              <linearGradient id={`silverShine-${size}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
              </linearGradient>
              <filter id={`silverGlow-${size}`}>
                <feGaussianBlur stdDeviation="0.5" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            
            {/* 底部基座 */}
            <rect x="0" y={baseY} width={width} height={baseHeight} 
                  fill={`url(#silverMetal-${size})`} rx="1" />
            
            {/* 珠串装饰 */}
            {Array.from({ length: 8 }).map((_, i) => {
              const x = (width / 9) * (i + 1)
              return (
                <circle key={i} cx={x} cy={beadY} r={beadSize} 
                        fill={`url(#silverMetal-${size})`} 
                        stroke="#A0A0A0" strokeWidth="0.3" />
              )
            })}
            
            {/* 5个尖峰 */}
            {peaks.map((peak, i) => (
              <g key={i}>
                <path
                  d={`M ${peak.x - peakWidth/2} ${peakBaseY} 
                      L ${peak.x} ${peakBaseY - peak.height} 
                      L ${peak.x + peakWidth/2} ${peakBaseY} Z`}
                  fill={`url(#silverMetal-${size})`}
                  stroke="#A0A0A0"
                  strokeWidth="0.5"
                />
                {/* 尖峰顶部圆珠 */}
                <circle cx={peak.x} cy={peakBaseY - peak.height - orbSize/2} 
                        r={orbSize} 
                        fill={`url(#silverMetal-${size})`}
                        stroke="#A0A0A0" strokeWidth="0.3" />
                {/* 中央宝石（白银版用浅蓝色宝石） */}
                {peak.isCenter && (
                  <ellipse cx={peak.x} cy={peakBaseY - peak.height + jewelHeight/2} 
                          rx={jewelWidth/2} ry={jewelHeight/2}
                          fill="#B8D4E3" stroke="#8FB8CC" strokeWidth="0.5" />
                )}
              </g>
            ))}
            
            {/* 高光效果 */}
            <rect x="0" y={baseY} width={width * 0.3} height={baseHeight} 
                  fill={`url(#silverShine-${size})`} rx="1" />
          </svg>
        )
      
      case 'professional':
        // 黄金皇冠
        return (
          <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
            <defs>
              <linearGradient id={`goldMetal-${size}`} x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#FFED4E" stopOpacity="1" />
                <stop offset="50%" stopColor="#FFD700" stopOpacity="1" />
                <stop offset="100%" stopColor="#D4AF37" stopOpacity="1" />
              </linearGradient>
              <linearGradient id={`goldShine-${size}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.7" />
                <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
              </linearGradient>
              <filter id={`goldGlow-${size}`}>
                <feGaussianBlur stdDeviation="0.8" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            
            {/* 底部基座 */}
            <rect x="0" y={baseY} width={width} height={baseHeight} 
                  fill={`url(#goldMetal-${size})`} rx="1" filter={`url(#goldGlow-${size})`} />
            
            {/* 珠串装饰 */}
            {Array.from({ length: 8 }).map((_, i) => {
              const x = (width / 9) * (i + 1)
              return (
                <circle key={i} cx={x} cy={beadY} r={beadSize} 
                        fill={`url(#goldMetal-${size})`} 
                        stroke="#CC9900" strokeWidth="0.3" />
              )
            })}
            
            {/* 5个尖峰 */}
            {peaks.map((peak, i) => (
              <g key={i}>
                <path
                  d={`M ${peak.x - peakWidth/2} ${peakBaseY} 
                      L ${peak.x} ${peakBaseY - peak.height} 
                      L ${peak.x + peakWidth/2} ${peakBaseY} Z`}
                  fill={`url(#goldMetal-${size})`}
                  stroke="#CC9900"
                  strokeWidth="0.5"
                  filter={peak.isCenter ? `url(#goldGlow-${size})` : undefined}
                />
                {/* 尖峰顶部圆珠 */}
                <circle cx={peak.x} cy={peakBaseY - peak.height - orbSize/2} 
                        r={orbSize} 
                        fill={`url(#goldMetal-${size})`}
                        stroke="#CC9900" strokeWidth="0.3" />
                {/* 中央宝石（金色版用红色宝石，参考图样式） */}
                {peak.isCenter && (
                  <>
                    <ellipse cx={peak.x} cy={peakBaseY - peak.height + jewelHeight/2} 
                            rx={jewelWidth/2} ry={jewelHeight/2}
                            fill="#FF4500" stroke="#CC3300" strokeWidth="0.5" />
                    <ellipse cx={peak.x - jewelWidth/6} cy={peakBaseY - peak.height + jewelHeight/2 - jewelHeight/6} 
                            rx={jewelWidth/6} ry={jewelHeight/6}
                            fill="#FFFFFF" opacity="0.6" />
                  </>
                )}
              </g>
            ))}
            
            {/* 高光效果 */}
            <rect x="0" y={baseY} width={width * 0.3} height={baseHeight} 
                  fill={`url(#goldShine-${size})`} rx="1" />
          </svg>
        )
      
      case 'enterprise':
        // 钻石皇冠（蓝白色，带闪光效果）
        return (
          <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
            <defs>
              <linearGradient id={`diamondMetal-${size}`} x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
                <stop offset="30%" stopColor="#E0F7FF" stopOpacity="0.9" />
                <stop offset="60%" stopColor="#B9F2FF" stopOpacity="0.95" />
                <stop offset="100%" stopColor="#87CEEB" stopOpacity="0.9" />
              </linearGradient>
              <linearGradient id={`diamondShine-${size}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
              </linearGradient>
              <radialGradient id={`diamondJewel-${size}`} cx="50%" cy="40%">
                <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
                <stop offset="50%" stopColor="#B9F2FF" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#5F9EA0" stopOpacity="0.9" />
              </radialGradient>
              <filter id={`diamondGlow-${size}`}>
                <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            
            {/* 底部基座 */}
            <rect x="0" y={baseY} width={width} height={baseHeight} 
                  fill={`url(#diamondMetal-${size})`} rx="1" filter={`url(#diamondGlow-${size})`} />
            
            {/* 珠串装饰 */}
            {Array.from({ length: 8 }).map((_, i) => {
              const x = (width / 9) * (i + 1)
              return (
                <circle key={i} cx={x} cy={beadY} r={beadSize} 
                        fill={`url(#diamondMetal-${size})`} 
                        stroke="#87CEEB" strokeWidth="0.3" />
              )
            })}
            
            {/* 5个尖峰 */}
            {peaks.map((peak, i) => (
              <g key={i}>
                <path
                  d={`M ${peak.x - peakWidth/2} ${peakBaseY} 
                      L ${peak.x} ${peakBaseY - peak.height} 
                      L ${peak.x + peakWidth/2} ${peakBaseY} Z`}
                  fill={`url(#diamondMetal-${size})`}
                  stroke="#87CEEB"
                  strokeWidth="0.5"
                  filter={peak.isCenter ? `url(#diamondGlow-${size})` : undefined}
                />
                {/* 尖峰顶部圆珠 */}
                <circle cx={peak.x} cy={peakBaseY - peak.height - orbSize/2} 
                        r={orbSize} 
                        fill={`url(#diamondMetal-${size})`}
                        stroke="#87CEEB" strokeWidth="0.3" />
                {/* 中央宝石（钻石版用蓝色宝石） */}
                {peak.isCenter && (
                  <>
                    <ellipse cx={peak.x} cy={peakBaseY - peak.height + jewelHeight/2} 
                            rx={jewelWidth/2} ry={jewelHeight/2}
                            fill={`url(#diamondJewel-${size})`} 
                            stroke="#5F9EA0" strokeWidth="0.5" />
                    <ellipse cx={peak.x - jewelWidth/6} cy={peakBaseY - peak.height + jewelHeight/2 - jewelHeight/6} 
                            rx={jewelWidth/6} ry={jewelHeight/6}
                            fill="#FFFFFF" opacity="0.8" />
                  </>
                )}
              </g>
            ))}
            
            {/* 高光效果 */}
            <rect x="0" y={baseY} width={width * 0.3} height={baseHeight} 
                  fill={`url(#diamondShine-${size})`} rx="1" />
          </svg>
        )
      
      default:
        return null
    }
  }

  // 普通用户不显示
  if (level === 'normal') {
    return null
  }

  return (
    <div
      className="inline-flex items-center justify-center"
      style={{
        width: size,
        height: size,
      }}
      title={levelConfig.name}
    >
      {getCrownSVG()}
    </div>
  )
}

export default UserLevelBadge
