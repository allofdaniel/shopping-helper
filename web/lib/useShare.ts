'use client'

import { useCallback, useState } from 'react'
import type { Product } from './types'

export function useShare() {
  const [isSharing, setIsSharing] = useState(false)
  const [shareSuccess, setShareSuccess] = useState(false)

  // 상품 공유
  const shareProduct = useCallback(async (product: Product) => {
    setIsSharing(true)
    setShareSuccess(false)

    const title = product.official_name || product.name
    const price = product.official_price || product.price
    const priceText = price ? ` - ${price.toLocaleString()}원` : ''
    const text = `${title}${priceText}\n${product.store_name || product.store_key}에서 추천하는 꿀템!\n\n추천 채널: ${product.channel_title || '알 수 없음'}`

    // 공유 URL 생성 (상품 ID 포함)
    const url = typeof window !== 'undefined'
      ? `${window.location.origin}?product=${product.id}`
      : ''

    try {
      // Web Share API 지원 확인
      if (navigator.share) {
        await navigator.share({
          title: `🛒 ${title}`,
          text,
          url,
        })
        setShareSuccess(true)
      } else {
        // 클립보드에 복사
        await navigator.clipboard.writeText(`${text}\n\n${url}`)
        setShareSuccess(true)
      }
    } catch (error) {
      // 사용자가 공유를 취소하면 에러가 발생하지만 무시
      if ((error as Error).name !== 'AbortError') {
        console.error('공유 실패:', error)
      }
    } finally {
      setIsSharing(false)
      // 성공 상태 3초 후 리셋
      if (shareSuccess) {
        setTimeout(() => setShareSuccess(false), 3000)
      }
    }
  }, [shareSuccess])

  // 찜 목록 공유
  const shareWishlist = useCallback(async (products: Product[], wishlistIds: number[]) => {
    setIsSharing(true)
    setShareSuccess(false)

    const wishlistProducts = products.filter(p => wishlistIds.includes(p.id))
    if (wishlistProducts.length === 0) {
      setIsSharing(false)
      return
    }

    // 찜 목록 텍스트 생성
    const itemList = wishlistProducts.slice(0, 5).map((p, i) => {
      const name = p.official_name || p.name
      const price = p.official_price || p.price
      return `${i + 1}. ${name}${price ? ` (${price.toLocaleString()}원)` : ''}`
    }).join('\n')

    const moreText = wishlistProducts.length > 5
      ? `\n...외 ${wishlistProducts.length - 5}개`
      : ''

    const text = `🛒 나의 꿀템 위시리스트 (${wishlistProducts.length}개)\n\n${itemList}${moreText}`

    // 공유 URL 생성 (찜 목록 ID 포함)
    const url = typeof window !== 'undefined'
      ? `${window.location.origin}?wishlist=${wishlistIds.join(',')}`
      : ''

    try {
      if (navigator.share) {
        await navigator.share({
          title: '🛒 나의 꿀템 위시리스트',
          text,
          url,
        })
        setShareSuccess(true)
      } else {
        await navigator.clipboard.writeText(`${text}\n\n${url}`)
        setShareSuccess(true)
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('공유 실패:', error)
      }
    } finally {
      setIsSharing(false)
      if (shareSuccess) {
        setTimeout(() => setShareSuccess(false), 3000)
      }
    }
  }, [shareSuccess])

  // 비교 목록 공유
  const shareCompare = useCallback(async (products: Product[], compareIds: number[]) => {
    setIsSharing(true)
    setShareSuccess(false)

    const compareProducts = products.filter(p => compareIds.includes(p.id))
    if (compareProducts.length === 0) {
      setIsSharing(false)
      return
    }

    // 가격 비교 텍스트 생성
    const itemList = compareProducts.map((p, i) => {
      const name = p.official_name || p.name
      const price = p.official_price || p.price
      return `${i + 1}. ${name}\n   ${p.store_name || p.store_key} | ${price ? `${price.toLocaleString()}원` : '가격 미정'}`
    }).join('\n\n')

    // 최저가 찾기
    const prices = compareProducts
      .map(p => p.official_price || p.price)
      .filter((p): p is number => p !== null && p > 0)
    const lowestPrice = prices.length > 0 ? Math.min(...prices) : null
    const lowestPriceProduct = lowestPrice
      ? compareProducts.find(p => (p.official_price || p.price) === lowestPrice)
      : null

    const summaryText = lowestPriceProduct
      ? `\n\n👑 최저가: ${lowestPriceProduct.official_name || lowestPriceProduct.name} (${lowestPrice?.toLocaleString()}원)`
      : ''

    const text = `📊 상품 비교 (${compareProducts.length}개)\n\n${itemList}${summaryText}`

    const url = typeof window !== 'undefined'
      ? `${window.location.origin}?compare=${compareIds.join(',')}`
      : ''

    try {
      if (navigator.share) {
        await navigator.share({
          title: '📊 상품 비교',
          text,
          url,
        })
        setShareSuccess(true)
      } else {
        await navigator.clipboard.writeText(`${text}\n\n${url}`)
        setShareSuccess(true)
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('공유 실패:', error)
      }
    } finally {
      setIsSharing(false)
      if (shareSuccess) {
        setTimeout(() => setShareSuccess(false), 3000)
      }
    }
  }, [shareSuccess])

  // 현재 화면 공유
  const shareCurrentView = useCallback(async (options: {
    store?: string
    category?: string
    search?: string
    productCount: number
  }) => {
    setIsSharing(true)
    setShareSuccess(false)

    let title = '🛒 꿀템장바구니'
    let description = `${options.productCount}개의 유튜버 추천 상품`

    if (options.store && options.store !== 'all') {
      title = `🏪 ${options.store} 꿀템`
    }
    if (options.category && options.category !== 'all') {
      description = `${options.category} 카테고리 ${options.productCount}개 상품`
    }
    if (options.search) {
      description = `"${options.search}" 검색 결과 ${options.productCount}개`
    }

    const url = typeof window !== 'undefined' ? window.location.href : ''

    try {
      if (navigator.share) {
        await navigator.share({
          title,
          text: description,
          url,
        })
        setShareSuccess(true)
      } else {
        await navigator.clipboard.writeText(`${title}\n${description}\n\n${url}`)
        setShareSuccess(true)
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('공유 실패:', error)
      }
    } finally {
      setIsSharing(false)
      if (shareSuccess) {
        setTimeout(() => setShareSuccess(false), 3000)
      }
    }
  }, [shareSuccess])

  return {
    isSharing,
    shareSuccess,
    shareProduct,
    shareWishlist,
    shareCompare,
    shareCurrentView,
  }
}
