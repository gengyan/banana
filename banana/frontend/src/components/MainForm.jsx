import { useTranslation } from 'react-i18next'

/**
 * 主表单组件
 */
export default function MainForm({
  message,
  setMessage,
  mode,
  setMode,
  aspectRatio,
  setAspectRatio,
  resolution,
  setResolution,
  temperature,
  setTemperature,
  loading,
  referenceImages,
  onSubmit,
  onImageSelect,
  onRemoveImage
}) {
  const { t } = useTranslation()
  const isImageMode = mode === 'banana' || mode === 'banana_pro' || mode === 'imagen'

  return (
    <div className="wrapper relative mt-[30px] max-md:mt-4 w-[min(800px,100%)] max-md:w-full">
      <div className="color-border"></div>
      <div className="gradient-border z-10 rounded-3xl max-md:rounded-2xl border-transparent bg-[#5F5F5F]/20 p-[10px] max-md:p-2 text-white backdrop-blur-[50px] relative">

        <form onSubmit={onSubmit} className="space-y-4 max-md:space-y-3 relative z-10 p-[10px] max-md:p-2">
          {/* 参考图片预览区域 */}
          {(mode === 'banana' || mode === 'banana_pro' || mode === 'chat') && referenceImages.length > 0 && (
            <div id="attachment" className="flex items-center gap-2 max-md:gap-1.5 px-1 pb-3 max-md:pb-2 flex-wrap">
              {referenceImages.map((img, index) => (
                <div key={index} className="relative group">
                  <img 
                    src={img.preview} 
                    alt={`参考图 ${index + 1}`} 
                    className="w-20 h-20 max-md:w-16 max-md:h-16 rounded-lg object-cover border border-white/20"
                  />
                  <button
                    type="button"
                    onClick={() => onRemoveImage && onRemoveImage(index)}
                    className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <svg 
                      className="w-3 h-3" 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                      strokeWidth={3}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center gap-x-2 max-md:gap-x-1.5 max-md:flex-col max-md:items-stretch">
            {/* 图片选择按钮 */}
            <label className="shrink-0 cursor-pointer max-md:self-start">
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={onImageSelect}
                className="hidden"
                disabled={loading}
              />
              <div 
                className="group relative inline-flex h-[71.42px] w-[54px] max-md:h-12 max-md:w-10 rotate-[-15deg] max-md:rotate-0 cursor-pointer items-center justify-center overflow-hidden rounded-lg border border-dashed border-white/50 bg-white/[14%] hover:bg-white/[20%] active:scale-[0.97] transition"
                title="当前模型最多上传 14 张图片（每张 10 MB）"
              >
                <div className="absolute inset-0 bg-[linear-gradient(0deg,rgba(0,0,0,0.50)_0%,rgba(0,0,0,0.50)_100%),linear-gradient(180deg,#000_0%,#7D7D7C_100%)] opacity-0 transition-opacity group-hover:opacity-100"></div>
                <svg 
                  className="relative z-10 h-6 w-6 max-md:h-5 max-md:w-5 text-white/70" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M12 4v16m8-8H4" 
                  />
                </svg>
              </div>
            </label>

            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              maxLength={2000}
              placeholder={t('home.placeholder')}
              className="h-[88px] max-md:h-24 grow resize-none border-none bg-transparent p-[10px] max-md:p-2 text-base max-md:text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-0 z-10 relative"
              disabled={loading}
            />
          </div>

          {/* 控制栏：第一行 - 模式切换 + 长宽比 + 分辨率 */}
          <div className="flex items-center gap-3 max-md:gap-2">
            {/* 模式选择 */}
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="h-11 max-md:h-10 rounded-2xl border-none bg-white/[12%] px-4 max-md:px-3 py-2 text-base max-md:text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/20 hover:bg-white/15 cursor-pointer appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundImage: "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%23fff' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e\")",
                backgroundPosition: 'right 0.75rem center',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '1.5em 1.5em',
                paddingRight: '2.75rem'
              }}
              disabled={loading}
            >
              <option value="chat">{t('home.chatMode')}</option>
              <option value="banana">{t('home.bananaMode')}</option>
              <option value="banana_pro">{t('home.bananaProMode')}</option>
            </select>
            <select
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
              className="h-11 max-md:h-10 rounded-2xl border-none bg-white/[12%] px-4 max-md:px-3 py-2 text-base max-md:text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/20 hover:bg-white/15 cursor-pointer appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundImage: "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%23fff' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e\")",
                backgroundPosition: 'right 0.75rem center',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '1.5em 1.5em',
                paddingRight: '2.75rem'
              }}
              disabled={loading || !isImageMode}
            >
              <option value="auto">{t('home.auto', 'Auto')}</option>
              <option value="1:1">1:1</option>
              <option value="2:3">2:3</option>
              <option value="3:2">3:2</option>
              <option value="3:4">3:4</option>
              <option value="4:3">4:3</option>
              <option value="4:5">4:5</option>
              <option value="5:4">5:4</option>
              <option value="9:16">9:16</option>
              <option value="16:9">16:9</option>
              <option value="21:9">21:9</option>
            </select>

            {/* 分辨率选择 - banana模式下隐藏（只支持1K） */}
            {mode !== 'banana' && (
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="h-11 max-md:h-10 rounded-2xl border-none bg-white/[12%] px-4 max-md:px-3 py-2 text-base max-md:text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/20 hover:bg-white/15 cursor-pointer appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  backgroundImage: "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%23fff' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e\")",
                  backgroundPosition: 'right 0.75rem center',
                  backgroundRepeat: 'no-repeat',
                  backgroundSize: '1.5em 1.5em',
                  paddingRight: '2.75rem'
                }}
                disabled={loading || !isImageMode}
              >
                <option value="1K">1K</option>
                <option value="2K">2K</option>
                <option value="4K">4K</option>
              </select>
            )}
          </div>

          {/* 控制栏：第二行 - 温度滑块 + 提交按钮 */}
          <div className="flex items-center gap-2 flex-wrap max-md:flex-col max-md:items-stretch">
            <div className="flex items-center gap-3 flex-1 min-w-[220px] max-w-[420px] max-md:w-full">
              <span className="text-sm max-md:text-xs text-white/80 whitespace-nowrap px-2 py-1 rounded-xl bg-white/10 border border-white/15">{t('home.temp', 'Temp')}</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer disabled:cursor-not-allowed max-w-[260px]"
                style={{
                  background: `linear-gradient(to right, #60a5fa 0%, #60a5fa ${temperature * 100}%, rgba(255,255,255,0.1) ${temperature * 100}%, rgba(255,255,255,0.1) 100%)`
                }}
                disabled={loading || !isImageMode}
              />
              <div className="w-12 h-10 rounded-2xl bg-white/[12%] border border-white/20 flex items-center justify-center text-sm max-md:text-xs text-white font-mono">
                {temperature.toFixed(1)}
              </div>
            </div>

            {/* 提交按钮 */}
            <div className="max-md:w-full ml-auto self-end flex-shrink-0">
              <button
                type="submit"
                disabled={loading || !message.trim()}
                className="rounded-2xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 px-6 py-2.5 max-md:px-5 max-md:py-2 text-base max-md:text-sm font-bold text-white transition hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.97]"
              >
                {loading ? t('home.processing', '处理中...') : t('home.submit')}
              </button>
            </div>
          </div>

        </form>
      </div>
    </div>
  )
}
