import type { Product, Stats } from './types'

// API v2 - Always use local API, no S3 fallback

interface FetchProductsOptions {
  store?: string
  category?: string
  search?: string
  sort?: 'popular' | 'newest' | 'price_low' | 'price_high'
  limit?: number
  offset?: number
}

export async function fetchProducts(options: FetchProductsOptions | string = {}): Promise<Product[]> {
  // 이전 호환성: string이면 storeKey로 처리
  const opts: FetchProductsOptions = typeof options === 'string' ? { store: options } : options

  try {
    // 항상 로컬 API 사용 (Vercel serverless에서도 동작)
    const params = new URLSearchParams()
    if (opts.store && opts.store !== 'all') params.set('store', opts.store)
    if (opts.category && opts.category !== 'all') params.set('category', opts.category)
    if (opts.search) params.set('search', opts.search)
    if (opts.sort) params.set('sort', opts.sort)
    if (opts.limit) params.set('limit', opts.limit.toString())
    if (opts.offset) params.set('offset', opts.offset.toString())

    const response = await fetch(`/api/products?${params.toString()}`, {
      cache: 'no-store', // 항상 최신 데이터
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch products: ${response.status}`)
    }

    const data = await response.json()
    return data.products || []
  } catch (error) {
    console.error('Error fetching products:', error)
    return []
  }
}

export async function fetchStats(): Promise<Stats | null> {
  try {
    const response = await fetch('/api/stats', {
      cache: 'no-store',
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

/**
 * 이미지 URL 처리
 * - 다이소몰 이미지는 로컬에 다운로드된 이미지 사용 (/images/daiso/{product_no}.jpg)
 * - 그 외는 원본 URL 반환
 */
export function getProxiedImageUrl(imageUrl: string | null | undefined, productNo?: string | null): string | null {
  if (!imageUrl) return null

  try {
    const url = new URL(imageUrl)

    // 다이소몰 이미지 → 로컬 이미지 사용
    if (url.hostname.includes('daisomall.co.kr')) {
      // product_no가 제공되면 로컬 이미지 URL 반환
      if (productNo) {
        return `/images/daiso/${productNo}.jpg`
      }
      // URL에서 product_no 추출 시도 (예: /file/PD/.../1043198_00_00...)
      const match = imageUrl.match(/(\d{5,10})_\d+_\d+/)
      if (match) {
        return `/images/daiso/${match[1]}.jpg`
      }
      // 추출 실패 시 null 반환 (플레이스홀더 표시)
      return null
    }

    // 일반 이미지 - 원본 URL 반환
    return imageUrl
  } catch {
    // URL 파싱 실패 - 원본 반환
    return imageUrl
  }
}
