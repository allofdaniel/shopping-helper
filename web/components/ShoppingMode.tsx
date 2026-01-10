'use client'

import { useState, useMemo, useCallback } from 'react'
import {
  ShoppingCart, Check, Copy, ExternalLink, ChevronDown, ChevronUp,
  MapPin, Search, X, CheckCircle2, Circle, Store, Tag, Clock
} from 'lucide-react'
import type { Product } from '@/lib/types'
import { STORES } from '@/lib/types'
import { formatPrice } from '@/lib/api'
import { useTranslation } from '@/lib/i18n'

interface ShoppingModeProps {
  products: Product[]
  wishlistIds: number[]
  isOpen: boolean
  onClose: () => void
  onToggleCheck: (productId: number) => void
  checkedIds: number[]
}

// 매장별 검색 URL 생성
const getStoreSearchUrl = (storeKey: string, query: string): string | null => {
  const encodedQuery = encodeURIComponent(query)

  switch (storeKey) {
    case 'daiso':
      return `https://www.daiso.co.kr/search?keyword=${encodedQuery}`
    case 'costco':
      return `https://www.costco.co.kr/search?text=${encodedQuery}`
    case 'ikea':
      return `https://www.ikea.com/kr/ko/search/?q=${encodedQuery}`
    case 'oliveyoung':
      return `https://www.oliveyoung.co.kr/store/search/getSearchMain.do?query=${encodedQuery}`
    case 'artbox':
      return `https://www.artbox.co.kr/search?q=${encodedQuery}`
    case 'cu':
      return `https://cu.bgfretail.com/product/search.do?searchKeyword=${encodedQuery}`
    case 'gs25':
      return `https://gs25.gsretail.com/gscvs/ko/products/search?keyword=${encodedQuery}`
    case 'seveneleven':
      return `https://www.7-eleven.co.kr/product/search.asp?keyword=${encodedQuery}`
    case 'emart24':
      return `https://emart24.co.kr/product/search?keyword=${encodedQuery}`
    default:
      return null
  }
}

