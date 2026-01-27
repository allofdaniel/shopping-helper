'use client'

import { useState, useCallback, useMemo } from 'react'
import type { Product } from './types'
import { matchesCategory, type CategoryKey } from './categoryUtils'

export interface FilterState {
  priceRange: [number, number]
  minViews: number
  hasRecommendation: boolean
  hasOfficialMatch: boolean
  dateRange: 'all' | 'week' | 'month' | '3months'
  stores: string[]
  categories: string[]
}

export const DEFAULT_FILTERS: FilterState = {
  priceRange: [0, 100000],
  minViews: 0,
  hasRecommendation: false,
  hasOfficialMatch: false,
  dateRange: 'all',
  stores: [],
  categories: [],
}

export function useAdvancedFilters(products: Product[]) {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS)
  const [isOpen, setIsOpen] = useState(false)

  // 가격 범위 계산
  const priceStats = useMemo(() => {
    const prices = products
      .map((p) => p.official_price || p.price || 0)
      .filter((p) => p > 0)
    return {
      min: prices.length > 0 ? prices.reduce((a, b) => a < b ? a : b, Infinity) : 0,
      max: prices.length > 0 ? prices.reduce((a, b) => a > b ? a : b, -Infinity) : 100000,
      avg: prices.length > 0 ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0,
    }
  }, [products])

  // 조회수 범위 계산
  const viewStats = useMemo(() => {
    const views = products.map((p) => p.source_view_count || 0)
    return {
      min: views.length > 0 ? views.reduce((a, b) => a < b ? a : b, Infinity) : 0,
      max: views.length > 0 ? views.reduce((a, b) => a > b ? a : b, -Infinity) : 10000000,
    }
  }, [products])

  // 필터 업데이트
  const updateFilter = useCallback(<K extends keyof FilterState>(
    key: K,
    value: FilterState[K]
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }, [])

  // 필터 초기화
  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS)
  }, [])

  // 활성 필터 개수
  const activeFilterCount = useMemo(() => {
    let count = 0
    if (filters.priceRange[0] > 0 || filters.priceRange[1] < 100000) count++
    if (filters.minViews > 0) count++
    if (filters.hasRecommendation) count++
    if (filters.hasOfficialMatch) count++
    if (filters.dateRange !== 'all') count++
    if (filters.stores.length > 0) count++
    if (filters.categories.length > 0) count++
    return count
  }, [filters])

  // 필터링 적용
  const applyFilters = useCallback((productList: Product[]): Product[] => {
    return productList.filter((product) => {
      // 가격 필터
      const price = product.official_price || product.price || 0
      if (price > 0) {
        if (price < filters.priceRange[0] || price > filters.priceRange[1]) {
          return false
        }
      }

      // 조회수 필터
      if (filters.minViews > 0 && (product.source_view_count || 0) < filters.minViews) {
        return false
      }

      // 추천 코멘트 필터
      if (filters.hasRecommendation && !product.recommendation_quote) {
        return false
      }

      // 공식 매칭 필터
      if (filters.hasOfficialMatch && !product.is_matched) {
        return false
      }

      // 날짜 필터
      if (filters.dateRange !== 'all') {
        const productDate = new Date(product.created_at)
        const now = new Date()
        const diffDays = Math.floor((now.getTime() - productDate.getTime()) / (1000 * 60 * 60 * 24))

        if (filters.dateRange === 'week' && diffDays > 7) return false
        if (filters.dateRange === 'month' && diffDays > 30) return false
        if (filters.dateRange === '3months' && diffDays > 90) return false
      }

      // 스토어 필터
      if (filters.stores.length > 0 && !filters.stores.includes(product.store_key)) {
        return false
      }

      // 카테고리 필터 (using centralized category matching)
      if (filters.categories.length > 0) {
        const matched = filters.categories.some((filterCat) =>
          matchesCategory(product.category, filterCat as CategoryKey)
        )
        if (!matched) return false
      }

      return true
    })
  }, [filters])

  return {
    filters,
    updateFilter,
    resetFilters,
    activeFilterCount,
    applyFilters,
    priceStats,
    viewStats,
    isOpen,
    setIsOpen,
  }
}
