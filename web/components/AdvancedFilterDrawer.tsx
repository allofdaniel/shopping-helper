'use client'

import { X, SlidersHorizontal, RotateCcw, Check, ChevronDown, Eye, MessageSquare, Link2 } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import type { FilterState } from '@/lib/useAdvancedFilters'
import { STORES } from '@/lib/types'

interface AdvancedFilterDrawerProps {
  isOpen: boolean
  onClose: () => void
  filters: FilterState
  onUpdateFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  onResetFilters: () => void
  activeFilterCount: number
  priceStats: { min: number; max: number; avg: number }
  viewStats: { min: number; max: number }
}

const PRICE_PRESETS = [
  { label: '전체', range: [0, 100000] as [number, number] },
  { label: '~1천원', range: [0, 1000] as [number, number] },
  { label: '~3천원', range: [0, 3000] as [number, number] },
  { label: '~5천원', range: [0, 5000] as [number, number] },
  { label: '~1만원', range: [0, 10000] as [number, number] },
  { label: '1~3만원', range: [10000, 30000] as [number, number] },
  { label: '3만원~', range: [30000, 100000] as [number, number] },
]

const VIEW_PRESETS = [
  { label: '전체', min: 0 },
  { label: '1만+', min: 10000 },
  { label: '10만+', min: 100000 },
  { label: '50만+', min: 500000 },
  { label: '100만+', min: 1000000 },
]

const DATE_PRESETS = [
  { key: 'all' as const, label: '전체 기간' },
  { key: 'week' as const, label: '이번 주' },
  { key: 'month' as const, label: '이번 달' },
  { key: '3months' as const, label: '최근 3개월' },
]

const CATEGORY_OPTIONS = [
  { key: 'kitchen', name: '주방', icon: '🍳' },
  { key: 'living', name: '생활', icon: '🏠' },
  { key: 'beauty', name: '뷰티', icon: '💄' },
  { key: 'interior', name: '인테리어', icon: '🪴' },
  { key: 'food', name: '식품', icon: '🍽️' },
  { key: 'digital', name: '디지털', icon: '📱' },
]

