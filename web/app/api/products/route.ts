import { NextRequest, NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

const STORES = ['daiso', 'costco', 'oliveyoung', 'traders', 'ikea', 'convenience']
const VALID_SORTS = ['popular', 'price_low', 'price_high', 'newest', 'rating']
const MAX_LIMIT = 200
const DEFAULT_LIMIT = 100
const MAX_SEARCH_LENGTH = 100

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

async function loadAllProducts() {
  if (allProductsCache && Date.now() - cacheLoadedAt < CACHE_TTL) {
    return allProductsCache
  }

  const allProducts: any[] = []

  for (const store of STORES) {
    try {
      const jsonPath = path.join(process.cwd(), 'public', 'data', `${store}.json`)
      const content = await fs.readFile(jsonPath, 'utf-8')
      const data = JSON.parse(content)

      if (data.products) {
        for (const product of data.products) {
          allProducts.push({
            ...product,
            store_key: store,
            store_name: getStoreName(store),
          })
        }
      }
    } catch (error) {
      console.error(`Failed to load ${store}:`, error)
    }
  }

  allProductsCache = allProducts
  cacheLoadedAt = Date.now()
  return allProducts
}

function getStoreName(key: string): string {
  const names: Record<string, string> = {
    daiso: '다이소',
    costco: 'Costco',
    oliveyoung: '올리브영',
    traders: '트레이더스',
    ikea: 'IKEA',
    convenience: '편의점',
  }
  return names[key] || key
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)

    // 검증된 파라미터 사용
    const { store, category, search, sort, limit, offset } = validateParams(searchParams)

    let products = await loadAllProducts()

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

    // 검색
    if (search) {
      products = products.filter(p =>
        p.name?.toLowerCase().includes(search) ||
        p.brand?.toLowerCase().includes(search) ||
        p.category?.toLowerCase().includes(search)
      )
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
      default:
        // popular - 기본 순서 유지
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
