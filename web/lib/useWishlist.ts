'use client'

import { useState, useEffect, useCallback } from 'react'
import type { Product } from './types'

const WISHLIST_KEY = 'shopping_helper_wishlist'

export interface WishlistItem {
  productId: number
  addedAt: string
}

export function useWishlist() {
  const [wishlist, setWishlist] = useState<WishlistItem[]>([])
  const [isLoaded, setIsLoaded] = useState(false)

  // 로컬스토리지에서 불러오기
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(WISHLIST_KEY)
      if (saved) {
        try {
          setWishlist(JSON.parse(saved))
        } catch {
          setWishlist([])
        }
      }
      setIsLoaded(true)
    }
  }, [])

  // 변경시 로컬스토리지에 저장
  useEffect(() => {
    if (isLoaded && typeof window !== 'undefined') {
      localStorage.setItem(WISHLIST_KEY, JSON.stringify(wishlist))
    }
  }, [wishlist, isLoaded])

  // 찜 추가
  const addToWishlist = useCallback((productId: number) => {
    setWishlist((prev) => {
      if (prev.some((item) => item.productId === productId)) {
        return prev
      }
      return [...prev, { productId, addedAt: new Date().toISOString() }]
    })
  }, [])

  // 찜 제거
  const removeFromWishlist = useCallback((productId: number) => {
    setWishlist((prev) => prev.filter((item) => item.productId !== productId))
  }, [])

  // 찜 토글
  const toggleWishlist = useCallback((productId: number) => {
    setWishlist((prev) => {
      if (prev.some((item) => item.productId === productId)) {
        return prev.filter((item) => item.productId !== productId)
      }
      return [...prev, { productId, addedAt: new Date().toISOString() }]
    })
  }, [])

  // 찜 여부 확인
  const isInWishlist = useCallback(
    (productId: number) => {
      return wishlist.some((item) => item.productId === productId)
    },
    [wishlist]
  )

  // 찜 목록 비우기
  const clearWishlist = useCallback(() => {
    setWishlist([])
  }, [])

  // 찜한 상품 ID 목록
  const wishlistIds = wishlist.map((item) => item.productId)

  // CSV 형식으로 내보내기
  const exportToCSV = useCallback((products: Product[]) => {
    const wishlistProducts = products.filter(p => wishlistIds.includes(p.id))
    if (wishlistProducts.length === 0) return null

    const headers = ['상품명', '가격', '매장', '카테고리', '품번', '구매링크']
    const rows = wishlistProducts.map(p => [
      p.official_name || p.name,
      (p.official_price || p.price || 0).toString(),
      p.store_name || p.store_key,
      p.category || '',
      p.official_code || '',
      p.official_product_url || '',
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(','))
    ].join('\n')

    return csvContent
  }, [wishlistIds])

  // 텍스트 형식으로 내보내기 (쇼핑 리스트용)
  const exportToText = useCallback((products: Product[]) => {
    const wishlistProducts = products.filter(p => wishlistIds.includes(p.id))
    if (wishlistProducts.length === 0) return null

    // 매장별로 그룹화
    const byStore: Record<string, Product[]> = {}
    wishlistProducts.forEach(p => {
      const store = p.store_name || p.store_key
      if (!byStore[store]) byStore[store] = []
      byStore[store].push(p)
    })

    let text = `🛒 나의 쇼핑 리스트 (${wishlistProducts.length}개)\n`
    text += `생성일: ${new Date().toLocaleDateString('ko-KR')}\n\n`

    Object.entries(byStore).forEach(([store, items]) => {
      text += `📍 ${store} (${items.length}개)\n`
      text += '─'.repeat(30) + '\n'
      items.forEach((p, i) => {
        const name = p.official_name || p.name
        const price = p.official_price || p.price
        text += `${i + 1}. ${name}\n`
        if (price) text += `   💰 ${price.toLocaleString()}원\n`
        if (p.official_code) text += `   📋 품번: ${p.official_code}\n`
        text += '\n'
      })
    })

    // 총 예상 금액 계산
    const totalPrice = wishlistProducts.reduce((sum, p) => sum + (p.official_price || p.price || 0), 0)
    text += `─`.repeat(30) + '\n'
    text += `💵 예상 총액: ${totalPrice.toLocaleString()}원\n`

    return text
  }, [wishlistIds])

  // 다운로드 함수
  const downloadWishlist = useCallback((products: Product[], format: 'csv' | 'text' = 'text') => {
    let content: string | null
    let filename: string
    let mimeType: string

    if (format === 'csv') {
      content = exportToCSV(products)
      filename = `wishlist_${new Date().toISOString().split('T')[0]}.csv`
      mimeType = 'text/csv;charset=utf-8'
    } else {
      content = exportToText(products)
      filename = `wishlist_${new Date().toISOString().split('T')[0]}.txt`
      mimeType = 'text/plain;charset=utf-8'
    }

    if (!content) return false

    // BOM 추가 (한글 인코딩 문제 해결)
    const BOM = '\uFEFF'
    const blob = new Blob([BOM + content], { type: mimeType })
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    return true
  }, [exportToCSV, exportToText])

  return {
    wishlist,
    wishlistIds,
    wishlistCount: wishlist.length,
    isLoaded,
    addToWishlist,
    removeFromWishlist,
    toggleWishlist,
    isInWishlist,
    clearWishlist,
    exportToCSV,
    exportToText,
    downloadWishlist,
  }
}
