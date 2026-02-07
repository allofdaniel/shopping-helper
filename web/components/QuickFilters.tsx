'use client'

import { Scale, Grid3X3, LayoutGrid, List } from 'lucide-react'
import type { TranslationKey } from '@/lib/i18n'
import type { SortOption } from '@/lib/types'

// 필터 아이콘
const FILTER_ICONS: Record<string, string> = {
  all: '',
  popular: '',
  new: '',
  recommended: '',
  favorites: '',
  priceLow: '',
  priceHigh: '',
  salesCount: '',
  reviewCount: '',
}

export type ViewMode = 'large' | 'small' | 'list'

interface QuickFiltersProps {
  sortBy: SortOption
  setSortBy: (sort: SortOption) => void
  showWishlistOnly: boolean
  setShowWishlistOnly: (show: boolean) => void
  wishlistCount: number
  compareCount: number
  showComparePanel: boolean
  setShowComparePanel: (show: boolean) => void
  onResetAll: () => void
  t: (key: TranslationKey) => string
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
}

export function QuickFilters({
  sortBy,
  setSortBy,
  showWishlistOnly,
  setShowWishlistOnly,
  wishlistCount,
  compareCount,
  showComparePanel,
  setShowComparePanel,
  onResetAll,
  t,
  viewMode,
  setViewMode,
}: QuickFiltersProps) {
  const QUICK_FILTER_KEYS = ['all', 'popular', 'new', 'priceLow', 'priceHigh', 'salesCount', 'reviewCount', 'favorites'] as const
  const SORT_KEYS: SortOption[] = ['popular', 'new', 'priceLow', 'priceHigh', 'salesCount', 'reviewCount']

  const handleFilterClick = (key: typeof QUICK_FILTER_KEYS[number]) => {
    if (key === 'all') {
      onResetAll()
    } else if (key === 'favorites') {
      setShowWishlistOnly(!showWishlistOnly)
    } else if (SORT_KEYS.includes(key)) {
      setSortBy(key)
      setShowWishlistOnly(false)
    }
  }

  const getButtonStyle = (key: typeof QUICK_FILTER_KEYS[number]) => {
    if (key === 'favorites' && showWishlistOnly) {
      return 'bg-red-500 text-white shadow-md shadow-red-500/30'
    }
    if (sortBy === key && !showWishlistOnly) {
      return 'bg-orange-500 text-white shadow-md shadow-orange-500/30'
    }
    if (key === 'all' && sortBy === 'popular' && !showWishlistOnly) {
      return 'bg-orange-500 text-white shadow-md shadow-orange-500/30'
    }
    return 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-600'
  }

  return (
    <div className="flex gap-1.5 px-3 pb-2 overflow-x-auto scrollbar-hide" role="group" aria-label="빠른 필터">
      {QUICK_FILTER_KEYS.map((key) => (
        <button
          key={key}
          onClick={() => handleFilterClick(key)}
          aria-pressed={key === 'favorites' ? showWishlistOnly : sortBy === key}
          className={`min-h-[44px] px-4 py-2.5 rounded-full text-xs font-medium whitespace-nowrap
                     transition-all duration-150 flex items-center gap-1
                     focus:outline-none focus:ring-2 focus:ring-orange-400 focus:ring-offset-2
                     ${getButtonStyle(key)}`}
        >
          <span>{FILTER_ICONS[key]}</span>
          <span>{t(key as TranslationKey)}</span>
          {key === 'favorites' && wishlistCount > 0 && (
            <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${showWishlistOnly ? 'bg-white/30' : 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'}`}>
              {wishlistCount}
            </span>
          )}
        </button>
      ))}

      {/* 비교 모드 버튼 */}
      {compareCount > 0 && (
        <button
          onClick={() => setShowComparePanel(!showComparePanel)}
          aria-pressed={showComparePanel}
          aria-label={`상품 비교 (${compareCount}개)`}
          className={`min-h-[44px] px-4 py-2.5 rounded-full text-xs font-medium whitespace-nowrap
                     transition-all duration-150 flex items-center gap-1.5
                     focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2
                     ${showComparePanel
                       ? 'bg-blue-500 text-white shadow-md shadow-blue-500/30'
                       : 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                     }`}
        >
          <Scale className="w-4 h-4" />
          <span> {compareCount}</span>
        </button>
      )}

      {/* 뷰 모드 버튼 그룹 */}
      <div
        role="group"
        aria-label="보기 방식 선택"
        className="flex ml-auto border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800"
      >
        <button
          onClick={() => setViewMode('large')}
          className={`min-w-[44px] min-h-[44px] p-3 transition-colors flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-orange-400 focus:ring-inset ${viewMode === 'large' ? 'bg-orange-500 text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
          aria-label="큰 아이콘 보기"
          aria-pressed={viewMode === 'large'}
        >
          <LayoutGrid className="w-5 h-5" aria-hidden="true" />
        </button>
        <button
          onClick={() => setViewMode('small')}
          className={`min-w-[44px] min-h-[44px] p-3 transition-colors border-x border-gray-200 dark:border-gray-700 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-orange-400 focus:ring-inset ${viewMode === 'small' ? 'bg-orange-500 text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
          aria-label="작은 아이콘 보기"
          aria-pressed={viewMode === 'small'}
        >
          <Grid3X3 className="w-5 h-5" aria-hidden="true" />
        </button>
        <button
          onClick={() => setViewMode('list')}
          className={`min-w-[44px] min-h-[44px] p-3 transition-colors flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-orange-400 focus:ring-inset ${viewMode === 'list' ? 'bg-orange-500 text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
          aria-label="목록 보기"
          aria-pressed={viewMode === 'list'}
        >
          <List className="w-5 h-5" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
