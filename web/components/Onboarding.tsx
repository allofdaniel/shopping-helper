'use client'

import { useState, useEffect } from 'react'
import { ShoppingCart, Search, Heart, MapPin, X, ChevronRight, ChevronLeft, Sparkles } from 'lucide-react'

interface OnboardingProps {
  onComplete: () => void
}

const ONBOARDING_STEPS = [
  {
    icon: ShoppingCart,
    title: '유튜버 추천 꿀템 모음',
    description: '다이소, 코스트코, 이케아 등\n오프라인 매장 꿀템을 한눈에!',
    color: 'from-orange-400 to-red-500',
  },
  {
    icon: Search,
    title: '쉬운 상품 검색',
    description: '상품명, 상품코드로 빠르게 검색\n카테고리별 필터링도 가능해요',
    color: 'from-blue-400 to-indigo-500',
  },
  {
    icon: Heart,
    title: '장바구니에 담기',
    description: '마음에 드는 상품은 찜하고\n매장 방문 시 체크리스트로 활용!',
    color: 'from-pink-400 to-rose-500',
  },
  {
    icon: MapPin,
    title: '오프라인 매장 정보',
    description: '근처 매장 위치와 연락처\n바로 확인하고 방문하세요',
    color: 'from-green-400 to-emerald-500',
  },
]

export function Onboarding({ onComplete }: OnboardingProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [isVisible, setIsVisible] = useState(true)

  const handleNext = () => {
    if (currentStep < ONBOARDING_STEPS.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleComplete()
    }
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleComplete = () => {
    setIsVisible(false)
    localStorage.setItem('onboarding_completed', 'true')
    setTimeout(() => onComplete(), 300)
  }

  const handleSkip = () => {
    handleComplete()
  }

  if (!isVisible) return null

  const step = ONBOARDING_STEPS[currentStep]
  const Icon = step.icon

  return (
    <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center p-4">
      <div
        className={`bg-white dark:bg-gray-900 rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl
                   transition-all duration-300 ${isVisible ? 'scale-100 opacity-100' : 'scale-95 opacity-0'}`}
      >
        {/* Skip button */}
        <div className="flex justify-end p-3">
          <button
            onClick={handleSkip}
            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex items-center gap-1"
          >
            건너뛰기
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 pb-6">
          {/* Icon */}
          <div className={`w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br ${step.color}
                         flex items-center justify-center mb-6 shadow-lg`}>
            <Icon className="w-10 h-10 text-white" />
          </div>

          {/* Title */}
          <h2 className="text-xl font-bold text-center text-gray-900 dark:text-white mb-3">
            {step.title}
          </h2>

          {/* Description */}
          <p className="text-sm text-center text-gray-500 dark:text-gray-400 whitespace-pre-line leading-relaxed">
            {step.description}
          </p>

          {/* Progress dots */}
          <div className="flex justify-center gap-2 mt-6 mb-6">
            {ONBOARDING_STEPS.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentStep(index)}
                className={`w-2 h-2 rounded-full transition-all duration-300
                           ${index === currentStep
                             ? 'w-6 bg-orange-500'
                             : 'bg-gray-300 dark:bg-gray-600'}`}
              />
            ))}
          </div>

          {/* Navigation buttons */}
          <div className="flex gap-3">
            {currentStep > 0 && (
              <button
                onClick={handlePrev}
                className="flex-1 py-3 rounded-xl border border-gray-200 dark:border-gray-700
                          text-gray-600 dark:text-gray-400 font-medium text-sm
                          hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors
                          flex items-center justify-center gap-1"
              >
                <ChevronLeft className="w-4 h-4" />
                이전
              </button>
            )}
            <button
              onClick={handleNext}
              className={`flex-1 py-3 rounded-xl bg-gradient-to-r ${step.color}
                        text-white font-bold text-sm shadow-lg
                        hover:shadow-xl transition-all
                        flex items-center justify-center gap-1`}
            >
              {currentStep === ONBOARDING_STEPS.length - 1 ? (
                <>
                  <Sparkles className="w-4 h-4" />
                  시작하기
                </>
              ) : (
                <>
                  다음
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Hook to manage onboarding state
export function useOnboarding() {
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    const completed = localStorage.getItem('onboarding_completed')
    if (!completed) {
      setShowOnboarding(true)
    }
    setIsLoaded(true)
  }, [])

  const completeOnboarding = () => {
    setShowOnboarding(false)
  }

  const resetOnboarding = () => {
    localStorage.removeItem('onboarding_completed')
    setShowOnboarding(true)
  }

  return { showOnboarding, isLoaded, completeOnboarding, resetOnboarding }
}
