'use client'

import { Scale, Grid3X3, LayoutGrid, List } from 'lucide-react'
import type { TranslationKey } from '@/lib/i18n'

// 필터 아이콘
const FILTER_ICONS: Record<string, string> = {
  all: '',
  popular: '',
  new: '',
  recommended: '',
  favorites: '',
}

export type ViewMode = 'large' | 'small' | 'list'

interface QuickFiltersProps {
  sortBy: string
  setSortBy: (sort: string) => void
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
  const QUICK_FILTER_KEYS = ['all', 'popular', 'new', 'recommended', 'favorites'] as const

  const handleFilterClick = (key: typeof QUICK_FILTER_KEYS[number]) => {
    if (key === 'all') {
      onResetAll()
    } else if (key === 'favorites') {
      setShowWishlistOnly(!showWishlistOnly)
    } else if (['popular', 'new', 'recommended'].includes(key)) {
      setSortBy(key)
      setShowWishlistOnly(false)
    }
  }

  const getButtonStyle = (key: typeof QUICK_FILTER_KEYS[number]) => {
    if (key === 'favorites' && showWishlistOnly) {
      return 'bg-red-500 text-white shadow-md shadow-red-500/30'
    }
    if ((sortBy === key && !showWishlistOnly) || (key === 'all' && sortBy === 'popular' && !showWishlistOnly)) {
      return 'bg-orange-500 text-white shadow-md shadow-orange-500/30'
    }
    return 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-600'
  }

  return (
    <div className="flex gap-1.5 px-3 pb-2 overflow-x-auto scrollbar-hide">
      {QUICK_FILTER_KEYS.map((key) => (
        <button
          key={key}
          onClick={() => handleFilterClick(key)}
          className={`px-2.5 py-1 rounded-full text-[11px] font-medium whitespace-nowrap
                     transition-all duration-150 flex items-center gap-0.5
                     ${getButtonStyle(key)}`}
        >
          <span>{FILTER_ICONS[key]}</span>
          <span>{t(key as TranslationKey)}</span>
          {key === 'favorites' && wishlistCount > 0 && (
            <span className={`px-1 py-0.5 rounded-full text-[9px] ${showWishlistOnly ? 'bg-white/30' : 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'}`}>
              {wishlistCount}
            </span>
          )}
        </button>
      ))}

      {/* 비교 모드 버튼 */}
      {compareCount > 0 && (
        <button
          onClick={() => setShowComparePanel(!showComparePanel)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap
                     transition-all duration-150 flex items-center gap-1
                     ${showComparePanel
                       ? 'bg-blue-500 text-white shadow-md shadow-blue-500/30'
                       : 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                     }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span> {compareCount}</span>
        </button>
      )}

      {/* 뷰 모드 버튼 그룹 */}
      <div className="flex ml-auto border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
        <button
          onClick={() => setViewMode('large')}
          className={`p-1.5 transition-colors ${viewMode === 'large' ? 'bg-orange-500 text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
          title="큰 아이콘"
        >
          <LayoutGrid className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => setViewMode('small')}
          className={`p-1.5 transition-colors border-x border-gray-200 dark:border-gray-700 ${viewMode === 'small' ? 'bg-orange-500 text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
          title="작은 아이콘"
        >
          <Grid3X3 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => setViewMode('list')}
          className={`p-1.5 transition-colors ${viewMode === 'list' ? 'bg-orange-500 text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
          title="목록"
        >
          <List className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
