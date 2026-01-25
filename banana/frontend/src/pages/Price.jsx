import { useState } from 'react'
import { Link } from 'react-router-dom'

function Price() {
  const [selectedPlan, setSelectedPlan] = useState(1) // 默认选中专业版（索引1）
  
  const plans = [
    {
      name: '基础版',
      price: '29',
      period: '月',
      features: [
        '100次图片生成',
        '基础修图功能',
        '标准分辨率输出',
        '社区支持',
      ],
      popular: false,
    },
    {
      name: '专业版',
      price: '99',
      period: '月',
      features: [
        '500次图片生成',
        '高级修图功能',
        '高清分辨率输出',
        '优先技术支持',
        '商业授权',
      ],
      popular: true,
    },
    {
      name: '企业版',
      price: '299',
      period: '月',
      features: [
        '无限次图片生成',
        '全部功能',
        '4K分辨率输出',
        '专属技术支持',
        '商业授权',
        'API访问',
      ],
      popular: false,
    },
  ]

  return (
    <div className="container mx-auto mt-20 max-w-6xl px-4 py-8">
      <div className="mb-12 text-center">
        <h1 className="mb-4 text-5xl font-bold text-white">选择适合您的方案</h1>
        <p className="text-xl text-white/60">灵活的价格，满足不同需求</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan, index) => (
          <div
            key={index}
            onClick={() => setSelectedPlan(index)}
            className={`relative cursor-pointer rounded-3xl bg-white/[8%] p-8 backdrop-blur-sm transition-all ${
              selectedPlan === index
                ? 'border-2 border-blue-500 scale-105'
                : 'border border-white/10'
            }`}
          >
            {selectedPlan === index && (
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 px-4 py-1 text-sm font-bold text-white">
                已选择
              </div>
            )}

            <div className="mb-6">
              <h3 className="mb-2 text-2xl font-bold text-white">{plan.name}</h3>
              <div className="flex items-baseline">
                <span className="text-5xl font-bold text-white">¥{plan.price}</span>
                <span className="ml-2 text-white/60">/{plan.period}</span>
              </div>
            </div>

            <ul className="mb-8 space-y-3">
              {plan.features.map((feature, idx) => (
                <li key={idx} className="flex items-start text-white/70">
                  <svg
                    className="mr-2 mt-1 size-5 shrink-0 text-green-500"
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
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <Link
              to={`/payment?plan=${plan.name}&price=${plan.price}`}
              onClick={(e) => e.stopPropagation()}
              className={`block w-full rounded-xl px-6 py-3 text-center font-bold transition ${
                selectedPlan === index
                  ? 'bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 text-white hover:from-purple-600 hover:via-pink-600 hover:to-blue-600'
                  : 'bg-white/10 text-white hover:bg-white/15'
              } active:scale-[0.97]`}
            >
              立即购买
            </Link>
          </div>
        ))}
      </div>

      <div className="mt-12 rounded-3xl bg-white/[8%] p-8 text-center">
        <h2 className="mb-4 text-2xl font-bold text-white">需要定制方案？</h2>
        <p className="mb-6 text-white/70">联系我们获取企业定制方案和专属服务</p>
        <button className="rounded-xl bg-white/10 px-6 py-3 font-bold text-white hover:bg-white/15 transition">
          联系销售
        </button>
      </div>
    </div>
  )
}

export default Price

