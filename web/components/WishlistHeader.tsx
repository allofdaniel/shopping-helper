'use client'

import { Heart, Download } from 'lucide-react'
import type { Product } from '@/lib/types'
import type { TranslationKey } from '@/lib/i18n'

interface WishlistHeaderProps {
  wishlistCount: number
  products: Product[]
  onDownload: (products: Product[], format: 'text' | 'csv') => void
  t: (key: TranslationKey) => string
}

export function WishlistHeader({
  wishlistCount,
  products,
  onDownload,
  t,
}: WishlistHeaderProps) {
  if (wishlistCount === 0) return null

  return (
    <div className="flex items-center justify-between mb-3 p-2 bg-red-50 dark:bg-red-900/20 rounded-lg">
      <div className="flex items-center gap-1.5">
        <Heart className="w-4 h-4 text-red-500" fill="currentColor" />
        <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
          {t('wishlist')} ({wishlistCount})
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onDownload(products, 'text')}
          className="flex items-center gap-0.5 px-2 py-1 bg-white dark:bg-gray-800 rounded-lg
                   text-[10px] font-medium text-gray-600 dark:text-gray-400
                   hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors
                   border border-gray-200 dark:border-gray-700"
          title={t('exportWishlist')}
        >
          <Download className="w-3 h-3" />
          {t('exportWishlist')}
        </button>
      </div>
    </div>
  )
}
