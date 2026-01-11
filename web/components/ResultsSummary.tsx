'use client'

import { Clock, X } from 'lucide-react'
import type { TranslationKey } from '@/lib/i18n'

interface ResultsSummaryProps {
  productCount: number
  searchQuery: string
  activeFilterCount: number
  onResetFilters: () => void
  lastUpdated: string | null
  t: (key: TranslationKey) => string
}

export function ResultsSummary({
  productCount,
  searchQuery,
  activeFilterCount,
  onResetFilters,
  lastUpdated,
  t,
}: ResultsSummaryProps) {
  return (
    <div className="flex items-center justify-between mb-2 px-1">
      <div className="flex items-center gap-1.5">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
          {productCount} {t('products')}
        </span>
        {searchQuery && (
          <span className="text-[10px] text-gray-400 dark:text-gray-500">
            "{searchQuery}" {t('searchResults')}
          </span>
        )}
        {activeFilterCount > 0 && (
          <button
            onClick={onResetFilters}
            className="text-[10px] text-orange-500 hover:text-orange-600 flex items-center gap-0.5"
          >
            {t('resetFilters')}
            <X className="w-2.5 h-2.5" />
          </button>
        )}
      </div>
      {lastUpdated && (
        <span className="text-[9px] text-gray-400 dark:text-gray-500 flex items-center gap-0.5">
          <Clock className="w-2.5 h-2.5" />
          {lastUpdated} {t('lastUpdated')}
        </span>
      )}
    </div>
  )
}
