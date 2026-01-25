import { useTranslation } from 'react-i18next'

/**
 * 老照片修复组件
 */
export default function OldPhotoRestore({
  oldPhotoFile,
  oldPhotoPreview,
  oldPhotoPrompt,
  oldPhotoLoading,
  restoredImage,
  onFileChange,
  onPromptChange,
  onSubmit,
  onDownload,
  onClearFile,
  onDrop,
  onDragOver
}) {
  const { t } = useTranslation()

  return (
    <div className="relative z-10 mt-[60px] flex flex-col items-center justify-center max-md:mt-[5%] px-4">
      <div className="mb-4 text-center max-md:mb-2">
        <img 
          src="/icon.png" 
          alt={t('app.name')} 
          className="mx-auto mb-3 h-[269px] w-[269px] max-md:h-[120px] max-md:w-[120px] max-md:mb-2 object-contain" 
        />
        <h1 className="text-[46px] font-medium text-white max-md:text-2xl max-md:mb-2 mb-4">
          老照片修复
        </h1>
      </div>

      <div className="w-full max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6 max-md:gap-4">
        {/* 左侧：图片上传区域 */}
        <div className="lg:col-span-1">
          <div className="bg-gray-900/50 backdrop-blur-lg rounded-2xl border border-gray-700/50 p-6 max-md:p-4">
            <label className="block text-sm font-medium text-gray-300 mb-3">上传老照片</label>
            <div
              onDrop={onDrop}
              onDragOver={onDragOver}
              className="border-2 border-dashed border-gray-600 rounded-xl p-8 text-center cursor-pointer hover:border-gray-500 transition-colors bg-gray-800/30"
            >
              <input
                type="file"
                accept="image/*"
                onChange={onFileChange}
                className="hidden"
                id="old-photo-upload"
                disabled={oldPhotoLoading}
              />
              <label htmlFor="old-photo-upload" className="cursor-pointer">
                {oldPhotoPreview ? (
                  <div className="relative">
                    <img
                      src={oldPhotoPreview}
                      alt="预览"
                      className="w-full h-auto rounded-lg max-h-96 object-contain"
                    />
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onClearFile && onClearFile()
                      }}
                      className="absolute top-2 right-2 bg-red-600 hover:bg-red-700 text-white rounded-full w-8 h-8 flex items-center justify-center"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ) : (
                  <div className="py-12">
                    <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <p className="text-gray-400 text-sm">拖拽图片到此处或点击上传</p>
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* 文本输入框 */}
          <div className="mt-6 bg-gray-900/50 backdrop-blur-lg rounded-2xl border border-gray-700/50 p-6 max-md:p-4">
            <label className="block text-sm font-medium text-gray-300 mb-3">优化指令</label>
            <textarea
              value={oldPhotoPrompt}
              onChange={(e) => onPromptChange && onPromptChange(e.target.value)}
              placeholder="high quality, sharp focus, clean skin"
              className="w-full h-32 bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              disabled={oldPhotoLoading}
            />
          </div>

          {/* 修复按钮 */}
          <button
            onClick={onSubmit}
            disabled={!oldPhotoFile || oldPhotoLoading}
            className="mt-6 w-full bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-4 px-6 rounded-xl transition active:scale-[0.97]"
          >
            {oldPhotoLoading ? '修复中...' : '开始修复'}
          </button>
        </div>

        {/* 右侧：修复结果显示 */}
        <div className="lg:col-span-2">
          <div className="bg-gray-900/50 backdrop-blur-lg rounded-2xl border border-gray-700/50 p-6 max-md:p-4 h-full">
            <label className="block text-sm font-medium text-gray-300 mb-3">修复结果</label>
            {restoredImage ? (
              <div>
                <img
                  src={restoredImage}
                  alt="修复后"
                  className="w-full h-auto rounded-lg mb-4"
                />
                <button
                  onClick={onDownload}
                  className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-xl transition active:scale-[0.97]"
                >
                  下载修复后的图片
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-center h-96 bg-gray-800/30 rounded-lg">
                <p className="text-gray-400">
                  {oldPhotoLoading ? '修复中，请稍候...' : '修复结果将显示在这里'}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
