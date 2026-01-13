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

// 핫링크 보호로 외부 접근이 차단된 도메인
// 이 도메인의 이미지는 null 반환하여 플레이스홀더 표시
const BLOCKED_IMAGE_DOMAINS = [
  'daisomall.co.kr',
]

/**
 * 이미지 URL 처리
 * - 핫링크 보호가 있는 사이트 (다이소몰 등)는 null 반환 → 플레이스홀더 표시
 * - 그 외는 원본 URL 반환
 */
export function getProxiedImageUrl(imageUrl: string | null | undefined): string | null {
  if (!imageUrl) return null

  try {
    const url = new URL(imageUrl)
    const isBlocked = BLOCKED_IMAGE_DOMAINS.some(domain => url.hostname.includes(domain))

    if (isBlocked) {
      // 핫링크 보호로 차단된 도메인 - 플레이스홀더 표시
      return null
    }

    // 일반 이미지 - 원본 URL 반환
    return imageUrl
  } catch {
    // URL 파싱 실패 - 원본 반환
    return imageUrl
  }
}
