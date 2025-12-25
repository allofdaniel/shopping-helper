'use client'

import { useState, useCallback, useMemo } from 'react'
import type { Product } from './types'

const MAX_COMPARE_ITEMS = 4
const COMPARE_KEY = 'shopping_helper_compare'

export function useCompare() {
  const [compareIds, setCompareIds] = useState<number[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(COMPARE_KEY)
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch {
          return []
        }
      }
    }
    return []
  })

  const [isCompareMode, setIsCompareMode] = useState(false)
  const [showComparePanel, setShowComparePanel] = useState(false)

  // 비교 목록에 추가/제거
  const toggleCompare = useCallback((productId: number) => {
    setCompareIds((prev) => {
      let next: number[]
      if (prev.includes(productId)) {
        next = prev.filter((id) => id !== productId)
      } else {
        if (prev.length >= MAX_COMPARE_ITEMS) {
          // 최대 개수 초과시 가장 오래된 것 제거
          next = [...prev.slice(1), productId]
        } else {
          next = [...prev, productId]
        }
      }
      if (typeof window !== 'undefined') {
        localStorage.setItem(COMPARE_KEY, JSON.stringify(next))
      }
      return next
    })
  }, [])

  // 비교 목록에 있는지 확인
  const isInCompare = useCallback((productId: number) => {
    return compareIds.includes(productId)
  }, [compareIds])

  // 비교 목록 초기화
  const clearCompare = useCallback(() => {
    setCompareIds([])
    if (typeof window !== 'undefined') {
      localStorage.removeItem(COMPARE_KEY)
    }
    setShowComparePanel(false)
  }, [])

  // 비교 모드 토글
  const toggleCompareMode = useCallback(() => {
    setIsCompareMode((prev) => !prev)
    if (isCompareMode) {
      setShowComparePanel(false)
    }
  }, [isCompareMode])

  // 비교 패널 열기/닫기
  const toggleComparePanel = useCallback(() => {
    setShowComparePanel((prev) => !prev)
  }, [])

  return {
    compareIds,
    compareCount: compareIds.length,
    maxCompareItems: MAX_COMPARE_ITEMS,
    isCompareMode,
    showComparePanel,
    toggleCompare,
    isInCompare,
    clearCompare,
    toggleCompareMode,
    toggleComparePanel,
    setShowComparePanel,
  }
}

// 상품 비교 데이터 구조화
export function getCompareData(products: Product[], compareIds: number[]) {
  const compareProducts = compareIds
    .map((id) => products.find((p) => p.id === id))
    .filter((p): p is Product => p !== undefined)

  if (compareProducts.length === 0) return null

  // 비교 항목들
  const fields = [
    { key: 'price', label: '가격', format: (p: Product) => {
      const price = p.official_price || p.price
      return price ? `${price.toLocaleString()}원` : '-'
    }},
    { key: 'store', label: '매장', format: (p: Product) => p.store_name || p.store_key },
    { key: 'category', label: '카테고리', format: (p: Product) => p.category || '-' },
    { key: 'views', label: '영상 조회수', format: (p: Product) => {
      const views = p.source_view_count || 0
      if (views >= 10000) return `${Math.floor(views / 10000)}만`
      return views.toLocaleString()
    }},
    { key: 'matched', label: '공식 매칭', format: (p: Product) => p.is_matched ? '✓' : '-' },
    { key: 'recommendation', label: '추천 코멘트', format: (p: Product) => p.recommendation_quote ? '있음' : '-' },
    { key: 'channel', label: '추천 채널', format: (p: Product) => p.channel_title || '-' },
  ]

  return { products: compareProducts, fields }
}
