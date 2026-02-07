'use client'

import { memo } from 'react'
import { Package, Heart, Loader2, Play, Eye } from 'lucide-react'
import { ProductCard } from './ProductCard'
import type { Product } from '@/lib/types'
import { STORES } from '@/lib/types'
import type { TranslationKey } from '@/lib/i18n'
import { useInfiniteScroll } from '@/lib/useInfiniteScroll'
import { formatPrice, getYoutubeThumbnail, formatViewCount, getProxiedImageUrl } from '@/lib/api'
import type { ViewMode } from './QuickFilters'

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

  // 뷰 모드
  viewMode: ViewMode

  // 검색 추천
  onSearchSuggestion?: (query: string) => void
}

// Stitch-style 스켈레톤 UI
const ProductSkeleton = memo(function ProductSkeleton() {
  return (
    <div className="flex flex-col gap-1.5">
      {/* 이미지 영역 - aspect-[4/5] */}
      <div className="relative aspect-[4/5] bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-sm border border-slate-100 dark:border-slate-800">
        <div className="absolute inset-0 bg-gray-200 dark:bg-gray-700 skeleton-shimmer" />
        {/* YT 배지 스켈레톤 */}
        <div className="absolute top-1.5 left-1.5 w-8 h-4 rounded-sm bg-gray-300 dark:bg-gray-600" />
        {/* 하트 버튼 스켈레톤 */}
        <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-gray-300 dark:bg-gray-600" />
        {/* + 버튼 스켈레톤 */}
        <div className="absolute bottom-1.5 right-1.5 w-7 h-7 rounded-lg bg-gray-300 dark:bg-gray-600" />
      </div>
      {/* 정보 영역 */}
      <div className="px-0.5 space-y-1">
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full skeleton-shimmer" />
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3 skeleton-shimmer" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16 skeleton-shimmer mt-1" />
      </div>
      <style>{`
        .skeleton-shimmer {
          background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }
        @media (prefers-color-scheme: dark) {
          .skeleton-shimmer {
            background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%);
            background-size: 200% 100%;
          }
        }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
      `}</style>
    </div>
  )
})

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

// 추천 검색어
const SUGGESTED_SEARCHES = ['밀폐용기', '수납박스', '청소용품', '화장품 파우치', '간식', '주방용품', '다이소 꿀템', '코스트코']

