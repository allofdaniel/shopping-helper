import { NextRequest, NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

// 지원하는 매장 목록
const VALID_STORES = ['daiso', 'costco', 'oliveyoung', 'traders', 'ikea', 'convenience']

// JSON 데이터 캐시
const dataCache: Record<string, { products: any[]; total: number; loadedAt: number }> = {}
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

    const search = searchParams.get('search')?.toLowerCase()
    const category = searchParams.get('category')
    const limit = parseInt(searchParams.get('limit') || '50')
    const offset = parseInt(searchParams.get('offset') || '0')

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
      filtered = filtered.filter((p: any) =>
        p.name?.toLowerCase().includes(search) ||
        p.brand?.toLowerCase().includes(search)
      )
    }

    if (category) {
      filtered = filtered.filter((p: any) =>
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
