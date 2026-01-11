'use client'

import { Package, Heart } from 'lucide-react'
import { ProductCard } from './ProductCard'
import type { Product } from '@/lib/types'
import type { TranslationKey } from '@/lib/i18n'

interface ProductGridProps {
  products: Product[]
  isLoading: boolean
  isError: boolean
  error?: Error
  onRetry: () => void
  isFetching: boolean

  // 찜/비교 기능
  isInWishlist: (id: number) => boolean
  onToggleWishlist: (id: number) => void
  isInCompare: (id: number) => boolean
  onToggleCompare: (id: number) => void
  compareCount: number
  maxCompare: number
  onShare: (product: Product) => void

  // 찜 목록 모드
  showWishlistOnly: boolean
  onClearWishlistOnly: () => void

  // 필터 상태
  activeFilterCount: number
  onResetFilters: () => void
  onClearSearch: () => void
  searchQuery: string

  // 번역
  t: (key: TranslationKey) => string
}

// 스켈레톤 UI
function ProductSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden animate-pulse">
      <div className="aspect-[4/3] bg-gray-200 dark:bg-gray-700" />
      <div className="p-3 space-y-2">
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
      </div>
    </div>
  )
}

// API 에러 표시
function ApiErrorDisplay({
  error,
  onRetry,
  isRetrying,
}: {
  error: Error
  onRetry: () => void
  isRetrying: boolean
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-400 dark:text-gray-500">
      <Package className="w-12 h-12 mb-3 text-red-300 dark:text-red-600" />
      <p className="text-sm font-medium mb-0.5 text-gray-600 dark:text-gray-400">
        데이터를 불러오는데 실패했습니다
      </p>
      <p className="text-xs text-gray-400 dark:text-gray-500 mb-3">
        {error.message}
      </p>
      <button
        onClick={onRetry}
        disabled={isRetrying}
        className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors disabled:opacity-50"
      >
        {isRetrying ? '재시도 중...' : '다시 시도'}
      </button>
    </div>
  )
}

// 빈 상태
function EmptyState({
  showWishlistOnly,
  onClearWishlistOnly,
  searchQuery,
  activeFilterCount,
  onClearSearch,
  onResetFilters,
  t,
}: {
  showWishlistOnly: boolean
  onClearWishlistOnly: () => void
  searchQuery: string
  activeFilterCount: number
  onClearSearch: () => void
  onResetFilters: () => void
  t: (key: TranslationKey) => string
}) {
  if (showWishlistOnly) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400 dark:text-gray-500">
        <Heart className="w-12 h-12 mb-3 text-gray-300 dark:text-gray-600" />
        <p className="text-sm font-medium mb-0.5 text-gray-600 dark:text-gray-400">{t('noWishlist')}</p>
        <p className="text-xs text-gray-400 dark:text-gray-500">{t('addSomeProducts')}</p>
        <button
          onClick={onClearWishlistOnly}
          className="mt-3 px-3 py-1.5 bg-orange-500 text-white rounded-lg text-xs font-medium hover:bg-orange-600 transition-colors"
        >
          {t('viewAllProducts')}
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-400 dark:text-gray-500">
      <Package className="w-12 h-12 mb-3 text-gray-300 dark:text-gray-600" />
      <p className="text-sm font-medium mb-0.5 text-gray-600 dark:text-gray-400">{t('noResults')}</p>
      <p className="text-xs text-gray-400 dark:text-gray-500">{t('tryDifferentSearch')}</p>
      {(searchQuery || activeFilterCount > 0) && (
        <button
          onClick={() => {
            onClearSearch()
            onResetFilters()
          }}
          className="mt-3 px-3 py-1.5 bg-orange-500 text-white rounded-lg text-xs font-medium hover:bg-orange-600 transition-colors"
        >
          {t('resetFilters')}
        </button>
      )}
    </div>
  )
}

export function ProductGrid({
  products,
  isLoading,
  isError,
  error,
  onRetry,
  isFetching,
  isInWishlist,
  onToggleWishlist,
  isInCompare,
  onToggleCompare,
  compareCount,
  maxCompare,
  onShare,
  showWishlistOnly,
  onClearWishlistOnly,
  activeFilterCount,
  onResetFilters,
  onClearSearch,
  searchQuery,
  t,
}: ProductGridProps) {
  // 로딩 스켈레톤
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {[...Array(8)].map((_, i) => (
          <ProductSkeleton key={i} />
        ))}
      </div>
    )
  }

  // 에러 상태
  if (isError && error) {
    return (
      <ApiErrorDisplay
        error={error}
        onRetry={onRetry}
        isRetrying={isFetching}
      />
    )
  }

  // 빈 상태
  if (products.length === 0) {
    return (
      <EmptyState
        showWishlistOnly={showWishlistOnly}
        onClearWishlistOnly={onClearWishlistOnly}
        searchQuery={searchQuery}
        activeFilterCount={activeFilterCount}
        onClearSearch={onClearSearch}
        onResetFilters={onResetFilters}
        t={t}
      />
    )
  }

  // 상품 그리드
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {products.map((product: Product) => (
        <ProductCard
          key={product.id}
          product={product}
          isInWishlist={isInWishlist(product.id)}
          onToggleWishlist={onToggleWishlist}
          isInCompare={isInCompare(product.id)}
          onToggleCompare={onToggleCompare}
          compareCount={compareCount}
          maxCompare={maxCompare}
          onShare={() => onShare(product)}
        />
      ))}
    </div>
  )
}
