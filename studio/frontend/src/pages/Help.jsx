function Help() {
  return (
    <div className="fixed inset-0 bg-white" style={{ top: '64px', zIndex: 10 }}>
      <iframe
        src="/help.html"
        className="w-full h-full border-0"
        title="使用帮助"
        style={{ height: 'calc(100vh - 64px)' }}
      />
    </div>
  )
}

export default Help

