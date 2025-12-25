'use client'

import { useState, useMemo, useCallback, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ProductCard } from '@/components/ProductCard'
import { AdvancedFilterDrawer } from '@/components/AdvancedFilterDrawer'
import { ComparePanel, CompareFab } from '@/components/ComparePanel'
import { ShoppingMode } from '@/components/ShoppingMode'
import { fetchProducts } from '@/lib/api'
import type { Product } from '@/lib/types'
import { STORES } from '@/lib/types'
import { useWishlist } from '@/lib/useWishlist'
import { useAdvancedFilters } from '@/lib/useAdvancedFilters'
import { useCompare } from '@/lib/useCompare'
import { useTheme } from '@/lib/useTheme'
import { useShare } from '@/lib/useShare'
import { useChecklist } from '@/lib/useChecklist'
import { useLocale } from '@/lib/i18n'
import {
  Package, Search, RefreshCw, Clock, X, Heart,
  SlidersHorizontal, Scale, Sun, Moon, Share2, ChevronUp, Download,
  ShoppingCart, Globe, Tag
} from 'lucide-react'
import { ErrorBoundary, ApiErrorDisplay } from '@/components/ErrorBoundary'

// UX Laws Applied:
// 1. Hick's Law - 선택지 3~4개로 제한, 추천 필터 먼저 표시
// 2. Miller's Law - 정보를 5~7개 그룹으로 청킹
// 3. Fitts's Law - 중요 버튼 크게, 터치 영역 44px 이상
// 4. Jakob's Law - 표준 UI 패턴 사용 (검색창 위치, 아이콘 등)
// 5. Tesler's Law - 시스템이 복잡성 처리 (자동 정렬, 추천 필터)
// 6. Doherty Threshold - 400ms 이내 반응, 스켈레톤 UI

// 빠른 필터 키 (Hick's Law: 핵심 5개만)
const QUICK_FILTER_KEYS = ['all', 'popular', 'new', 'recommended', 'wishlist'] as const

// 카테고리 키 (Miller's Law: 7개로 제한)
const CATEGORY_KEYS = ['all', 'kitchen', 'living', 'beauty', 'interior', 'food', 'digital'] as const

// 필터/카테고리 아이콘
const FILTER_ICONS: Record<string, string> = {
  all: '🔥',
  popular: '📈',
  new: '✨',
  recommended: '💬',
  wishlist: '❤️',
  kitchen: '🍳',
  living: '🏠',
  beauty: '💄',
  interior: '🪴',
  food: '🍽️',
  digital: '📱',
}

