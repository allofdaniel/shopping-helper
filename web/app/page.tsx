'use client'

// Build v2.2.0 - Performance + Security + Accessibility improvements
import { useState, useMemo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import dynamic from 'next/dynamic'

// Components - eagerly loaded (above the fold)
import { type ViewMode } from '@/components/QuickFilters'
import { ProductGrid } from '@/components/ProductGrid'
import { WishlistHeader } from '@/components/WishlistHeader'
import { ScrollTopButton } from '@/components/ScrollTopButton'
import { AdvancedFilterDrawer } from '@/components/AdvancedFilterDrawer'
import { ComparePanel, CompareFab } from '@/components/ComparePanel'
import { PullToRefreshIndicator } from '@/components/PullToRefresh'
import { ToastContainer } from '@/components/Toast'
import { OfflineIndicator } from '@/components/OfflineIndicator'

// Components - lazy loaded (modals, not needed at initial render)
const ShoppingMode = dynamic(() => import('@/components/ShoppingMode').then(m => m.ShoppingMode), { ssr: false })
const Onboarding = dynamic(() => import('@/components/Onboarding').then(m => m.Onboarding), { ssr: false })
const StoreLocator = dynamic(() => import('@/components/StoreLocator').then(m => m.StoreLocator), { ssr: false })
const BarcodeScanner = dynamic(() => import('@/components/BarcodeScanner').then(m => m.BarcodeScanner), { ssr: false })

// Hooks from lazy-loaded components (hooks are lightweight, safe to import eagerly)
import { useOnboarding } from '@/components/Onboarding'
import { useStoreLocator } from '@/components/StoreLocator'
import { useBarcodeScanner } from '@/components/BarcodeScanner'

// Libs & Types
import { fetchProducts } from '@/lib/api'
import type { Product, SortOption, StoreFilter } from '@/lib/types'
import { useWishlist } from '@/lib/useWishlist'
import { useAdvancedFilters } from '@/lib/useAdvancedFilters'
import { useCompare } from '@/lib/useCompare'
import { useTheme } from '@/lib/useTheme'
import { useShare } from '@/lib/useShare'
import { useChecklist } from '@/lib/useChecklist'
import { useLocale, type TranslationKey } from '@/lib/i18n'
import { usePullToRefresh } from '@/lib/usePullToRefresh'
import { useToastProvider } from '@/lib/useToast'
import { useRecentSearch } from '@/lib/useRecentSearch'
import { useDebounce } from '@/lib/useDebounce'
import { matchesCategory, CATEGORY_KEYS, type CategoryKey } from '@/lib/categoryUtils'

const FILTER_ICONS: Record<string, string> = {
  all: '🏠',
  kitchen: '🍳',
  living: '🧹',
  beauty: '💄',
  interior: '🪴',
  food: '🍪',
  digital: '📱',
  fashion: '👕',
  health: '💊',
  baby: '👶',
  pet: '🐕',
  office: '📝',
  outdoor: '⛺',
}

export default function Home() {
  // UI State
  const [selectedStore, setSelectedStore] = useState<StoreFilter>('all')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [sortBy, setSortBy] = useState<SortOption>('new')
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedSearchQuery = useDebounce(searchQuery, 300) // Debounce search for better performance
  const [isSearchFocused, setIsSearchFocused] = useState(false)
  const [showWishlistOnly, setShowWishlistOnly] = useState(false)
  const [showShoppingMode, setShowShoppingMode] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('large')

  // Hooks
  const { showOnboarding, completeOnboarding } = useOnboarding()
  const { resolvedTheme, toggleTheme, mounted } = useTheme()
  const { locale, setLocale, t, localeNames } = useLocale()
  const { wishlistIds, wishlistCount, toggleWishlist, isInWishlist, downloadWishlist } = useWishlist()
  const { checkedIds, toggleCheck } = useChecklist()
  const { shareProduct } = useShare()
  const { toasts, showToast, removeToast } = useToastProvider()
  const { recentSearches, addSearch, removeSearch, clearAll: clearRecentSearches } = useRecentSearch()
  const { isOpen: isStoreLocatorOpen, filterStore, openLocator: openStoreLocator, closeLocator: closeStoreLocator } = useStoreLocator()
  const { isOpen: isScannerOpen, openScanner, closeScanner } = useBarcodeScanner()
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

  // Data Fetching
  const { data: products = [], isLoading, isError, error, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ['products'],
    queryFn: () => fetchProducts(),
  })

  // Pull-to-Refresh (모바일)
  const { pullDistance, isRefreshing } = usePullToRefresh({
    onRefresh: async () => {
      await refetch()
    },
    disabled: isFetching,
  })

  // Advanced Filters
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

  // Handlers
  const handleClearSearch = useCallback(() => setSearchQuery(''), [])

  const handleResetAll = useCallback(() => {
    setSelectedStore('all')
    setSelectedCategory('all')
    setSortBy('popular')
    setShowWishlistOnly(false)
  }, [])

  // Filtered Products
  const filteredProducts = useMemo(() => {
    let result = [...products]

    // Apply advanced filters
    result = applyFilters(result)

    // Wishlist filter
    if (showWishlistOnly) {
      result = result.filter((p: Product) => wishlistIds.includes(p.id))
    }

    // Store filter
    if (selectedStore !== 'all') {
      result = result.filter((p: Product) => p.store_key === selectedStore)
    }

    // Category filter (using centralized category matching)
    if (selectedCategory !== 'all') {
      result = result.filter((p: Product) =>
        matchesCategory(p.category, selectedCategory as CategoryKey)
      )
    }

    // Search filter (uses debounced query for better performance)
    if (debouncedSearchQuery) {
      const query = debouncedSearchQuery.toLowerCase().trim().slice(0, 100) // Limit length
      result = result.filter((p: Product) =>
        p.name.toLowerCase().includes(query) ||
        p.official_name?.toLowerCase().includes(query) ||
        p.official_code?.toLowerCase().includes(query) ||
        p.channel_title?.toLowerCase().includes(query) ||
        p.category?.toLowerCase().includes(query) ||
        (Array.isArray(p.keywords) && p.keywords.some(k => k.toLowerCase().includes(query)))
      )
    }

    // Sort
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
    } else if (sortBy === 'priceLow') {
      result.sort((a, b) => (a.price || 0) - (b.price || 0))
    } else if (sortBy === 'priceHigh') {
      result.sort((a, b) => (b.price || 0) - (a.price || 0))
    } else if (sortBy === 'salesCount') {
      result.sort((a, b) => (b.order_count || 0) - (a.order_count || 0))
    } else if (sortBy === 'reviewCount') {
      result.sort((a, b) => (b.review_count || 0) - (a.review_count || 0))
    }

    return result
  }, [products, selectedStore, selectedCategory, debouncedSearchQuery, sortBy, showWishlistOnly, wishlistIds, applyFilters])

  // Store counts
  const storeCounts = useMemo(() => {
    const counts: Record<string, number> = { all: products.length }
    products.forEach((p: Product) => {
      counts[p.store_key] = (counts[p.store_key] || 0) + 1
    })
    return counts
  }, [products])

  // Last updated time
  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
    : null

  // Hydration guard
  if (!mounted) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-orange-50 to-gray-100 dark:from-gray-900 dark:to-gray-950">
        <div className="flex items-center justify-center h-screen">
          <div className="animate-pulse text-orange-500 text-xl">...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F8F9FA] dark:bg-[#121212] transition-colors duration-300 font-['Inter',sans-serif]">
      {/* Offline Indicator */}
      <OfflineIndicator />

      {/* Pull-to-Refresh 인디케이터 */}
      <PullToRefreshIndicator
        pullDistance={pullDistance}
        isRefreshing={isRefreshing}
      />

      {/* Stitch-style Header */}
      <header className="sticky top-0 z-50 bg-[#F8F9FA]/80 dark:bg-[#121212]/80 backdrop-blur-md px-4 pt-4 pb-2">
        {/* Search Bar - Stitch style */}
        <div className="relative flex items-center mb-4">
          <span className="absolute left-3 text-slate-400 text-xl" aria-hidden="true">🔍</span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setIsSearchFocused(false)}
            placeholder={t('searchPlaceholder')}
            aria-label={t('searchPlaceholder')}
            className="w-full bg-slate-100 dark:bg-slate-800 border-none rounded-full py-2.5 pl-10 pr-12 text-sm focus:ring-2 focus:ring-[#FF4E00]/20 focus:outline-none"
          />
          <button
            onClick={() => setIsFilterOpen(true)}
            className="absolute right-3 p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label={`필터 설정${activeFilterCount > 0 ? ` (${activeFilterCount}개 적용됨)` : ''}`}
          >
            <span className="text-slate-500 text-xl" aria-hidden="true">⚙️</span>
            {activeFilterCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#FF4E00] text-white text-[10px] rounded-full flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Category Pills - Stitch style (horizontal scroll) */}
        <div className="flex items-center space-x-2 overflow-x-auto scrollbar-hide pb-2">
          {CATEGORY_KEYS.map((key) => (
            <button
              key={key}
              onClick={() => setSelectedCategory(key)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-all
                         ${selectedCategory === key
                           ? 'bg-[#FF4E00] text-white'
                           : 'bg-white dark:bg-[#1E1E1E] border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                         }`}
            >
              {FILTER_ICONS[key]} {t(key as TranslationKey)}
            </button>
          ))}
        </div>
      </header>

      {/* Main Content - Stitch style */}
      <main className="px-4">
        {/* Results summary - Stitch style */}
        <div className="flex justify-between items-center py-3">
          <div className="flex items-center gap-1">
            <span className="font-bold text-lg text-slate-900 dark:text-white">{filteredProducts.length.toLocaleString()}</span>
            <span className="text-sm text-slate-500 dark:text-slate-400">{t('productsFound')}</span>
          </div>
          <div className="flex items-center text-[11px] text-slate-400 gap-1 uppercase tracking-wider">
            <span>🕐</span>
            {lastUpdated && <span>Updated {lastUpdated}</span>}
          </div>
        </div>

        {showWishlistOnly && (
          <WishlistHeader
            wishlistCount={wishlistCount}
            products={products}
            onDownload={downloadWishlist}
            t={t}
          />
        )}

        {/* Product Grid */}
        <div className="pb-28">
          <ProductGrid
            products={filteredProducts}
            isLoading={isLoading}
            isError={isError}
            error={error as Error}
            onRetry={() => refetch()}
            isFetching={isFetching}
            isInWishlist={isInWishlist}
            onToggleWishlist={toggleWishlist}
            isInCompare={isInCompare}
            onToggleCompare={toggleCompare}
            compareCount={compareCount}
            maxCompare={maxCompareItems}
            onShare={shareProduct}
            showWishlistOnly={showWishlistOnly}
            onClearWishlistOnly={() => setShowWishlistOnly(false)}
            activeFilterCount={activeFilterCount}
            onResetFilters={resetFilters}
            onClearSearch={handleClearSearch}
            searchQuery={searchQuery}
            t={t}
            viewMode={viewMode}
            onSearchSuggestion={(query) => {
              setSearchQuery(query)
              addSearch(query)
            }}
          />
        </div>
      </main>

      {/* Stitch-style Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white/90 dark:bg-[#1E1E1E]/90 backdrop-blur-xl border-t border-slate-200 dark:border-slate-800 px-6 py-3 pb-8 flex justify-between items-center z-50" aria-label="메인 네비게이션">
        <button
          onClick={() => {
            setShowWishlistOnly(false)
            setSelectedCategory('all')
          }}
          className={`flex flex-col items-center gap-1 transition-colors min-w-[44px] min-h-[44px] justify-center ${
            !showWishlistOnly ? 'text-[#FF4E00]' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
          }`}
          aria-label="상품 탐색"
          aria-current={!showWishlistOnly ? 'page' : undefined}
        >
          <span className="text-xl" aria-hidden="true">🧭</span>
          <span className="text-[10px] font-bold">Discover</span>
        </button>

        <button
          onClick={() => setShowWishlistOnly(true)}
          className={`relative flex flex-col items-center gap-1 transition-colors min-w-[44px] min-h-[44px] justify-center ${
            showWishlistOnly ? 'text-[#FF4E00]' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
          }`}
          aria-label={`찜한 상품${wishlistCount > 0 ? ` (${wishlistCount}개)` : ''}`}
          aria-current={showWishlistOnly ? 'page' : undefined}
        >
          <span className="text-xl" aria-hidden="true">🔖</span>
          <span className="text-[10px] font-medium">Saved</span>
          {wishlistCount > 0 && (
            <span className="absolute -top-1 ml-4 w-4 h-4 bg-[#FF4E00] text-white text-[9px] rounded-full flex items-center justify-center" aria-hidden="true">
              {wishlistCount}
            </span>
          )}
        </button>

        {/* Center floating action button */}
        <div className="relative -top-4">
          <button
            onClick={() => setShowShoppingMode(true)}
            className="bg-[#FF4E00] text-white p-4 rounded-full shadow-lg shadow-[#FF4E00]/30 active:scale-95 transition-transform min-w-[56px] min-h-[56px] flex items-center justify-center"
            aria-label="쇼핑 모드 열기"
          >
            <span className="text-2xl" aria-hidden="true">➕</span>
          </button>
        </div>

        <button
          onClick={() => refetch()}
          className="flex flex-col items-center gap-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors min-w-[44px] min-h-[44px] justify-center"
          aria-label={isFetching ? '새로고침 중' : '새로고침'}
          aria-busy={isFetching}
        >
          <span className={`text-xl ${isFetching ? 'animate-spin' : ''}`} aria-hidden="true">🔄</span>
          <span className="text-[10px] font-medium">Refresh</span>
        </button>

        <button
          onClick={toggleTheme}
          className="flex flex-col items-center gap-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors min-w-[44px] min-h-[44px] justify-center"
          aria-label={resolvedTheme === 'dark' ? '라이트 모드 전환' : '다크 모드 전환'}
        >
          <span className="text-xl" aria-hidden="true">{resolvedTheme === 'dark' ? '🌙' : '☀️'}</span>
          <span className="text-[10px] font-medium">Theme</span>
        </button>
      </nav>

      {/* Floating Components */}
      <ScrollTopButton />
      <CompareFab count={compareCount} onClick={() => setShowComparePanel(!showComparePanel)} isActive={showComparePanel} />

      {/* Modals & Drawers */}
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

      <ComparePanel
        products={products}
        compareIds={compareIds}
        maxItems={maxCompareItems}
        onRemove={toggleCompare}
        onClear={clearCompare}
        onClose={() => setShowComparePanel(false)}
        isOpen={showComparePanel}
      />

      <ShoppingMode
        products={products}
        wishlistIds={wishlistIds}
        isOpen={showShoppingMode}
        onClose={() => setShowShoppingMode(false)}
        onToggleCheck={toggleCheck}
        checkedIds={checkedIds}
      />

      <StoreLocator
        isOpen={isStoreLocatorOpen}
        onClose={closeStoreLocator}
        filterStore={filterStore}
      />

      <BarcodeScanner
        isOpen={isScannerOpen}
        onClose={closeScanner}
        onScan={(code) => {
          setSearchQuery(code)
          addSearch(code)
          showToast(`바코드 "${code}" 검색`, 'success')
        }}
      />

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      {/* Onboarding */}
      {showOnboarding && <Onboarding onComplete={completeOnboarding} />}
    </div>
  )
}
