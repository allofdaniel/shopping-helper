import { NextRequest, NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

const STORES = ['daiso', 'costco', 'oliveyoung', 'traders', 'ikea', 'convenience', 'youtube_products']
const VALID_SORTS = ['popular', 'price_low', 'price_high', 'newest', 'rating', 'sales_count', 'review_count']
const MAX_LIMIT = 10000
const DEFAULT_LIMIT = 10000  // 전체 상품 반환 (클라이언트에서 필터링)
const MAX_SEARCH_LENGTH = 100

// Vercel 환경 감지
const isVercel = process.env.VERCEL === '1'

// 입력값 검증 함수
function validateParams(searchParams: URLSearchParams) {
  // store 검증
  const store = searchParams.get('store')
  const validStore = (store && (STORES.includes(store) || store === 'all')) ? store : null

  // sort 검증
  const sort = searchParams.get('sort')
  const validSort = (sort && VALID_SORTS.includes(sort)) ? sort : 'popular'

  // limit 검증
  let limit = parseInt(searchParams.get('limit') || String(DEFAULT_LIMIT))
  if (isNaN(limit) || limit < 1) limit = DEFAULT_LIMIT
  if (limit > MAX_LIMIT) limit = MAX_LIMIT

  // offset 검증
  let offset = parseInt(searchParams.get('offset') || '0')
  if (isNaN(offset) || offset < 0) offset = 0

  // search 검증
  let search = searchParams.get('search')?.toLowerCase().trim()
  if (search) {
    search = search.slice(0, MAX_SEARCH_LENGTH).replace(/[<>'"`;]/g, '')
  }

  // category 검증
  let category = searchParams.get('category')?.trim()
  if (category) {
    category = category.slice(0, 50).replace(/[<>'"`;]/g, '')
  }

  return { store: validStore, sort: validSort, limit, offset, search, category }
}

// 전체 상품 캐시
let allProductsCache: any[] | null = null
let cacheLoadedAt = 0
const CACHE_TTL = 5 * 60 * 1000

// HTTP로 JSON 파일 로드 (Vercel 환경)
async function loadProductsViaHttp(store: string, baseUrl: string): Promise<any[]> {
  try {
    const response = await fetch(`${baseUrl}/data/${store}.json`, {
      cache: 'no-store',
    })

    if (!response.ok) {
      console.error(`HTTP fetch failed for ${store}: ${response.status}`)
      return []
    }

    const data = await response.json()
    return data.products || []
  } catch (error) {
    console.error(`Failed to fetch ${store} via HTTP:`, error)
    return []
  }
}

// 파일 시스템으로 JSON 로드 (로컬 환경)
async function loadProductsViaFs(store: string): Promise<any[]> {
  try {
    const jsonPath = path.join(process.cwd(), 'public', 'data', `${store}.json`)
    const content = await fs.readFile(jsonPath, 'utf-8')
    const data = JSON.parse(content)
    return data.products || []
  } catch (error) {
    console.error(`Failed to load ${store} via FS:`, error)
    return []
  }
}

// 중복 제거 함수
function deduplicateProducts(products: any[]): any[] {
  const seen = new Map<string, any>()

  for (const product of products) {
    // 고유 키: store_key + (official_code 또는 name)
    const name = product.official_name || product.name || ''
    const code = product.official_code || product.product_no || ''
    const key = `${product.store_key}:${code || name.toLowerCase()}`

    // 이미 존재하면 더 완성도 높은 것 유지
    if (seen.has(key)) {
      const existing = seen.get(key)
      // 이미지가 있는 것, 가격이 있는 것 우선
      const existingScore = (existing.image_url ? 1 : 0) + (existing.official_price ? 1 : 0) + (existing.rating ? 1 : 0)
      const newScore = (product.image_url ? 1 : 0) + (product.official_price ? 1 : 0) + (product.rating ? 1 : 0)
      if (newScore > existingScore) {
        seen.set(key, product)
      }
    } else {
      seen.set(key, product)
    }
  }

  return Array.from(seen.values())
}

async function loadAllProducts(baseUrl?: string) {
  if (allProductsCache && Date.now() - cacheLoadedAt < CACHE_TTL) {
    return allProductsCache
  }

  // 병렬 로드로 성능 최적화 (N+1 문제 해결)
  const loadResults = await Promise.all(
    STORES.map(async (store) => {
      try {
        let products: any[] = []
        // Vercel 환경에서는 HTTP로, 로컬에서는 파일 시스템으로 로드
        if (isVercel && baseUrl) {
          products = await loadProductsViaHttp(store, baseUrl)
        } else {
          products = await loadProductsViaFs(store)
        }
        return products.map(product => ({
          ...product,
          store_key: product.store_key || store,
          store_name: product.store_name || getStoreName(store),
        }))
      } catch (err) {
        console.error(`[API] Failed to load ${store}:`, err)
        return []
      }
    })
  )

  const allProducts = loadResults.flat()

  // 중복 제거
  const deduplicated = deduplicateProducts(allProducts)

  allProductsCache = deduplicated
  cacheLoadedAt = Date.now()
  console.log(`[API] Loaded ${allProducts.length} products, after dedup: ${deduplicated.length} (Vercel: ${isVercel})`)
  return deduplicated
}

function getStoreName(key: string): string {
  const names: Record<string, string> = {
    daiso: '다이소',
    costco: 'Costco',
    oliveyoung: '올리브영',
    traders: '트레이더스',
    ikea: 'IKEA',
    convenience: '편의점',
    youtube_products: 'YouTube 추천',
  }
  return names[key] || key
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const url = new URL(request.url)
    const baseUrl = `${url.protocol}//${url.host}`

    // 검증된 파라미터 사용
    const { store, category, search, sort, limit, offset } = validateParams(searchParams)

    let products = await loadAllProducts(baseUrl)

    // 매장 필터
    if (store && store !== 'all') {
      products = products.filter(p => p.store_key === store)
    }

    // 카테고리 필터
    if (category && category !== 'all') {
      products = products.filter(p =>
        p.category?.toLowerCase().includes(category.toLowerCase())
      )
    }

    // 검색 (name, brand, category, keywords, official_name, official_code 포함)
    if (search) {
      products = products.filter(p => {
        if (p.name?.toLowerCase().includes(search)) return true
        if (p.brand?.toLowerCase().includes(search)) return true
        if (p.category?.toLowerCase().includes(search)) return true
        if (p.official_name?.toLowerCase().includes(search)) return true
        if (p.official_code?.toLowerCase().includes(search)) return true
        if (p.channel_title?.toLowerCase().includes(search)) return true
        // keywords 배열 검색
        if (Array.isArray(p.keywords)) {
          return p.keywords.some((k: string) => k.toLowerCase().includes(search))
        }
        return false
      })
    }

    // 정렬
    switch (sort) {
      case 'price_low':
        products = [...products].sort((a, b) => (a.price || 0) - (b.price || 0))
        break
      case 'price_high':
        products = [...products].sort((a, b) => (b.price || 0) - (a.price || 0))
        break
      case 'newest':
        products = [...products].sort((a, b) =>
          new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        )
        break
      case 'rating':
        products = [...products].sort((a, b) => (b.rating || 0) - (a.rating || 0))
        break
      case 'sales_count':
        products = [...products].sort((a, b) => (b.order_count || 0) - (a.order_count || 0))
        break
      case 'review_count':
        products = [...products].sort((a, b) => (b.review_count || 0) - (a.review_count || 0))
        break
      default:
        // popular - 조회수 기준 정렬
        products = [...products].sort((a, b) => (b.source_view_count || 0) - (a.source_view_count || 0))
        break
    }

    const total = products.length
    const paginated = products.slice(offset, offset + limit)

    return NextResponse.json({
      products: paginated,
      total,
      limit,
      offset,
      hasMore: offset + paginated.length < total,
    })

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', products: [] },
      { status: 500 }
    )
  }
}
