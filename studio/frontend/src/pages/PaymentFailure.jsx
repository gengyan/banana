import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

function PaymentFailure() {
  const [searchParams] = useSearchParams()
  const [orderInfo, setOrderInfo] = useState(null)
  const [failureReason, setFailureReason] = useState('')
  
  // 从URL参数获取订单信息和失败原因（支付宝回调时会带参数）
  useEffect(() => {
    const outTradeNo = searchParams.get('out_trade_no')
    const tradeNo = searchParams.get('trade_no')
    const totalAmount = searchParams.get('total_amount')
    
    // 可能的错误原因参数
    const errorMsg = searchParams.get('error_message') || searchParams.get('error_msg')
    const errorCode = searchParams.get('error_code')
    
    if (outTradeNo) {
      setOrderInfo({
        orderId: outTradeNo,
        tradeNo: tradeNo || '',
        amount: totalAmount || ''
      })
    }
    
    // 解析失败原因
    if (errorMsg) {
      setFailureReason(errorMsg)
    } else if (errorCode) {
      // 根据错误代码显示友好提示
      const reasonMap = {
        'USER_CANCEL': '用户取消支付',
        'SYSTEM_ERROR': '系统错误，请稍后重试',
        'PAYMENT_TIMEOUT': '支付超时，请重新支付',
        'INSUFFICIENT_BALANCE': '账户余额不足',
        'CARD_LIMIT': '银行卡支付限额',
        'NETWORK_ERROR': '网络错误，请检查网络连接',
      }
      setFailureReason(reasonMap[errorCode] || `支付失败（错误代码：${errorCode}）`)
    } else {
      setFailureReason('支付未完成或已取消')
    }
  }, [searchParams])

  return (
    <div className="container mx-auto mt-20 max-w-2xl px-4 py-8">
      <div className="rounded-3xl bg-white/[8%] p-8 backdrop-blur-sm text-center">
        {/* 失败图标 */}
        <div className="mb-6 flex justify-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-red-500/20">
            <svg
              className="h-12 w-12 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
        </div>

        {/* 标题 */}
        <h1 className="mb-4 text-3xl font-bold text-white">支付失败</h1>
        <p className="mb-8 text-lg text-white/70">
          很抱歉，您的支付未完成
        </p>

        {/* 失败原因 */}
        {failureReason && (
          <div className="mb-8 rounded-xl bg-red-500/20 border border-red-500/50 p-6">
            <div className="mb-2 flex items-center justify-center gap-2">
              <svg
                className="h-5 w-5 text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <h2 className="text-xl font-semibold text-red-400">失败原因</h2>
            </div>
            <p className="text-white/90">{failureReason}</p>
          </div>
        )}

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
                  <span className="text-white/70">订单金额</span>
                  <span className="text-xl font-bold text-white">¥{orderInfo.amount}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
          <Link
            to="/price"
            className="rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 px-8 py-3 text-center font-bold text-white transition hover:from-purple-600 hover:via-pink-600 hover:to-blue-600 active:scale-[0.97]"
          >
            重新支付
          </Link>
          <Link
            to="/"
            className="rounded-xl bg-white/10 px-8 py-3 text-center font-bold text-white transition hover:bg-white/15 active:scale-[0.97]"
          >
            返回首页
          </Link>
        </div>

        {/* 提示信息 */}
        <div className="mt-8 rounded-xl bg-blue-500/20 border border-blue-500/50 p-4">
          <p className="text-sm text-blue-400">
            💡 提示：如果多次支付失败，请检查账户余额或联系客服
          </p>
        </div>
      </div>
    </div>
  )
}

export default PaymentFailure

