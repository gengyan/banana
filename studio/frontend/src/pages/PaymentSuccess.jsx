import { useEffect, useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'

function PaymentSuccess() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [orderInfo, setOrderInfo] = useState(null)
  
  // 从URL参数获取订单信息（支付宝回调时会带参数）
  useEffect(() => {
    const outTradeNo = searchParams.get('out_trade_no')
    const tradeNo = searchParams.get('trade_no')
    const totalAmount = searchParams.get('total_amount')
    
    if (outTradeNo) {
      setOrderInfo({
        orderId: outTradeNo,
        tradeNo: tradeNo || '',
        amount: totalAmount || ''
      })
    }
  }, [searchParams])

  return (
    <div className="container mx-auto mt-20 max-w-2xl px-4 py-8">
      <div className="rounded-3xl bg-white/[8%] p-8 backdrop-blur-sm text-center">
        {/* 成功图标 */}
        <div className="mb-6 flex justify-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-green-500/20">
            <svg
              className="h-12 w-12 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>

        {/* 标题 */}
        <h1 className="mb-4 text-3xl font-bold text-white">支付成功！</h1>
        <p className="mb-8 text-lg text-white/70">
          感谢您的支持，您的订单已成功支付
        </p>

        {/* 订单信息 */}
        {orderInfo && (
          <div className="mb-8 rounded-xl bg-white/[4%] p-6 text-left">
            <h2 className="mb-4 text-xl font-semibold text-white">订单信息</h2>
            <div className="space-y-3">
              {orderInfo.orderId && (
                <div className="flex items-center justify-between">
                  <span className="text-white/70">商户订单号</span>
                  <span className="font-mono text-sm text-white">{orderInfo.orderId}</span>
                </div>
              )}
              {orderInfo.tradeNo && (
                <div className="flex items-center justify-between">
                  <span className="text-white/70">支付宝交易号</span>
                  <span className="font-mono text-sm text-white">{orderInfo.tradeNo}</span>
                </div>
              )}
              {orderInfo.amount && (
                <div className="flex items-center justify-between border-t border-white/10 pt-3">
                  <span className="text-white/70">支付金额</span>
                  <span className="text-xl font-bold text-white">¥{orderInfo.amount}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
          <Link
            to="/"
            className="rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 px-8 py-3 text-center font-bold text-white transition hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 active:scale-[0.97]"
          >
            返回首页
          </Link>
          <Link
            to="/projects"
            className="rounded-xl bg-white/10 px-8 py-3 text-center font-bold text-white transition hover:bg-white/15 active:scale-[0.97]"
          >
            查看项目库
          </Link>
        </div>

        {/* 提示信息 */}
        <p className="mt-8 text-sm text-white/40">
          如有疑问，请联系客服
        </p>
      </div>
    </div>
  )
}

export default PaymentSuccess