export function AdvancedFilterDrawer({
  isOpen,
  onClose,
  filters,
  onUpdateFilter,
  onResetFilters,
  activeFilterCount,
  priceStats,
  viewStats,
}: AdvancedFilterDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null)
  const [expandedSection, setExpandedSection] = useState<string | null>('price')

  // 바깥 클릭 감지
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  // ESC 키로 닫기
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
    }
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section)
  }

  const formatPrice = (price: number) => {
    if (price >= 10000) return `${Math.floor(price / 10000)}만원`
    if (price >= 1000) return `${Math.floor(price / 1000)}천원`
    return `${price}원`
  }

  const formatViews = (views: number) => {
    if (views >= 10000) return `${Math.floor(views / 10000)}만`
    if (views >= 1000) return `${Math.floor(views / 1000)}천`
    return `${views}`
  }

  if (!isOpen) return null

  return (
    <>
      {/* 배경 오버레이 */}
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 transition-opacity duration-300" />

      {/* 드로어 */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="filter-drawer-title"
        className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-white dark:bg-gray-900
                   shadow-2xl z-50 flex flex-col transform transition-transform duration-300
                   animate-slide-in-right"
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <SlidersHorizontal className="w-5 h-5 text-orange-500" aria-hidden="true" />
            <h2 id="filter-drawer-title" className="text-lg font-bold text-gray-900 dark:text-white">상세 필터</h2>
            {activeFilterCount > 0 && (
              <span className="px-2 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400
                             rounded-full text-xs font-medium">
                {activeFilterCount}개 적용중
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="필터 닫기"
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" aria-hidden="true" />
          </button>
        </div>

        {/* 필터 섹션들 */}
        <div className="flex-1 overflow-y-auto">
          {/* 가격대 필터 */}
          <div className="border-b border-gray-100 dark:border-gray-800">
            <button
              onClick={() => toggleSection('price')}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50"
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">💰</span>
                <span className="font-medium text-gray-800 dark:text-gray-200">가격대</span>
                {(filters.priceRange[0] > 0 || filters.priceRange[1] < 100000) && (
                  <span className="text-xs text-orange-500">
                    {formatPrice(filters.priceRange[0])} ~ {formatPrice(filters.priceRange[1])}
                  </span>
                )}
              </div>
              <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSection === 'price' ? 'rotate-180' : ''}`} />
            </button>

            {expandedSection === 'price' && (
              <div className="px-5 pb-4">
                <div className="flex flex-wrap gap-2">
                  {PRICE_PRESETS.map((preset) => (
                    <button
                      key={preset.label}
                      onClick={() => onUpdateFilter('priceRange', preset.range)}
                      className={`px-3 py-1.5 rounded-full text-sm transition-all
                                 ${filters.priceRange[0] === preset.range[0] && filters.priceRange[1] === preset.range[1]
                                   ? 'bg-orange-500 text-white shadow-md shadow-orange-500/30'
                                   : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                                 }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
                <p className="mt-3 text-xs text-gray-400">
                  평균 가격: {formatPrice(priceStats.avg)}
                </p>
              </div>
            )}
          </div>

          {/* 조회수 필터 */}
          <div className="border-b border-gray-100 dark:border-gray-800">
            <button
              onClick={() => toggleSection('views')}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50"
            >
              <div className="flex items-center gap-2">
                <Eye className="w-5 h-5 text-blue-500" />
                <span className="font-medium text-gray-800 dark:text-gray-200">영상 조회수</span>
                {filters.minViews > 0 && (
                  <span className="text-xs text-blue-500">
                    {formatViews(filters.minViews)}+ 이상
                  </span>
                )}
              </div>
              <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSection === 'views' ? 'rotate-180' : ''}`} />
            </button>

            {expandedSection === 'views' && (
              <div className="px-5 pb-4">
                <div className="flex flex-wrap gap-2">
                  {VIEW_PRESETS.map((preset) => (
                    <button
                      key={preset.label}
                      onClick={() => onUpdateFilter('minViews', preset.min)}
                      className={`px-3 py-1.5 rounded-full text-sm transition-all
                                 ${filters.minViews === preset.min
                                   ? 'bg-blue-500 text-white shadow-md shadow-blue-500/30'
                                   : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                                 }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 날짜 필터 */}
          <div className="border-b border-gray-100 dark:border-gray-800">
            <button
              onClick={() => toggleSection('date')}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50"
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">📅</span>
                <span className="font-medium text-gray-800 dark:text-gray-200">등록 기간</span>
                {filters.dateRange !== 'all' && (
                  <span className="text-xs text-purple-500">
                    {DATE_PRESETS.find(d => d.key === filters.dateRange)?.label}
                  </span>
                )}
              </div>
              <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSection === 'date' ? 'rotate-180' : ''}`} />
            </button>

            {expandedSection === 'date' && (
              <div className="px-5 pb-4">
                <div className="flex flex-wrap gap-2">
                  {DATE_PRESETS.map((preset) => (
                    <button
                      key={preset.key}
                      onClick={() => onUpdateFilter('dateRange', preset.key)}
                      className={`px-3 py-1.5 rounded-full text-sm transition-all
                                 ${filters.dateRange === preset.key
                                   ? 'bg-purple-500 text-white shadow-md shadow-purple-500/30'
                                   : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                                 }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 스토어 필터 */}
          <div className="border-b border-gray-100 dark:border-gray-800">
            <button
              onClick={() => toggleSection('stores')}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50"
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">🏪</span>
                <span className="font-medium text-gray-800 dark:text-gray-200">매장</span>
                {filters.stores.length > 0 && (
                  <span className="text-xs text-green-500">
                    {filters.stores.length}개 선택
                  </span>
                )}
              </div>
              <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSection === 'stores' ? 'rotate-180' : ''}`} />
            </button>

            {expandedSection === 'stores' && (
              <div className="px-5 pb-4">
                <div className="flex flex-wrap gap-2">
                  {Object.entries(STORES).map(([key, store]) => (
                    <button
                      key={key}
                      onClick={() => {
                        const newStores = filters.stores.includes(key)
                          ? filters.stores.filter(s => s !== key)
                          : [...filters.stores, key]
                        onUpdateFilter('stores', newStores)
                      }}
                      className={`px-3 py-1.5 rounded-full text-sm transition-all flex items-center gap-1.5
                                 ${filters.stores.includes(key)
                                   ? 'text-white shadow-md'
                                   : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                                 }`}
                      style={filters.stores.includes(key) ? { backgroundColor: store.color } : {}}
                    >
                      {store.icon} {store.name}
                      {filters.stores.includes(key) && <Check className="w-3.5 h-3.5" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 카테고리 필터 */}
          <div className="border-b border-gray-100 dark:border-gray-800">
            <button
              onClick={() => toggleSection('categories')}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50"
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">🏷️</span>
                <span className="font-medium text-gray-800 dark:text-gray-200">카테고리</span>
                {filters.categories.length > 0 && (
                  <span className="text-xs text-teal-500">
                    {filters.categories.length}개 선택
                  </span>
                )}
              </div>
              <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expandedSection === 'categories' ? 'rotate-180' : ''}`} />
            </button>

            {expandedSection === 'categories' && (
              <div className="px-5 pb-4">
                <div className="flex flex-wrap gap-2">
                  {CATEGORY_OPTIONS.map((cat) => (
                    <button
                      key={cat.key}
                      onClick={() => {
                        const newCategories = filters.categories.includes(cat.key)
                          ? filters.categories.filter(c => c !== cat.key)
                          : [...filters.categories, cat.key]
                        onUpdateFilter('categories', newCategories)
                      }}
                      className={`px-3 py-1.5 rounded-full text-sm transition-all flex items-center gap-1.5
                                 ${filters.categories.includes(cat.key)
                                   ? 'bg-teal-500 text-white shadow-md shadow-teal-500/30'
                                   : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                                 }`}
                    >
                      {cat.icon} {cat.name}
                      {filters.categories.includes(cat.key) && <Check className="w-3.5 h-3.5" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 추가 옵션 */}
          <div className="px-5 py-4 space-y-3">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">추가 조건</h3>

            <label className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <div className={`w-5 h-5 rounded flex items-center justify-center transition-all
                             ${filters.hasRecommendation
                               ? 'bg-orange-500 text-white'
                               : 'border-2 border-gray-300 dark:border-gray-600'
                             }`}>
                {filters.hasRecommendation && <Check className="w-3.5 h-3.5" />}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-orange-500" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">추천 코멘트 있는 상품</span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">유튜버의 추천 이유가 있는 상품만</p>
              </div>
              <input
                type="checkbox"
                checked={filters.hasRecommendation}
                onChange={(e) => onUpdateFilter('hasRecommendation', e.target.checked)}
                className="sr-only"
              />
            </label>

            <label className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              <div className={`w-5 h-5 rounded flex items-center justify-center transition-all
                             ${filters.hasOfficialMatch
                               ? 'bg-green-500 text-white'
                               : 'border-2 border-gray-300 dark:border-gray-600'
                             }`}>
                {filters.hasOfficialMatch && <Check className="w-3.5 h-3.5" />}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Link2 className="w-4 h-4 text-green-500" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">공식 매칭된 상품</span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">공식몰 링크가 확인된 상품만</p>
              </div>
              <input
                type="checkbox"
                checked={filters.hasOfficialMatch}
                onChange={(e) => onUpdateFilter('hasOfficialMatch', e.target.checked)}
                className="sr-only"
              />
            </label>
          </div>
        </div>

        {/* 푸터 버튼 */}
        <div className="flex gap-3 p-4 border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
          <button
            onClick={onResetFilters}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl
                     bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400
                     hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors font-medium"
          >
            <RotateCcw className="w-4 h-4" />
            초기화
          </button>
          <button
            onClick={onClose}
            className="flex-[2] py-3 rounded-xl bg-orange-500 text-white font-medium
                     hover:bg-orange-600 transition-colors shadow-lg shadow-orange-500/30"
          >
            {activeFilterCount > 0 ? `${activeFilterCount}개 필터 적용` : '적용하기'}
          </button>
        </div>
      </div>

      <style jsx global>{`
        @keyframes slide-in-right {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in-right {
          animation: slide-in-right 0.3s ease-out;
        }
      `}</style>
    </>
  )
}
