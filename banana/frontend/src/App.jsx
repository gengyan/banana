import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Home from './pages/Home'
import Help from './pages/Help'
import HowToUse from './pages/HowToUse'
import Working from './pages/Working'
import Price from './pages/Price'
import Payment from './pages/Payment'
import PaymentSuccess from './pages/PaymentSuccess'
import PaymentFailure from './pages/PaymentFailure'
import ProjectLibrary from './pages/ProjectLibrary'
import ProjectDetail from './pages/ProjectDetail'
import Profile from './pages/Profile'
import UserList from './pages/UserList'
import ManagerPage from './pages/ManagerPage'
import CustomerService from './pages/CustomerService'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

function AppRoutes() {
  const { isAuthenticated, loading } = useAuth()

  // 如果未登录且不在登录/注册页，重定向到登录页
  useEffect(() => {
    if (!loading && !isAuthenticated && !window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
      // 这个逻辑由路由守卫处理，这里只是备用
    }
  }, [isAuthenticated, loading])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Home />} />
        <Route path="help" element={<Help />} />
        <Route path="howtouse" element={<HowToUse />} />
        <Route path="working" element={<Working />} />
        <Route path="price" element={<Price />} />
        <Route path="payment" element={<Payment />} />
        <Route path="payment/success" element={<PaymentSuccess />} />
        <Route path="payment/failure" element={<PaymentFailure />} />
        <Route path="projects" element={<ProjectLibrary />} />
        <Route path="projects/:projectId" element={<ProjectDetail />} />
        <Route path="profile" element={<Profile />} />
        <Route path="userlist" element={<UserList />} />
        <Route path="admin/users" element={<ManagerPage />} />
        <Route path="customer-service" element={<CustomerService />} />
      </Route>
      {/* 保留 /manager 路由作为兼容（重定向到 /admin/users） */}
      <Route path="/manager" element={<Navigate to="/admin/users" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <Router>
      <AppRoutes />
    </Router>
  )
}

export default App

