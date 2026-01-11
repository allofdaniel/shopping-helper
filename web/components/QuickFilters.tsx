'use client'

import { Scale } from 'lucide-react'
import type { TranslationKey } from '@/lib/i18n'

// 필터 아이콘
const FILTER_ICONS: Record<string, string> = {
  all: '',
  popular: '',
  new: '',
  recommended: '',
  favorites: '',
}

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
    </div>
  )
}
