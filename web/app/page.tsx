'use client'

// Build v2.0.1 - Search keywords fix applied
import { useState, useMemo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'

// Components
import { SearchBar } from '@/components/SearchBar'
import { HeaderActions } from '@/components/HeaderActions'
import { QuickFilters, type ViewMode } from '@/components/QuickFilters'
import { ProductGrid } from '@/components/ProductGrid'
import { ResultsSummary } from '@/components/ResultsSummary'
import { WishlistHeader } from '@/components/WishlistHeader'
import { ScrollTopButton } from '@/components/ScrollTopButton'
import { AdvancedFilterDrawer } from '@/components/AdvancedFilterDrawer'
import { ComparePanel, CompareFab } from '@/components/ComparePanel'
import { ShoppingMode } from '@/components/ShoppingMode'
import { PullToRefreshIndicator } from '@/components/PullToRefresh'
import { ToastContainer } from '@/components/Toast'

// Libs & Types
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
import { usePullToRefresh } from '@/lib/usePullToRefresh'
import { useToastProvider } from '@/lib/useToast'
import { useRecentSearch } from '@/lib/useRecentSearch'

// Constants
const CATEGORY_KEYS = ['all', 'kitchen', 'living', 'beauty', 'interior', 'food', 'digital'] as const

const FILTER_ICONS: Record<string, string> = {
  all: '',
  kitchen: '',
  living: '',
  beauty: '',
  interior: '',
  food: '',
  digital: '',
}

export default function Home() {
  // UI State
  const [selectedStore, setSelectedStore] = useState('all')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [sortBy, setSortBy] = useState('popular')
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearchFocused, setIsSearchFocused] = useState(false)
  const [showWishlistOnly, setShowWishlistOnly] = useState(false)
  const [showShoppingMode, setShowShoppingMode] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('large')

  // Hooks
  const { resolvedTheme, toggleTheme, mounted } = useTheme()
  const { locale, setLocale, t, localeNames } = useLocale()
  const { wishlistIds, wishlistCount, toggleWishlist, isInWishlist, downloadWishlist } = useWishlist()
  const { checkedIds, toggleCheck } = useChecklist()
  const { shareProduct } = useShare()
  const { toasts, showToast, removeToast } = useToastProvider()
  const { recentSearches, addSearch, removeSearch, clearAll: clearRecentSearches } = useRecentSearch()
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
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
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

    // Category filter
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

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase().trim()
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
  }, [products, selectedStore, selectedCategory, searchQuery, sortBy, showWishlistOnly, wishlistIds, applyFilters])

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
    <div className="min-h-screen bg-gradient-to-b from-orange-50 to-gray-100 dark:from-gray-900 dark:to-gray-950 transition-colors duration-300">
      {/* Pull-to-Refresh 인디케이터 */}
      <PullToRefreshIndicator
        pullDistance={pullDistance}
        isRefreshing={isRefreshing}
      />

      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md shadow-sm transition-colors">
        {/* Logo + Search + Actions */}
        <div className="flex items-center gap-1.5 px-3 py-2">
          <h1 className="text-base font-bold text-orange-500 whitespace-nowrap">

          </h1>

          <SearchBar
            value={searchQuery}
            onChange={setSearchQuery}
            onClear={handleClearSearch}
            placeholder={t('searchPlaceholder')}
            isFocused={isSearchFocused}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setIsSearchFocused(false)}
            recentSearches={recentSearches}
            onSelectRecent={addSearch}
            onRemoveRecent={removeSearch}
            onClearAllRecent={clearRecentSearches}
          />

          <HeaderActions
            wishlistCount={wishlistCount}
            onOpenShoppingMode={() => setShowShoppingMode(true)}
            activeFilterCount={activeFilterCount}
            onOpenFilter={() => setIsFilterOpen(true)}
            locale={locale}
            setLocale={setLocale}
            localeNames={localeNames}
            resolvedTheme={resolvedTheme}
            toggleTheme={toggleTheme}
            isFetching={isFetching}
            onRefetch={() => refetch()}
            t={t}
          />
        </div>

        {/* Quick Filters */}
        <QuickFilters
          sortBy={sortBy}
          setSortBy={setSortBy}
          showWishlistOnly={showWishlistOnly}
          setShowWishlistOnly={setShowWishlistOnly}
          wishlistCount={wishlistCount}
          compareCount={compareCount}
          showComparePanel={showComparePanel}
          setShowComparePanel={setShowComparePanel}
          onResetAll={handleResetAll}
          t={t}
          viewMode={viewMode}
          setViewMode={setViewMode}
        />

        {/* Store Filter */}
        <div className="overflow-x-auto scrollbar-hide border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex gap-1.5 px-4 py-2 min-w-max">
            <button
              onClick={() => setSelectedStore('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-150
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
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-150 flex items-center gap-1
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

        {/* Category Filter */}
        <div className="overflow-x-auto scrollbar-hide border-t border-gray-100 dark:border-gray-800">
          <div className="flex gap-1 px-3 py-1 min-w-max">
            {CATEGORY_KEYS.map((key) => (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`px-2 py-0.5 rounded-md text-[10px] whitespace-nowrap transition-all duration-150
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

      {/* Main Content */}
      <main className="px-3 py-3 pb-24">
        <ResultsSummary
          productCount={filteredProducts.length}
          searchQuery={searchQuery}
          activeFilterCount={activeFilterCount}
          onResetFilters={resetFilters}
          lastUpdated={lastUpdated}
          t={t}
        />

        {showWishlistOnly && (
          <WishlistHeader
            wishlistCount={wishlistCount}
            products={products}
            onDownload={downloadWishlist}
            t={t}
          />
        )}

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
        />
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-t border-gray-200 dark:border-gray-800 py-1.5 text-center z-30 transition-colors">
        <p className="text-[10px] text-gray-400 dark:text-gray-500">
          {t('appTagline')}
        </p>
      </footer>

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

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      {/* Global Styles */}
      <style jsx global>{`
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in { animation: fade-in 0.3s ease-out; }
      `}</style>
    </div>
  )
}
