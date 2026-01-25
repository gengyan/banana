import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import UserLevelBadge from './UserLevelBadge'
import packageJson from '../../package.json'

function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const menuRef = useRef(null)

  const isActive = (path) => {
    if (path === '/projects') {
      return location.pathname === '/projects' || location.pathname.startsWith('/projects/')
    }
    return location.pathname === path
  }

  const handleLanguageChange = () => {
    const newLang = i18n.language === 'zh' ? 'en' : 'zh'
    i18n.changeLanguage(newLang)
  }

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsMenuOpen(false)
      }
    }

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isMenuOpen])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
    setIsMenuOpen(false)
  }

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen)
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#0e0e0e]">
      {/* 导航栏 */}
      <nav className="fixed inset-x-0 top-0 z-50 flex h-16 w-full shrink-0 items-center px-4 transition">
        <Link to="/" className="mr-6 flex items-center gap-2 max-md:mr-4">
          <img src="/icon.png" alt={t('app.name')} className="h-10 w-10 object-contain" />
          <span className="text-2xl font-bold text-white">{t('app.name')}</span>
        </Link>
        
        <div className="ml-auto flex items-center gap-x-3">
          {/* 语言切换按钮 */}
          <button
            onClick={handleLanguageChange}
            className="inline-flex items-center justify-center gap-1 whitespace-nowrap text-sm h-9 px-3 rounded-xl border-none bg-white/10 hover:bg-white/15 active:scale-[0.97] transition font-medium text-white"
            title={t('nav.language')}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
            </svg>
            <span>{i18n.language === 'zh' ? 'EN' : '中文'}</span>
          </button>
          
          {/* 用户信息 */}
          {user && (
            <div className="relative" ref={menuRef}>
              <button
                onClick={toggleMenu}
                className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm h-9 px-3 rounded-xl border-none bg-white/10 hover:bg-white/15 active:scale-[0.97] transition font-medium text-white"
              >
                <div className="relative w-7 h-7 rounded-full overflow-visible bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
                  {user.avatar ? (
                    <img src={user.avatar} alt={user.nickname} className="w-full h-full object-cover rounded-full" />
                  ) : (
                    <span className="text-xs text-white">{user.nickname?.charAt(0)?.toUpperCase() || 'U'}</span>
                  )}
                  {/* 用户等级皇冠 - 戴在头像顶部 */}
                  {user.level && user.level !== 'normal' && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10">
                      <UserLevelBadge level={user.level} size={20} />
                    </div>
                  )}
                </div>
                <span className="max-w-[100px] truncate">{user.nickname || user.account}</span>
                <svg 
                  className={`w-4 h-4 transition-transform ${isMenuOpen ? 'rotate-180' : ''}`} 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              {/* 下拉菜单 */}
              {isMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 rounded-xl bg-white/10 backdrop-blur-lg border border-white/20 shadow-lg overflow-hidden z-50">
                  <Link
                    to="/profile"
                    onClick={() => setIsMenuOpen(false)}
                    className="block px-4 py-3 text-sm text-white hover:bg-white/15 transition"
                  >
                    {t('nav.profile', '个人资料')}
                  </Link>
                  {/* 管理员菜单 - 仅 manager 用户可见 */}
                  {user && user.account === 'manager' && (
                    <Link
                      to="/admin/users"
                      onClick={() => setIsMenuOpen(false)}
                      className="block px-4 py-3 text-sm text-white hover:bg-white/15 transition border-t border-white/10"
                    >
                      {t('nav.userManagement', '用户管理')}
                    </Link>
                  )}
                  <Link
                    to="/help"
                    onClick={() => setIsMenuOpen(false)}
                    className="block px-4 py-3 text-sm text-white hover:bg-white/15 transition border-t border-white/10"
                  >
                    {t('nav.manual', '使用手册')}
                  </Link>
                  <Link
                    to="/price"
                    onClick={() => setIsMenuOpen(false)}
                    className="block px-4 py-3 text-sm text-white hover:bg-white/15 transition border-t border-white/10"
                  >
                    {t('nav.purchase', '立即购买')}
                  </Link>
                  <Link
                    to="/customer-service"
                    onClick={() => setIsMenuOpen(false)}
                    className="block px-4 py-3 text-sm text-white hover:bg-white/15 transition border-t border-white/10"
                  >
                    {t('nav.customerService', '客户服务')}
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-3 text-sm text-white hover:bg-white/15 transition border-t border-white/10"
                  >
                    {t('nav.logout')}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </nav>

      {/* 侧边栏 - 桌面端 */}
      <div className="fixed left-6 top-1/2 z-50 hidden md:flex -translate-y-1/2 flex-col gap-y-4">
        <div className="flex flex-col items-center gap-y-4 rounded-3xl bg-white/10 p-2">
          <Link
            to="/"
            className={`relative size-10 rounded-xl p-2 active:scale-[0.97] transition ${
              isActive('/') ? 'bg-[#D9D9D9]' : 'bg-transparent hover:bg-[#D9D9D9]'
            }`}
            title="灵感发现"
          >
            <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          </Link>
          
          <Link
            to="/projects"
            className={`relative size-10 rounded-xl p-2 active:scale-[0.97] transition ${
              isActive('/projects') ? 'bg-[#D9D9D9]' : 'bg-transparent hover:bg-[#D9D9D9]'
            }`}
            title="项目库"
          >
            <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </Link>
        </div>
      </div>

      {/* 底部导航栏 - 移动端 */}
      <div className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden items-center justify-center gap-x-4 px-4 py-3 bg-[#0e0e0e]/95 backdrop-blur-lg border-t border-white/10">
        <Link
          to="/"
          className={`relative size-12 rounded-2xl p-2.5 active:scale-[0.95] transition flex items-center justify-center ${
            isActive('/') ? 'bg-[#D9D9D9]' : 'bg-white/10'
          }`}
          title="灵感发现"
        >
          <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
        </Link>
        
        <Link
          to="/projects"
          className={`relative size-12 rounded-2xl p-2.5 active:scale-[0.95] transition flex items-center justify-center ${
            isActive('/projects') ? 'bg-[#D9D9D9]' : 'bg-white/10'
          }`}
          title="项目库"
        >
          <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </Link>
      </div>

      {/* 主内容区 */}
      <main className="relative flex flex-1 flex-col items-center justify-start px-12 pt-28 max-md:px-4 max-md:pt-24 max-md:pb-28">
        <div className="gradient-glow"></div>
        <div className="light-ray light-ray-1"></div>
        <div className="light-ray light-ray-2"></div>
        <div className="relative z-10 w-full">
          <Outlet />
        </div>
      </main>

      {/* 版本号 - 右下角 */}
      <div className="fixed bottom-14 right-4 z-[100] text-white/40 text-xs font-mono max-md:bottom-26 max-md:right-2">
        v{packageJson.version}
      </div>
    </div>
  )
}

export default Layout