// 빈 상태
function EmptyState({
  showWishlistOnly,
  onClearWishlistOnly,
  searchQuery,
  activeFilterCount,
  onClearSearch,
  onResetFilters,
  onSearchSuggestion,
  t,
}: {
  showWishlistOnly: boolean
  onClearWishlistOnly: () => void
  searchQuery: string
  activeFilterCount: number
  onClearSearch: () => void
  onResetFilters: () => void
  onSearchSuggestion?: (query: string) => void
  t: (key: TranslationKey) => string
}) {
  if (showWishlistOnly) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-pink-100 to-red-100 dark:from-pink-900/30 dark:to-red-900/30 flex items-center justify-center mb-4">
          <Heart className="w-10 h-10 text-pink-400 dark:text-pink-500" />
        </div>
        <p className="text-base font-bold text-gray-700 dark:text-gray-300 mb-1">{t('noWishlist')}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center mb-4">{t('addSomeProducts')}</p>
        <button
          onClick={onClearWishlistOnly}
          className="px-5 py-2.5 bg-gradient-to-r from-orange-400 to-orange-500 text-white rounded-xl text-sm font-bold hover:from-orange-500 hover:to-orange-600 transition-all shadow-lg shadow-orange-500/25"
        >
          {t('viewAllProducts')}
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-20 h-20 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center mb-4">
        <Package className="w-10 h-10 text-gray-400 dark:text-gray-500" />
      </div>
      <p className="text-base font-bold text-gray-700 dark:text-gray-300 mb-1">
        {searchQuery ? `"${searchQuery}" 검색 결과가 없어요` : t('noResults')}
      </p>
      <p className="text-sm text-gray-500 dark:text-gray-400 text-center mb-4">
        {searchQuery ? '다른 검색어로 다시 시도해보세요' : t('tryDifferentSearch')}
      </p>

      {/* 검색 초기화 버튼 */}
      {(searchQuery || activeFilterCount > 0) && (
        <button
          onClick={() => {
            onClearSearch()
            onResetFilters()
          }}
          className="px-5 py-2.5 bg-gradient-to-r from-orange-400 to-orange-500 text-white rounded-xl text-sm font-bold hover:from-orange-500 hover:to-orange-600 transition-all shadow-lg shadow-orange-500/25 mb-6"
        >
          {t('resetFilters')}
        </button>
      )}

      {/* 추천 검색어 */}
      {onSearchSuggestion && (
        <div className="w-full max-w-sm">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 text-center">
            이런 검색어는 어떠세요?
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {SUGGESTED_SEARCHES.slice(0, 6).map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => onSearchSuggestion(suggestion)}
                className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full text-xs text-gray-600 dark:text-gray-300 hover:border-orange-300 hover:text-orange-500 dark:hover:border-orange-600 dark:hover:text-orange-400 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// 목록 뷰용 간소화된 아이템
const ProductListItem = memo(function ProductListItem({
  product,
  isInWishlist,
  onToggleWishlist,
}: {
  product: Product
  isInWishlist: boolean
  onToggleWishlist: (id: number) => void
}) {
  const store = STORES[product.store_key]
  // 핫링크 보호가 있는 사이트 (다이소몰 등)는 프록시 경유
  const rawImageUrl = product.image_url || product.official_image_url
  const imageUrl = getProxiedImageUrl(rawImageUrl)

  return (
    <div className="flex items-center gap-3 p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow">
      {/* 썸네일 */}
      <div className="relative w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={product.name}
            className="w-full h-full object-contain"
            loading="lazy"
          />
        ) : product.video_id ? (
          <div className="relative w-full h-full">
            <img
              src={getYoutubeThumbnail(product.video_id)}
              alt={product.name}
              className="w-full h-full object-cover"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
              <Play className="w-4 h-4 text-white" fill="white" />
            </div>
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-600 dark:to-gray-700">
            <Package className="w-6 h-6 text-gray-300 dark:text-gray-500" />
          </div>
        )}
        {/* 스토어 배지 */}
        <span
          className="absolute top-0.5 left-0.5 px-1 py-0.5 rounded text-white text-[8px] font-bold"
          style={{ backgroundColor: store?.color || '#666' }}
        >
          {store?.icon}
        </span>
      </div>

      {/* 상품 정보 */}
      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-xs text-gray-900 dark:text-white line-clamp-1">
          {product.official_name || product.name}
        </h3>
        <p className="text-sm font-bold text-red-500 dark:text-red-400 mt-0.5">
          {formatPrice(product.official_price || product.price)}
        </p>
        <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500 dark:text-gray-400">
          <span className="truncate">{product.channel_title}</span>
          {product.source_view_count > 0 && (
            <span className="flex items-center gap-0.5 flex-shrink-0">
              <Eye className="w-2.5 h-2.5" />
              {formatViewCount(product.source_view_count)}
            </span>
          )}
        </div>
      </div>

      {/* 찜 버튼 */}
      <button
        onClick={(e) => {
          e.stopPropagation()
          onToggleWishlist(product.id)
        }}
        className={`p-2 rounded-full transition-colors flex-shrink-0 ${
          isInWishlist
            ? 'bg-red-100 dark:bg-red-900/30 text-red-500'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-red-500'
        }`}
      >
        <Heart className="w-4 h-4" fill={isInWishlist ? 'currentColor' : 'none'} />
      </button>
    </div>
  )
})

export const ProductGrid = memo(function ProductGrid({
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
  viewMode,
  onSearchSuggestion,
}: ProductGridProps) {
  // 무한 스크롤 훅 (Rules of Hooks: 조건부 return 전에 호출)
  const {
    displayedItems,
    hasMore,
    isLoadingMore,
    loaderRef,
  } = useInfiniteScroll({
    items: products,
    pageSize: 20,
    rootMargin: '400px',
  })

  // Stitch-style 로딩 스켈레톤 (3열 기본)
  if (isLoading) {
    return (
      <div role="status" aria-busy="true" aria-label="Loading products" className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        {[...Array(9)].map((_, i) => (
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
        onSearchSuggestion={onSearchSuggestion}
        t={t}
      />
    )
  }

  // Stitch-style: 3열 그리드가 기본 (high-density product discovery)
  const gridClass = viewMode === 'large'
    ? 'grid grid-cols-3 gap-2.5 sm:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6'
    : viewMode === 'small'
      ? 'grid grid-cols-4 gap-2 sm:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7'
      : 'flex flex-col gap-1.5'

  // 상품 그리드 + 무한 스크롤
  return (
    <>
      <div className={gridClass}>
        {displayedItems.map((product: Product) => (
          viewMode === 'list' ? (
            <ProductListItem
              key={product.id}
              product={product}
              isInWishlist={isInWishlist(product.id)}
              onToggleWishlist={onToggleWishlist}
            />
          ) : (
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
              compact={viewMode === 'small'}
            />
          )
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
})