export default function Home() {
  const [selectedStore, setSelectedStore] = useState('all')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [sortBy, setSortBy] = useState('popular')
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearchFocused, setIsSearchFocused] = useState(false)
  const [showWishlistOnly, setShowWishlistOnly] = useState(false)
  const [showScrollTop, setShowScrollTop] = useState(false)
  const [showShoppingMode, setShowShoppingMode] = useState(false)
  const [showLangMenu, setShowLangMenu] = useState(false)

  // 테마
  const { resolvedTheme, toggleTheme, mounted } = useTheme()

  // 다국어
  const { locale, setLocale, t, localeNames } = useLocale()

  // 찜하기 기능
  const { wishlistIds, wishlistCount, toggleWishlist, isInWishlist, downloadWishlist } = useWishlist()

  // 체크리스트 (쇼핑 모드용)
  const { checkedIds, toggleCheck } = useChecklist()

  // 공유 기능
  const { shareProduct, shareWishlist, shareCurrentView, isSharing } = useShare()

  // 비교 기능
  const {
    compareIds,
    compareCount,
    maxCompareItems,
    toggleCompare,
    isInCompare,
    clearCompare,
    showComparePanel,
    setShowComparePanel,
  } = useCompare()

  // Doherty Threshold: 즉각적인 데이터 로딩
  const { data: products = [], isLoading, isError, error, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ['products'],
    queryFn: () => fetchProducts(),
    staleTime: 5 * 60 * 1000, // 5분
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })

  // 고급 필터
  const {
    filters: advancedFilters,
    updateFilter,
    resetFilters,
    activeFilterCount,
    applyFilters,
    priceStats,
    viewStats,
    isOpen: isFilterOpen,
    setIsOpen: setIsFilterOpen,
  } = useAdvancedFilters(products)

  // 스크롤 위치 감지
  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 500)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // 맨 위로 스크롤
  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  // Tesler's Law: 시스템이 정렬/필터링 처리
  const filteredProducts = useMemo(() => {
    let result = [...products]

    // 고급 필터 적용
    result = applyFilters(result)

    // 찜 목록 필터
    if (showWishlistOnly) {
      result = result.filter((p: Product) => wishlistIds.includes(p.id))
    }

    // 스토어 필터
    if (selectedStore !== 'all') {
      result = result.filter((p: Product) => p.store_key === selectedStore)
    }

    // 카테고리 필터 (Tesler's Law: 자동 분류)
    if (selectedCategory !== 'all') {
      result = result.filter((p: Product) => {
        const cat = p.category?.toLowerCase() || ''
        if (selectedCategory === 'food') return cat.includes('식품') || cat.includes('간식') || cat.includes('음료')
        if (selectedCategory === 'beauty') return cat.includes('뷰티') || cat.includes('화장') || cat.includes('미용')
        if (selectedCategory === 'living') return cat.includes('생활') || cat.includes('청소') || cat.includes('세탁')
        if (selectedCategory === 'kitchen') return cat.includes('주방') || cat.includes('밀폐') || cat.includes('유리') || cat.includes('실리콘')
        if (selectedCategory === 'interior') return cat.includes('인테리어') || cat.includes('수납') || cat.includes('조명')
        if (selectedCategory === 'digital') return cat.includes('디지털') || cat.includes('케이블') || cat.includes('전자')
        return true
      })
    }

    // 검색 (품번, 상품명, 채널명, 카테고리)
    if (searchQuery) {
      const query = searchQuery.toLowerCase().trim()
      result = result.filter((p: Product) =>
        p.name.toLowerCase().includes(query) ||
        p.official_name?.toLowerCase().includes(query) ||
        p.official_code?.toLowerCase().includes(query) ||  // 품번 검색 추가
        p.channel_title?.toLowerCase().includes(query) ||
        p.category?.toLowerCase().includes(query) ||
        p.keywords?.some(k => k.toLowerCase().includes(query))  // 키워드 검색 추가
      )
    }

    // 정렬 (Tesler's Law: 자동 정렬)
    if (sortBy === 'popular') {
      result.sort((a, b) => (b.source_view_count || 0) - (a.source_view_count || 0))
    } else if (sortBy === 'new') {
      result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } else if (sortBy === 'recommended') {
      result.sort((a, b) => {
        const aScore = (a.recommendation_quote ? 1000 : 0) + (a.source_view_count || 0)
        const bScore = (b.recommendation_quote ? 1000 : 0) + (b.source_view_count || 0)
        return bScore - aScore
      })
    }

    return result
  }, [products, selectedStore, selectedCategory, searchQuery, sortBy, showWishlistOnly, wishlistIds, applyFilters])

  // 스토어별 개수 계산
  const storeCounts = useMemo(() => {
    const counts: Record<string, number> = { all: products.length }
    products.forEach((p: Product) => {
      counts[p.store_key] = (counts[p.store_key] || 0) + 1
    })
    return counts
  }, [products])

  // 검색 초기화 핸들러
  const handleClearSearch = useCallback(() => {
    setSearchQuery('')
  }, [])

  // 마지막 업데이트 시간
  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
    : null

  // 하이드레이션 문제 방지
  if (!mounted) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-orange-50 to-gray-100 dark:from-gray-900 dark:to-gray-950">
        <div className="flex items-center justify-center h-screen">
          <div className="animate-pulse text-orange-500 text-xl">로딩 중...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50 to-gray-100 dark:from-gray-900 dark:to-gray-950 transition-colors duration-300">
      {/* 헤더 - Sticky, Jakob's Law: 표준 위치 */}
      <header className="sticky top-0 z-40 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md shadow-sm transition-colors">
        {/* 로고 + 검색 + 액션버튼 */}
        <div className="flex items-center gap-1.5 px-3 py-2">
          <h1 className="text-base font-bold text-orange-500 whitespace-nowrap flex items-center gap-0.5">
            🛒
          </h1>
          <div className="flex-1 relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input
              type="text"
              placeholder={t('searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setIsSearchFocused(false)}
              className={`w-full pl-8 pr-8 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs
                         text-gray-900 dark:text-white placeholder-gray-400
                         focus:outline-none focus:ring-2 focus:ring-orange-400 focus:bg-white dark:focus:bg-gray-800
                         transition-all duration-200
                         ${isSearchFocused ? 'bg-white dark:bg-gray-800 shadow-lg' : ''}`}
            />
            {searchQuery && (
              <button
                onClick={handleClearSearch}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full"
              >
                <X className="w-3.5 h-3.5 text-gray-400" />
              </button>
            )}
          </div>

          {/* 액션 버튼들 */}
          <div className="flex items-center">
            {/* 쇼핑 모드 버튼 (찜 목록이 있을 때만) */}
            {wishlistCount > 0 && (
              <button
                onClick={() => setShowShoppingMode(true)}
                className="p-1.5 rounded-lg bg-gradient-to-r from-orange-400 to-red-500 text-white transition-all relative mr-0.5"
                title={t('shopping')}
              >
                <ShoppingCart className="w-3.5 h-3.5" />
                <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-white text-orange-500 text-[8px]
                               rounded-full flex items-center justify-center font-bold shadow-sm">
                  {wishlistCount}
                </span>
              </button>
            )}

            {/* 고급 필터 버튼 */}
            <button
              onClick={() => setIsFilterOpen(true)}
              className={`p-1.5 rounded-lg transition-colors relative
                         ${activeFilterCount > 0
                           ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-500'
                           : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400'
                         }`}
              title={t('advancedFilters')}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              {activeFilterCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-orange-500 text-white text-[8px]
                               rounded-full flex items-center justify-center font-bold">
                  {activeFilterCount}
                </span>
              )}
            </button>

            {/* 언어 선택 */}
            <div className="relative">
              <button
                onClick={() => setShowLangMenu(!showLangMenu)}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                title={t('language')}
              >
                <Globe className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
              </button>
              {showLangMenu && (
                <div className="absolute right-0 top-full mt-0.5 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-0.5 min-w-[90px] z-50">
                  {(['ko', 'en', 'ja'] as const).map((lang) => (
                    <button
                      key={lang}
                      onClick={() => {
                        setLocale(lang)
                        setShowLangMenu(false)
                      }}
                      className={`w-full px-2.5 py-1.5 text-left text-xs hover:bg-gray-100 dark:hover:bg-gray-700
                                ${locale === lang ? 'text-orange-500 font-medium' : 'text-gray-700 dark:text-gray-300'}`}
                    >
                      {localeNames[lang]}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 다크모드 토글 */}
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title={resolvedTheme === 'dark' ? t('lightMode') : t('darkMode')}
            >
              {resolvedTheme === 'dark' ? (
                <Sun className="w-3.5 h-3.5 text-yellow-400" />
              ) : (
                <Moon className="w-3.5 h-3.5 text-gray-500" />
              )}
            </button>

            {/* 새로고침 */}
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title={t('refresh')}
            >
              <RefreshCw className={`w-3.5 h-3.5 text-gray-500 dark:text-gray-400 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* 빠른 필터 - Hick's Law: 핵심 5개만 */}
        <div className="flex gap-1.5 px-3 pb-2 overflow-x-auto scrollbar-hide">
          {QUICK_FILTER_KEYS.map((key) => (
            <button
              key={key}
              onClick={() => {
                if (key === 'all') {
                  setSelectedStore('all')
                  setSelectedCategory('all')
                  setSortBy('popular')
                  setShowWishlistOnly(false)
                } else if (key === 'wishlist') {
                  setShowWishlistOnly(!showWishlistOnly)
                } else if (['popular', 'new', 'recommended'].includes(key)) {
                  setSortBy(key)
                  setShowWishlistOnly(false)
                }
              }}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium whitespace-nowrap
                         transition-all duration-150 flex items-center gap-0.5
                         ${(key === 'wishlist' && showWishlistOnly)
                           ? 'bg-red-500 text-white shadow-md shadow-red-500/30'
                           : (sortBy === key && !showWishlistOnly) || (key === 'all' && selectedStore === 'all' && selectedCategory === 'all' && !showWishlistOnly)
                             ? 'bg-orange-500 text-white shadow-md shadow-orange-500/30'
                             : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-600'
                         }`}
            >
              <span>{FILTER_ICONS[key]}</span>
              <span>{t(key as any)}</span>
              {key === 'wishlist' && wishlistCount > 0 && (
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
              <span>비교 {compareCount}</span>
            </button>
          )}
        </div>

        {/* 스토어 필터 - Hick's Law: 존재하는 것만 표시 */}
        <div className="overflow-x-auto scrollbar-hide border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex gap-1.5 px-4 py-2 min-w-max">
            <button
              onClick={() => setSelectedStore('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap
                         transition-all duration-150
                         ${selectedStore === 'all'
                           ? 'bg-gray-800 dark:bg-white text-white dark:text-gray-900'
                           : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700'
                         }`}
            >
              전체 {storeCounts.all}개
            </button>
            {Object.entries(STORES).map(([key, store]) => (
              storeCounts[key] > 0 && (
                <button
                  key={key}
                  onClick={() => setSelectedStore(key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap
                             transition-all duration-150 flex items-center gap-1
                             ${selectedStore === key
                               ? 'text-white shadow-md'
                               : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700'
                             }`}
                  style={selectedStore === key ? { backgroundColor: store.color } : {}}
                >
                  <span>{store.icon}</span>
                  <span>{store.name}</span>
                  <span className="opacity-70">{storeCounts[key]}</span>
                </button>
              )
            ))}
          </div>
        </div>

        {/* 카테고리 필터 - Miller's Law: 7개로 제한 */}
        <div className="overflow-x-auto scrollbar-hide border-t border-gray-100 dark:border-gray-800">
          <div className="flex gap-1 px-3 py-1 min-w-max">
            {CATEGORY_KEYS.map((key) => (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`px-2 py-0.5 rounded-md text-[10px] whitespace-nowrap
                           transition-all duration-150
                           ${selectedCategory === key
                             ? 'bg-gray-700 dark:bg-gray-200 text-white dark:text-gray-900 font-medium'
                             : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
                           }`}
              >
                {FILTER_ICONS[key]} {t(key as any)}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="px-3 py-3 pb-24">
        {/* 결과 요약 - Miller's Law: 핵심 정보만 */}
        <div className="flex items-center justify-between mb-2 px-1">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              {filteredProducts.length} {t('products')}
            </span>
            {searchQuery && (
              <span className="text-[10px] text-gray-400 dark:text-gray-500">
                "{searchQuery}" {t('searchResults')}
              </span>
            )}
            {activeFilterCount > 0 && (
              <button
                onClick={resetFilters}
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

        {/* 로딩 스켈레톤 - Doherty Threshold: 즉각적 피드백 */}
        {isLoading && (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden animate-pulse">
                <div className="aspect-[4/3] bg-gray-200 dark:bg-gray-700" />
                <div className="p-3 space-y-2">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                  <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                  <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 에러 상태 */}
        {isError && (
          <ApiErrorDisplay
            error={error as Error}
            onRetry={() => refetch()}
            isRetrying={isFetching}
          />
        )}

        {/* 빈 상태 */}
        {!isLoading && !isError && filteredProducts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400 dark:text-gray-500">
            {showWishlistOnly ? (
              <>
                <Heart className="w-12 h-12 mb-3 text-gray-300 dark:text-gray-600" />
                <p className="text-sm font-medium mb-0.5 text-gray-600 dark:text-gray-400">{t('noWishlist')}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500">{t('addSomeProducts')}</p>
                <button
                  onClick={() => setShowWishlistOnly(false)}
                  className="mt-3 px-3 py-1.5 bg-orange-500 text-white rounded-lg text-xs font-medium hover:bg-orange-600 transition-colors"
                >
                  {t('viewAllProducts')}
                </button>
              </>
            ) : (
              <>
                <Package className="w-12 h-12 mb-3 text-gray-300 dark:text-gray-600" />
                <p className="text-sm font-medium mb-0.5 text-gray-600 dark:text-gray-400">{t('noResults')}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500">{t('tryDifferentSearch')}</p>
                {(searchQuery || activeFilterCount > 0) && (
                  <button
                    onClick={() => {
                      handleClearSearch()
                      resetFilters()
                    }}
                    className="mt-3 px-3 py-1.5 bg-orange-500 text-white rounded-lg text-xs font-medium hover:bg-orange-600 transition-colors"
                  >
                    {t('resetFilters')}
                  </button>
                )}
              </>
            )}
          </div>
        )}

        {/* 찜 목록 헤더 (다운로드 버튼 포함) */}
        {showWishlistOnly && wishlistCount > 0 && (
          <div className="flex items-center justify-between mb-3 p-2 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <div className="flex items-center gap-1.5">
              <Heart className="w-4 h-4 text-red-500" fill="currentColor" />
              <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
                {t('wishlist')} ({wishlistCount})
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => downloadWishlist(products, 'text')}
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
        )}

        {/* 상품 그리드 - 2열 기본 (Fitts's Law: 충분한 터치 영역) */}
        {!isLoading && filteredProducts.length > 0 && (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {filteredProducts.map((product: Product) => (
              <ProductCard
                key={product.id}
                product={product}
                isInWishlist={isInWishlist(product.id)}
                onToggleWishlist={toggleWishlist}
                isInCompare={isInCompare(product.id)}
                onToggleCompare={toggleCompare}
                compareCount={compareCount}
                maxCompare={maxCompareItems}
                onShare={() => shareProduct(product)}
              />
            ))}
          </div>
        )}
      </main>

      {/* 푸터 - 미니멀 */}
      <footer className="fixed bottom-0 left-0 right-0 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-t border-gray-200 dark:border-gray-800 py-1.5 text-center z-30 transition-colors">
        <p className="text-[10px] text-gray-400 dark:text-gray-500">
          {t('appTagline')}
        </p>
      </footer>

      {/* 맨 위로 스크롤 버튼 */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-20 left-4 z-40 p-3 bg-white dark:bg-gray-800 rounded-full shadow-lg
                   border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700
                   transition-all duration-300 animate-fade-in"
        >
          <ChevronUp className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
      )}

      {/* 비교 FAB */}
      <CompareFab
        count={compareCount}
        onClick={() => setShowComparePanel(!showComparePanel)}
        isActive={showComparePanel}
      />

      {/* 고급 필터 드로어 */}
      <AdvancedFilterDrawer
        isOpen={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
        filters={advancedFilters}
        onUpdateFilter={updateFilter}
        onResetFilters={resetFilters}
        activeFilterCount={activeFilterCount}
        priceStats={priceStats}
        viewStats={viewStats}
      />

      {/* 비교 패널 */}
      <ComparePanel
        products={products}
        compareIds={compareIds}
        maxItems={maxCompareItems}
        onRemove={toggleCompare}
        onClear={clearCompare}
        onClose={() => setShowComparePanel(false)}
        isOpen={showComparePanel}
      />

      {/* 쇼핑 모드 */}
      <ShoppingMode
        products={products}
        wishlistIds={wishlistIds}
        isOpen={showShoppingMode}
        onClose={() => setShowShoppingMode(false)}
        onToggleCheck={toggleCheck}
        checkedIds={checkedIds}
      />

      {/* 스크롤 스타일 */}
      <style jsx global>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}
