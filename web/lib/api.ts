import type { Product, Stats } from './types'

const S3_BASE_URL = 'https://notam-korea-data.s3.ap-northeast-2.amazonaws.com/shopping-helper'

export async function fetchProducts(storeKey?: string): Promise<Product[]> {
  try {
    const response = await fetch(`${S3_BASE_URL}/json/products_latest.json`, {
      next: { revalidate: 300 }, // 5분 캐시
    })

    if (!response.ok) {
      throw new Error('Failed to fetch products')
    }

    const data = await response.json()
    let products: Product[] = data.products || []

    // 스토어 필터
    if (storeKey && storeKey !== 'all') {
      products = products.filter((p: Product) => p.store_key === storeKey)
    }

    // 승인된 상품만 (또는 매칭된 상품)
    products = products.filter((p: Product) => p.is_approved || p.is_matched)

    // 인기순 정렬
    products.sort((a: Product, b: Product) => (b.source_view_count || 0) - (a.source_view_count || 0))

    return products
  } catch (error) {
    console.error('Error fetching products:', error)
    return []
  }
}

export async function fetchStats(): Promise<Stats | null> {
  try {
    const response = await fetch(`${S3_BASE_URL}/json/stats_latest.json`, {
      next: { revalidate: 300 },
    })

    if (!response.ok) {
      return null
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching stats:', error)
    return null
  }
}

export function getYoutubeVideoUrl(videoId: string, timestamp?: number): string {
  let url = `https://www.youtube.com/watch?v=${videoId}`
  if (timestamp) {
    url += `&t=${timestamp}s`
  }
  return url
}

export function getYoutubeThumbnail(videoId: string): string {
  return `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`
}

export function formatPrice(price: number | null | undefined): string {
  if (price == null) return '가격 미정'
  return new Intl.NumberFormat('ko-KR').format(price) + '원'
}

export function formatViewCount(count: number): string {
  if (count >= 10000) {
    return (count / 10000).toFixed(1) + '만'
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1) + '천'
  }
  return count.toString()
}
