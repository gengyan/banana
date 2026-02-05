function HowToUse() {
  // 直接使用 iframe 加载提取好的 HTML 文件
  // HTML 文件已经提取到 public/manual/index.html

  return (
    <div className="container mx-auto mt-20 max-w-7xl px-4 py-8">
      <div className="mb-6">
        <h1 className="mb-2 text-4xl font-bold text-white">使用手册</h1>
        <p className="text-white/60">果捷 AI 完整使用指南</p>
      </div>
      
      <div className="rounded-3xl bg-white/[8%] p-4 overflow-hidden">
        <iframe
          src="/manual/index.html"
          className="w-full h-[calc(100vh-250px)] min-h-[800px] border-0 rounded-xl bg-white"
          title="使用手册"
          sandbox="allow-same-origin allow-scripts allow-forms"
        />
        <div className="mt-4 text-center">
          <a
            href="/manual/index.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 text-white font-bold hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 transition"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            在新窗口打开手册
          </a>
        </div>
      </div>
    </div>
  )
}

export default HowToUse

