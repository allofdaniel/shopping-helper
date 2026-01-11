import type { Product, Stats } from './types'

const S3_BASE_URL = 'https://notam-korea-data.s3.ap-southeast-2.amazonaws.com/shopping-helper'
const USE_LOCAL_API = process.env.NEXT_PUBLIC_USE_LOCAL_API === 'true'

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
    // 로컬 API 사용
    if (USE_LOCAL_API) {
      const params = new URLSearchParams()
      if (opts.store && opts.store !== 'all') params.set('store', opts.store)
      if (opts.category && opts.category !== 'all') params.set('category', opts.category)
      if (opts.search) params.set('search', opts.search)
      if (opts.sort) params.set('sort', opts.sort)
      if (opts.limit) params.set('limit', opts.limit.toString())
      if (opts.offset) params.set('offset', opts.offset.toString())

      const response = await fetch(`/api/products?${params.toString()}`, {
        next: { revalidate: 60 }, // 1분 캐시
      })

      if (!response.ok) {
        throw new Error('Failed to fetch products from local API')
      }

      const data = await response.json()
      return data.products || []
    }

    // S3 정적 파일 사용 (fallback)
    const response = await fetch(`${S3_BASE_URL}/json/products_latest.json`, {
      next: { revalidate: 300 }, // 5분 캐시
    })

    if (!response.ok) {
      throw new Error('Failed to fetch products')
    }

    const data = await response.json()
    let products: Product[] = data.products || []

    // 스토어 필터
    if (opts.store && opts.store !== 'all') {
      products = products.filter((p: Product) => p.store_key === opts.store)
    }

    // 카테고리 필터
    if (opts.category && opts.category !== 'all') {
      products = products.filter((p: Product) => p.category === opts.category)
    }

    // 검색
    if (opts.search) {
      const searchLower = opts.search.toLowerCase()
      products = products.filter((p: Product) =>
        p.name.toLowerCase().includes(searchLower) ||
        p.official_name?.toLowerCase().includes(searchLower) ||
        p.channel_title?.toLowerCase().includes(searchLower)
      )
    }

    // 정렬
    switch (opts.sort) {
      case 'newest':
        products.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        break
      case 'price_low':
        products.sort((a, b) => (a.official_price || a.price || 0) - (b.official_price || b.price || 0))
        break
      case 'price_high':
        products.sort((a, b) => (b.official_price || b.price || 0) - (a.official_price || a.price || 0))
        break
      default: // popular
        products.sort((a, b) => (b.source_view_count || 0) - (a.source_view_count || 0))
    }

    return products
  } catch (error) {
    console.error('Error fetching products:', error)
    return []
  }
}

export async function fetchStats(): Promise<Stats | null> {
  try {
    // 로컬 API 사용
    if (USE_LOCAL_API) {
      const response = await fetch('/api/stats', {
        next: { revalidate: 60 },
      })

      if (!response.ok) {
        return null
      }

      return await response.json()
    }

    // S3 fallback
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
