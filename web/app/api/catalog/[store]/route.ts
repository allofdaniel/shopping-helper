import { NextRequest, NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

// Product type for API responses
interface CatalogProduct {
  id?: number
  name?: string
  brand?: string
  category?: string
  price?: number
  [key: string]: unknown
}

// 지원하는 매장 목록
const VALID_STORES = ['daiso', 'costco', 'oliveyoung', 'traders', 'ikea', 'convenience', 'cu', 'gs25', 'seveneleven', 'emart24', 'youtube_products']

// 입력값 제한
const MAX_LIMIT = 100
const DEFAULT_LIMIT = 50
const MAX_SEARCH_LENGTH = 100
const MAX_CATEGORY_LENGTH = 50

// 입력값 검증 함수
function validateAndSanitizeParams(searchParams: URLSearchParams) {
  // limit 검증 (1-100)
  let limit = parseInt(searchParams.get('limit') || String(DEFAULT_LIMIT))
  if (isNaN(limit) || limit < 1) limit = DEFAULT_LIMIT
  if (limit > MAX_LIMIT) limit = MAX_LIMIT

  // offset 검증 (0 이상)
  let offset = parseInt(searchParams.get('offset') || '0')
  if (isNaN(offset) || offset < 0) offset = 0

  // search 검증 (길이 제한 및 특수문자 제거)
  let search = searchParams.get('search')?.toLowerCase().trim()
  if (search) {
    search = search.slice(0, MAX_SEARCH_LENGTH)
    // SQL 인젝션 방지용 특수문자 제거 (JSON 필터링이므로 큰 위험은 없지만 방어적 코딩)
    search = search.replace(/[<>'"`;]/g, '')
  }

  // category 검증
  let category = searchParams.get('category')?.trim()
  if (category) {
    category = category.slice(0, MAX_CATEGORY_LENGTH)
    category = category.replace(/[<>'"`;]/g, '')
  }

  return { limit, offset, search, category }
}

// JSON 데이터 캐시
const dataCache: Record<string, { products: CatalogProduct[]; total: number; loadedAt: number }> = {}
const CACHE_TTL = 5 * 60 * 1000 // 5분

async function loadStoreData(store: string) {
  // 캐시 확인
  const cached = dataCache[store]
  if (cached && Date.now() - cached.loadedAt < CACHE_TTL) {
    return cached
  }

  // JSON 파일 경로
  const jsonPath = path.join(process.cwd(), 'public', 'data', `${store}.json`)

  try {
    const fileContent = await fs.readFile(jsonPath, 'utf-8')
    const data = JSON.parse(fileContent)

    const result = {
      products: data.products || [],
      total: data.total || data.products?.length || 0,
      loadedAt: Date.now()
    }

    dataCache[store] = result
    return result
  } catch (error) {
    console.error(`Failed to load ${store} data:`, error)
    return { products: [], total: 0, loadedAt: Date.now() }
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: { store: string } }
) {
  try {
    const store = params.store
    const { searchParams } = new URL(request.url)

    // 검증된 파라미터 사용
    const { limit, offset, search, category } = validateAndSanitizeParams(searchParams)

    // 매장 유효성 검사
    if (!VALID_STORES.includes(store)) {
      return NextResponse.json(
        { error: `Unknown store: ${store}`, products: [] },
        { status: 400 }
      )
    }

    // 데이터 로드
    const storeData = await loadStoreData(store)

    if (!storeData.products.length) {
      return NextResponse.json({
        store,
        products: [],
        total: 0,
        message: `No data available for ${store}`,
      })
    }

    // 필터링
    let filtered = storeData.products

    if (search) {
      filtered = filtered.filter((p: CatalogProduct) =>
        p.name?.toLowerCase().includes(search) ||
        p.brand?.toLowerCase().includes(search)
      )
    }

    if (category) {
      filtered = filtered.filter((p: CatalogProduct) =>
        p.category?.toLowerCase().includes(category.toLowerCase())
      )
    }

    const total = filtered.length

    // 페이지네이션
    const paginated = filtered.slice(offset, offset + limit)

    return NextResponse.json({
      store,
      products: paginated,
      total,
      limit,
      offset,
      hasMore: offset + paginated.length < total,
    })

  } catch (error) {
    console.error('Catalog API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', products: [] },
      { status: 500 }
    )
  }
}
