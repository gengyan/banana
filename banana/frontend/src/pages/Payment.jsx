import { useState } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'
import { paymentAPI } from '../api'

function Payment() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const plan = searchParams.get('plan') || '基础版'
  const price = searchParams.get('price') || '29'
  
  const [paymentMethod, setPaymentMethod] = useState('alipay_qrcode')
  const [account, setAccount] = useState('')
  const [isValidated, setIsValidated] = useState(false)
  const [validationError, setValidationError] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [payUrl, setPayUrl] = useState('')
  
  // 订单号输入步骤
  const [showOrderInput, setShowOrderInput] = useState(false)
  const [orderNumber, setOrderNumber] = useState('')
  const [submittingOrder, setSubmittingOrder] = useState(false)

  // 实时校验账号（邮箱或手机号）
  const validateAccount = (value) => {
    setValidationError('')
    setIsValidated(false)
    
    if (!value.trim()) {
      setIsValidated(false)
      return false
    }
    
    const trimmedValue = value.trim()
    
    // 邮箱格式校验
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    // 手机号格式校验（支持11位中国大陆手机号）
    const phoneRegex = /^1[3-9]\d{9}$/
    
    if (emailRegex.test(trimmedValue) || phoneRegex.test(trimmedValue)) {
      setIsValidated(true)
      setValidationError('')
      setError('')
      return true
    } else {
      setIsValidated(false)
      return false
    }
  }

  // 处理账号输入变化
  const handleAccountChange = (e) => {
    const value = e.target.value
    setAccount(value)
    validateAccount(value)
  }

  // 处理支付完成（显示订单号输入步骤）
  const handlePaymentComplete = () => {
    setShowOrderInput(true)
  }
  
  // 提交订单号
  const handleSubmitOrder = async (e) => {
    e.preventDefault()
    
    if (!orderNumber.trim()) {
      setError('请输入支付订单号')
      return
    }
    
    setSubmittingOrder(true)
    setError('')
    
    try {
      // 调用后端API提交订单
      const result = await paymentAPI.submitOrder(plan, price, account, orderNumber.trim())
      
      if (result.success) {
        // 跳转到成功页面
        navigate('/payment/success', {
          state: {
            plan,
            price,
            orderNumber: orderNumber.trim(),
          },
        })
      } else {
        setError(result.error || '订单提交失败，请稍后重试')
      }
    } catch (err) {
      console.error('提交订单失败:', err)
      setError('订单提交失败，请稍后重试')
    } finally {
      setSubmittingOrder(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // 扫码支付不需要调用后端接口
    if (paymentMethod === 'alipay_qrcode') {
      // 如果是扫码支付，且未校验通过，则提示校验
      if (!isValidated) {
        setError('请先输入有效的支付宝账号（邮箱或手机号）')
        return
      }
      setError('')
      setSuccessMessage('请使用支付宝扫描上方二维码完成支付')
      return
    }
    
    if (paymentMethod !== 'alipay_online') {
      setError('目前仅支持支付宝支付')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      console.log('开始创建支付订单:', { plan, price })
      // 调用后端接口创建支付订单
      const result = await paymentAPI.createPayment(plan, price)
      console.log('支付接口返回结果:', result)
      
      if (result && result.success) {
        // 优先使用表单方式（按照支付宝官方文档推荐）
        if (result.pay_form) {
          console.log('使用支付表单方式')
          
          // 同时保存pay_url作为备用
          if (result.pay_url) {
            setPayUrl(result.pay_url)
          }
          
          setLoading(false)
          setSuccessMessage('正在跳转到支付宝支付页面...如果页面空白，请使用下方的支付链接')
          
          // 创建临时div，插入表单并自动提交
          const div = document.createElement('div')
          div.style.display = 'none'  // 隐藏div
          div.innerHTML = result.pay_form
          document.body.appendChild(div)
          
          // 等待DOM更新后手动提交表单（React不执行innerHTML中的script）
          setTimeout(() => {
            const form = document.forms['alipaysubmit']
            if (form) {
              console.log('找到支付表单，开始提交...')
              // 尝试在新窗口中提交表单
              try {
                form.target = '_blank'
                form.submit()  // 手动提交表单
              } catch (e) {
                console.error('表单提交失败:', e)
                setError('表单提交失败，请使用下方的支付链接')
              }
            } else {
              console.error('未找到支付表单')
              setError('支付表单提交失败，请使用下方的支付链接')
            }
          }, 100)
        } else if (result.pay_url) {
          // 备用方式：使用URL跳转
          console.log('使用支付URL方式:', result.pay_url)
          setPayUrl(result.pay_url)
          
          // 在新窗口中打开支付宝支付页面
          const payWindow = window.open(result.pay_url, '_blank')
          if (!payWindow) {
            // 如果弹窗被阻止，提示用户手动打开
            setError('弹窗被阻止，请允许弹窗后重试，或使用下方的支付链接')
            setLoading(false)
            return
          }
          
          // 支付窗口已打开，可以关闭加载状态
          setLoading(false)
          setSuccessMessage('支付页面已在新窗口打开。如果页面无法加载，请使用下方的支付链接')
        } else {
          setError('支付数据格式错误')
          setLoading(false)
        }
      } else {
        console.error('支付接口返回错误:', result)
        setError(result?.error_message || '创建支付订单失败，请稍后重试')
        setLoading(false)
      }
    } catch (error) {
      console.error('支付错误:', error)
      console.error('错误详情:', error.response?.data || error.message)
      setError(error.response?.data?.error_message || error.message || '支付失败，请稍后重试')
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto mt-20 max-w-2xl px-4 py-8">
      <div className="mb-8">
        <Link to="/price" className="text-white/60 hover:text-white">
          ← 返回价格页面
        </Link>
      </div>

      <div className="rounded-3xl bg-white/[8%] p-8 backdrop-blur-sm">
        <h1 className="mb-6 text-3xl font-bold text-white">确认订单</h1>

        <div className="mb-8 rounded-xl bg-white/[4%] p-6">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-white/70">方案</span>
            <span className="text-xl font-bold text-white">{plan}</span>
          </div>
          <div className="mb-4 flex items-center justify-between">
            <span className="text-white/70">周期</span>
            <span className="text-white">1个月</span>
          </div>
          <div className="flex items-center justify-between border-t border-white/10 pt-4">
            <span className="text-xl font-bold text-white">总计</span>
            <span className="text-3xl font-bold text-white">¥{price}</span>
          </div>
        </div>

        {/* 账号输入框 */}
        <div className="space-y-4 rounded-xl bg-white/[4%] p-6 mb-6">
          <div>
            <label className="mb-2 block text-sm font-medium text-white/70">
              支付宝账号 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={account}
              onChange={handleAccountChange}
              placeholder="请输入支付宝账号（邮箱或手机号）"
              className="w-full rounded-xl border-none bg-white/[12%] px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-white/20"
            />
            <p className="mt-2 text-xs text-white/50">
              ⚠️ 注意：此处输入的必须是您的支付宝账号（邮箱或手机号），否则无法完成支付校验
            </p>
          </div>

          {validationError && (
            <div className="rounded-xl bg-red-500/20 border border-red-500/50 p-3 text-red-400 text-sm">
              {validationError}
            </div>
          )}
        </div>

        {/* 扫码支付二维码显示（实时校验通过后自动显示） */}
        {isValidated && (
          <div className="rounded-xl bg-white/[4%] p-6 text-center mb-6">
            <div className="mb-4 flex justify-center">
              <div className="rounded-xl bg-white p-4 shadow-lg">
                <img
                  src="/alipay.jpg"
                  alt="支付宝收款二维码"
                  className="h-64 w-64 object-contain"
                  onError={(e) => {
                    e.target.style.display = 'none'
                    e.target.parentElement.innerHTML = '<div class="text-red-400 p-8">二维码图片未找到，请检查 /alipay.jpg 文件</div>'
                  }}
                />
              </div>
            </div>
            
            <div className="mb-6 rounded-lg bg-white/[8%] p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-white/70">订单金额</span>
                <span className="text-2xl font-bold text-white">¥{price}</span>
              </div>
              <div className="mt-3 border-t border-white/10 pt-3 text-left">
                <p className="text-xs text-white/60">支付宝账号：{account}</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={handlePaymentComplete}
                className="flex-1 rounded-xl bg-gradient-to-r from-green-500 to-emerald-500 px-6 py-3 text-lg font-bold text-white transition hover:from-green-600 hover:to-emerald-600 active:scale-[0.97]"
              >
                完成支付
              </button>
              <Link
                to="/price"
                className="flex-1 rounded-xl bg-white/10 px-6 py-3 text-lg font-bold text-white text-center transition hover:bg-white/15 active:scale-[0.97]"
              >
                返回
              </Link>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-xl bg-red-500/20 border border-red-500/50 p-4 text-red-400 text-sm mb-4">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="rounded-xl bg-green-500/20 border border-green-500/50 p-4 text-green-400 text-sm mb-4">
            {successMessage}
          </div>
        )}

        {/* 订单号输入步骤 */}
        {showOrderInput && (
          <div className="mt-6 rounded-xl bg-white/[4%] p-6 border border-white/10">
            <div className="mb-4 flex justify-center">
              <img
                src="/ordernum.jpg"
                alt="订单号示例"
                className="max-w-full h-auto rounded-lg"
                onError={(e) => {
                  e.target.style.display = 'none'
                }}
              />
            </div>
            
            <form onSubmit={handleSubmitOrder} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">
                  支付订单号 <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={orderNumber}
                  onChange={(e) => setOrderNumber(e.target.value)}
                  placeholder="请输入支付订单号"
                  className="w-full rounded-xl border-none bg-white/[12%] px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-white/20"
                  required
                />
              </div>

              {error && (
                <div className="rounded-xl bg-red-500/20 border border-red-500/50 p-4 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submittingOrder || !orderNumber.trim()}
                className="w-full rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 px-6 py-3 text-lg font-bold text-white transition hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submittingOrder ? '提交中...' : '完成'}
              </button>
            </form>
          </div>
        )}

        {!showOrderInput && (
          <p className="mt-6 text-center text-sm text-white/40">
            点击确认支付即表示您同意我们的服务条款和隐私政策
          </p>
        )}
      </div>
    </div>
  )
}

export default Payment