export function ShoppingMode({
  products,
  wishlistIds,
  isOpen,
  onClose,
  onToggleCheck,
  checkedIds,
}: ShoppingModeProps) {
  const { t } = useTranslation()
  const [expandedStore, setExpandedStore] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [searchInStore, setSearchInStore] = useState<string>('')

  // 찜한 상품만 필터링 후 매장별 그룹화
  const groupedByStore = useMemo(() => {
    const wishlistProducts = products.filter(p => wishlistIds.includes(p.id))
    const groups: Record<string, Product[]> = {}

    wishlistProducts.forEach(p => {
      const key = p.store_key
      if (!groups[key]) groups[key] = []
      groups[key].push(p)
    })

    // 매장별 정렬
    const order = ['daiso', 'costco', 'ikea', 'oliveyoung', 'cu', 'gs25', 'seveneleven', 'emart24', 'convenience', 'artbox']
    const sorted = Object.entries(groups).sort(([a], [b]) => {
      return order.indexOf(a) - order.indexOf(b)
    })

    return sorted
  }, [products, wishlistIds])

  // 전체 통계
  const stats = useMemo(() => {
    const total = wishlistIds.length
    const checked = checkedIds.filter(id => wishlistIds.includes(id)).length
    const totalPrice = products
      .filter(p => wishlistIds.includes(p.id))
      .reduce((sum, p) => sum + (p.official_price || p.price || 0), 0)

    return { total, checked, remaining: total - checked, totalPrice }
  }, [products, wishlistIds, checkedIds])

  // 품번 복사
  const handleCopyCode = useCallback(async (product: Product, e: React.MouseEvent) => {
    e.stopPropagation()
    const code = product.official_code || product.name
    try {
      await navigator.clipboard.writeText(code)
      setCopiedId(product.id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [])

  // 매장 검색창에서 검색
  const filteredGroups = useMemo(() => {
    if (!searchInStore) return groupedByStore

    const query = searchInStore.toLowerCase()
    return groupedByStore.map(([storeKey, items]) => {
      const filtered = items.filter(p =>
        p.name.toLowerCase().includes(query) ||
        p.official_name?.toLowerCase().includes(query) ||
        p.official_code?.toLowerCase().includes(query)
      )
      return [storeKey, filtered] as [string, Product[]]
    }).filter(([, items]) => items.length > 0)
  }, [groupedByStore, searchInStore])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[9999] bg-black/60 flex items-end sm:items-center justify-center">
      <div
        className="bg-white dark:bg-gray-900 w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl max-h-[95vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="sticky top-0 bg-white dark:bg-gray-900 border-b dark:border-gray-800 px-3 py-2.5 flex items-center justify-between z-10 rounded-t-2xl">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 bg-gradient-to-br from-orange-400 to-red-500 rounded-xl flex items-center justify-center">
              <ShoppingCart className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-sm text-gray-900 dark:text-white">
                {t('shoppingChecklist')}
              </h2>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">
                {t('checkAtStore')}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* 진행 상황 바 */}
        <div className="px-3 py-2 bg-gradient-to-r from-orange-50 to-yellow-50 dark:from-orange-900/20 dark:to-yellow-900/20 border-b dark:border-gray-800">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              {stats.checked} / {stats.total} {t('completed')}
            </span>
            <span className="text-xs font-bold text-orange-600 dark:text-orange-400">
              {stats.total > 0 ? Math.round((stats.checked / stats.total) * 100) : 0}%
            </span>
          </div>
          <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-orange-400 to-red-500 transition-all duration-500"
              style={{ width: `${stats.total > 0 ? (stats.checked / stats.total) * 100 : 0}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-1.5 text-[10px] text-gray-500 dark:text-gray-400">
            <span>{t('remaining')}: {stats.remaining}</span>
            <span>{t('estimatedTotal')}: {formatPrice(stats.totalPrice)}</span>
          </div>
        </div>

        {/* 검색 */}
        <div className="px-3 py-1.5 border-b dark:border-gray-800">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input
              type="text"
              placeholder={t('searchInStore')}
              value={searchInStore}
              onChange={(e) => setSearchInStore(e.target.value)}
              className="w-full pl-8 pr-7 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs
                       text-gray-900 dark:text-white placeholder-gray-400
                       focus:outline-none focus:ring-2 focus:ring-orange-400"
            />
            {searchInStore && (
              <button
                onClick={() => setSearchInStore('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5"
              >
                <X className="w-3.5 h-3.5 text-gray-400" />
              </button>
            )}
          </div>
        </div>

        {/* 매장별 리스트 */}
        <div className="flex-1 overflow-y-auto">
          {filteredGroups.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <ShoppingCart className="w-10 h-10 mb-2 opacity-50" />
              <p className="text-xs">{t('noWishlist')}</p>
              <p className="text-[10px] mt-0.5">{t('addSomeProducts')}</p>
            </div>
          ) : (
            filteredGroups.map(([storeKey, items]) => {
              const store = STORES[storeKey]
              const isExpanded = expandedStore === storeKey || expandedStore === null
              const storeChecked = items.filter(p => checkedIds.includes(p.id)).length

              return (
                <div key={storeKey} className="border-b dark:border-gray-800 last:border-0">
                  {/* 매장 헤더 */}
                  <button
                    onClick={() => setExpandedStore(expandedStore === storeKey ? null : storeKey)}
                    className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
                        style={{ backgroundColor: store?.color || '#666' }}
                      >
                        {store?.icon}
                      </div>
                      <div className="text-left">
                        <h3 className="font-bold text-sm text-gray-900 dark:text-white">
                          {store?.name || storeKey}
                        </h3>
                        <p className="text-[10px] text-gray-500 dark:text-gray-400">
                          {storeChecked}/{items.length} {t('completed')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {/* 매장 검색 링크 */}
                      {getStoreSearchUrl(storeKey, '') && (
                        <a
                          href={getStoreSearchUrl(storeKey, '') || '#'}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
                        >
                          <Store className="w-3.5 h-3.5 text-gray-600 dark:text-gray-400" />
                        </a>
                      )}
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  </button>

                  {/* 상품 리스트 */}
                  {isExpanded && (
                    <div className="px-3 pb-2 space-y-1.5">
                      {items.map((product) => {
                        const isChecked = checkedIds.includes(product.id)
                        const searchUrl = getStoreSearchUrl(
                          storeKey,
                          product.official_code || product.official_name || product.name
                        )

                        return (
                          <div
                            key={product.id}
                            className={`flex items-start gap-2 p-2 rounded-lg border transition-all
                                      ${isChecked
                                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                                        : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700'}`}
                          >
                            {/* 체크 버튼 */}
                            <button
                              onClick={() => onToggleCheck(product.id)}
                              className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center transition-all
                                        ${isChecked
                                          ? 'bg-green-500 text-white'
                                          : 'border-2 border-gray-300 dark:border-gray-600'}`}
                            >
                              {isChecked && <Check className="w-3 h-3" />}
                            </button>

                            {/* 상품 정보 */}
                            <div className="flex-1 min-w-0">
                              <h4 className={`font-medium text-xs leading-tight mb-0.5
                                            ${isChecked ? 'line-through text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                                {product.official_name || product.name}
                              </h4>

                              <div className="flex flex-wrap items-center gap-1.5">
                                {/* 가격 */}
                                <span className={`text-xs font-bold ${isChecked ? 'text-gray-400' : 'text-red-500'}`}>
                                  {formatPrice(product.official_price || product.price)}
                                </span>

                                {/* 품번 */}
                                {product.official_code && (
                                  <button
                                    onClick={(e) => handleCopyCode(product, e)}
                                    className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] transition-all
                                              ${copiedId === product.id
                                                ? 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400'
                                                : 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800'}`}
                                  >
                                    <Tag className="w-2.5 h-2.5" />
                                    {copiedId === product.id ? t('copied') : product.official_code}
                                    {copiedId !== product.id && <Copy className="w-2.5 h-2.5" />}
                                  </button>
                                )}
                              </div>
                            </div>

                            {/* 매장 검색 링크 */}
                            {searchUrl && (
                              <a
                                href={searchUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-shrink-0 p-1.5 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-600 transition-colors"
                                title={t('searchInStore')}
                              >
                                <ExternalLink className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
                              </a>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>

        {/* 하단 안내 */}
        <div className="sticky bottom-0 px-3 py-2 bg-gray-50 dark:bg-gray-800 border-t dark:border-gray-700 text-center">
          <p className="text-[10px] text-gray-500 dark:text-gray-400">
            <MapPin className="w-2.5 h-2.5 inline mr-0.5" />
            {t('checkWhenFound')}
          </p>
        </div>
      </div>

      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); opacity: 0.5; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
