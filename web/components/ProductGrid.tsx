'use client'

import { Package, Heart, Loader2 } from 'lucide-react'
import { ProductCard } from './ProductCard'
import type { Product } from '@/lib/types'
import type { TranslationKey } from '@/lib/i18n'
import { useInfiniteScroll } from '@/lib/useInfiniteScroll'

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

// 스켈레톤 UI - Shimmer 효과 적용
function ProductSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
      {/* 이미지 영역 */}
      <div className="relative aspect-[4/3] bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div className="absolute inset-0 skeleton-shimmer" />
        {/* 스토어 배지 스켈레톤 */}
        <div className="absolute top-1.5 left-1.5 w-14 h-4 rounded-full bg-gray-300 dark:bg-gray-600" />
        {/* 찜 버튼 스켈레톤 */}
        <div className="absolute top-1.5 right-1.5 w-7 h-7 rounded-full bg-gray-300 dark:bg-gray-600" />
      </div>
      {/* 정보 영역 */}
      <div className="p-2 space-y-2">
        {/* 상품명 */}
        <div className="space-y-1">
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full skeleton-shimmer" />
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3 skeleton-shimmer" />
        </div>
        {/* 가격 + 품번 */}
        <div className="flex items-center justify-between">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20 skeleton-shimmer" />
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-12 skeleton-shimmer" />
        </div>
        {/* 채널 + 조회수 */}
        <div className="flex items-center justify-between">
          <div className="h-2.5 bg-gray-200 dark:bg-gray-700 rounded w-16 skeleton-shimmer" />
          <div className="h-2.5 bg-gray-200 dark:bg-gray-700 rounded w-10 skeleton-shimmer" />
        </div>
      </div>
      {/* Shimmer 애니메이션 스타일 */}
      <style>{`
        .skeleton-shimmer {
          background: linear-gradient(
            90deg,
            transparent 0%,
            rgba(255, 255, 255, 0.4) 50%,
            transparent 100%
          );
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }
        @media (prefers-color-scheme: dark) {
          .skeleton-shimmer {
            background: linear-gradient(
              90deg,
              transparent 0%,
              rgba(255, 255, 255, 0.1) 50%,
              transparent 100%
            );
            background-size: 200% 100%;
          }
        }
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
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

  // 무한 스크롤 훅
  const {
    displayedItems,
    hasMore,
    isLoadingMore,
    loaderRef,
  } = useInfiniteScroll({
    items: products,
    pageSize: 20,
    rootMargin: '400px', // 화면 하단 400px 전에 미리 로딩
  })

  // 상품 그리드 + 무한 스크롤
  return (
    <>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {displayedItems.map((product: Product) => (
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

      {/* 무한 스크롤 로더 */}
      {hasMore && (
        <div
          ref={loaderRef}
          className="flex items-center justify-center py-8"
        >
          <div className="flex items-center gap-2 text-gray-400 dark:text-gray-500">
            {isLoadingMore ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-sm">로딩 중...</span>
              </>
            ) : (
              <span className="text-sm">스크롤하여 더 보기</span>
            )}
          </div>
        </div>
      )}

      {/* 전체 로드 완료 */}
      {!hasMore && products.length > 20 && (
        <div className="flex items-center justify-center py-6">
          <span className="text-xs text-gray-400 dark:text-gray-500">
            모든 상품을 불러왔습니다 ({products.length}개)
          </span>
        </div>
      )}
    </>
  )
}
