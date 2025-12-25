'use client'

import { X, Trash2, ExternalLink, Scale, Plus, ChevronUp, ChevronDown } from 'lucide-react'
import { useState, useMemo } from 'react'
import type { Product } from '@/lib/types'
import { getCompareData } from '@/lib/useCompare'
import { STORES } from '@/lib/types'

interface ComparePanelProps {
  products: Product[]
  compareIds: number[]
  maxItems: number
  onRemove: (id: number) => void
  onClear: () => void
  onClose: () => void
  isOpen: boolean
}

export function ComparePanel({
  products,
  compareIds,
  maxItems,
  onRemove,
  onClear,
  onClose,
  isOpen,
}: ComparePanelProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const compareData = useMemo(() => getCompareData(products, compareIds), [products, compareIds])

  if (!isOpen || compareIds.length === 0) return null

  const getProductImage = (product: Product) => {
    if (product.official_image_url) return product.official_image_url
    if (product.video_id) return `https://i.ytimg.com/vi/${product.video_id}/mqdefault.jpg`
    return null
  }

  const formatPrice = (product: Product) => {
    const price = product.official_price || product.price
    return price ? `${price.toLocaleString()}원` : '-'
  }

  const getLowestPrice = () => {
    if (!compareData) return null
    const prices = compareData.products
      .map((p) => p.official_price || p.price)
      .filter((p): p is number => p !== null && p > 0)
    if (prices.length === 0) return null
    return Math.min(...prices)
  }

  const lowestPrice = getLowestPrice()

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-900 shadow-2xl
                    border-t border-gray-200 dark:border-gray-800 transform transition-transform duration-300"
         style={{ transform: isExpanded ? 'translateY(0)' : 'translateY(calc(100% - 56px))' }}>

      {/* 핸들 바 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute -top-10 left-1/2 -translate-x-1/2 bg-white dark:bg-gray-900
                   px-4 py-2 rounded-t-xl shadow-lg border border-b-0 border-gray-200 dark:border-gray-800
                   flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <Scale className="w-4 h-4 text-orange-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {compareIds.length}개 상품 비교
        </span>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <Scale className="w-5 h-5 text-orange-500" />
          <h3 className="font-bold text-gray-900 dark:text-white">상품 비교</h3>
          <span className="text-xs text-gray-400">
            {compareIds.length}/{maxItems}개
          </span>
          {lowestPrice && (
            <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400
                           rounded-full text-xs font-medium">
              최저가: {lowestPrice.toLocaleString()}원
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onClear}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors
                     text-gray-400 hover:text-red-500"
            title="전체 삭제"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* 비교 테이블 */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px]">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 w-24">
                항목
              </th>
              {compareData?.products.map((product) => (
                <th key={product.id} className="px-3 py-3 text-center min-w-[140px]">
                  <div className="relative group">
                    {/* 상품 이미지 */}
                    <div className="relative w-20 h-20 mx-auto mb-2 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800">
                      {getProductImage(product) ? (
                        <img
                          src={getProductImage(product)!}
                          alt={product.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-2xl">
                          📦
                        </div>
                      )}
                      {/* 삭제 버튼 */}
                      <button
                        onClick={() => onRemove(product.id)}
                        className="absolute -top-1 -right-1 p-1 bg-red-500 text-white rounded-full
                                 opacity-0 group-hover:opacity-100 transition-opacity shadow-md"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                    {/* 상품명 */}
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 line-clamp-2 h-8">
                      {product.official_name || product.name}
                    </p>
                  </div>
                </th>
              ))}
              {/* 빈 슬롯 */}
              {[...Array(maxItems - compareIds.length)].map((_, i) => (
                <th key={`empty-${i}`} className="px-3 py-3 text-center min-w-[140px]">
                  <div className="w-20 h-20 mx-auto mb-2 rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700
                                flex items-center justify-center">
                    <Plus className="w-6 h-6 text-gray-300 dark:text-gray-600" />
                  </div>
                  <p className="text-xs text-gray-400">상품 추가</p>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {/* 가격 */}
            <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
              <td className="px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                💰 가격
              </td>
              {compareData?.products.map((product) => {
                const price = product.official_price || product.price
                const isLowest = price === lowestPrice && lowestPrice !== null
                return (
                  <td key={product.id} className="px-3 py-3 text-center">
                    <span className={`text-sm font-bold ${isLowest ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-white'}`}>
                      {formatPrice(product)}
                      {isLowest && <span className="ml-1 text-xs">👑</span>}
                    </span>
                  </td>
                )
              })}
              {[...Array(maxItems - compareIds.length)].map((_, i) => (
                <td key={`empty-price-${i}`} className="px-3 py-3 text-center text-gray-300">-</td>
              ))}
            </tr>

            {/* 매장 */}
            <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
              <td className="px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                🏪 매장
              </td>
              {compareData?.products.map((product) => {
                const store = STORES[product.store_key]
                return (
                  <td key={product.id} className="px-3 py-3 text-center">
                    <span
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs text-white"
                      style={{ backgroundColor: store?.color || '#666' }}
                    >
                      {store?.icon} {store?.name || product.store_key}
                    </span>
                  </td>
                )
              })}
              {[...Array(maxItems - compareIds.length)].map((_, i) => (
                <td key={`empty-store-${i}`} className="px-3 py-3 text-center text-gray-300">-</td>
              ))}
            </tr>

            {/* 카테고리 */}
            <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
              <td className="px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                🏷️ 카테고리
              </td>
              {compareData?.products.map((product) => (
                <td key={product.id} className="px-3 py-3 text-center text-sm text-gray-600 dark:text-gray-400">
                  {product.category || '-'}
                </td>
              ))}
              {[...Array(maxItems - compareIds.length)].map((_, i) => (
                <td key={`empty-cat-${i}`} className="px-3 py-3 text-center text-gray-300">-</td>
              ))}
            </tr>

            {/* 조회수 */}
            <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
              <td className="px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                👀 조회수
              </td>
              {compareData?.products.map((product) => {
                const views = product.source_view_count || 0
                return (
                  <td key={product.id} className="px-3 py-3 text-center text-sm text-gray-600 dark:text-gray-400">
                    {views >= 10000 ? `${Math.floor(views / 10000)}만` : views.toLocaleString()}
                  </td>
                )
              })}
              {[...Array(maxItems - compareIds.length)].map((_, i) => (
                <td key={`empty-views-${i}`} className="px-3 py-3 text-center text-gray-300">-</td>
              ))}
            </tr>

            {/* 추천 채널 */}
            <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
              <td className="px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                📺 채널
              </td>
              {compareData?.products.map((product) => (
                <td key={product.id} className="px-3 py-3 text-center text-xs text-gray-600 dark:text-gray-400 max-w-[120px] truncate">
                  {product.channel_title || '-'}
                </td>
              ))}
              {[...Array(maxItems - compareIds.length)].map((_, i) => (
                <td key={`empty-channel-${i}`} className="px-3 py-3 text-center text-gray-300">-</td>
              ))}
            </tr>

            {/* 구매 링크 */}
            <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
              <td className="px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                🔗 구매
              </td>
              {compareData?.products.map((product) => (
                <td key={product.id} className="px-3 py-3 text-center">
                  {product.official_product_url ? (
                    <a
                      href={product.official_product_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-orange-500 text-white
                               rounded-lg text-xs font-medium hover:bg-orange-600 transition-colors"
                    >
                      구매하기
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
              ))}
              {[...Array(maxItems - compareIds.length)].map((_, i) => (
                <td key={`empty-link-${i}`} className="px-3 py-3 text-center text-gray-300">-</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

// 비교 모드 FAB 버튼
export function CompareFab({
  count,
  onClick,
  isActive,
}: {
  count: number
  onClick: () => void
  isActive: boolean
}) {
  if (count === 0) return null

  return (
    <button
      onClick={onClick}
      className={`fixed bottom-20 right-4 z-40 flex items-center gap-2 px-4 py-3 rounded-full
                 shadow-lg transition-all duration-300 ${
                   isActive
                     ? 'bg-orange-500 text-white shadow-orange-500/40'
                     : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700'
                 }`}
    >
      <Scale className="w-5 h-5" />
      <span className="font-medium text-sm">비교 {count}개</span>
    </button>
  )
}
