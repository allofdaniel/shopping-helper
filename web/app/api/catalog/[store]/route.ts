import { NextRequest, NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

interface CatalogProduct {
  id?: number
  name?: string
  brand?: string
  category?: string
  price?: number
  [key: string]: unknown
}

const VALID_STORES = [
  'daiso',
  'costco',
  'oliveyoung',
  'traders',
  'ikea',
  'convenience',
  'cu',
  'gs25',
  'seveneleven',
  'emart24',
  'youtube_products',
]

const STORES_SET = new Set(VALID_STORES)
const MAX_LIMIT = 100
const DEFAULT_LIMIT = 50
const MAX_SEARCH_LENGTH = 100
const MAX_CATEGORY_LENGTH = 50
const MAX_OFFSET = 100000
const MAX_STORE_LENGTH = 40

interface StoreDataCache {
  products: CatalogProduct[]
  total: number
  loadedAt: number
  fingerprint: string
}

function sanitizeText(value: string | null, maxLength: number): string {
  if (!value) return ''
  const trimmed = value.trim().slice(0, maxLength)
  return trimmed.replace(/[<>'"`;]/g, '')
}

function validateAndSanitizeParams(searchParams: URLSearchParams) {
  let limit = parseInt(searchParams.get('limit') || String(DEFAULT_LIMIT))
  if (Number.isNaN(limit) || limit < 1) limit = DEFAULT_LIMIT
  if (limit > MAX_LIMIT) limit = MAX_LIMIT

  let offset = parseInt(searchParams.get('offset') || '0')
  if (Number.isNaN(offset) || offset < 0) offset = 0
  if (offset > MAX_OFFSET) offset = MAX_OFFSET

  const searchRaw = searchParams.get('search')
  const search = sanitizeText(searchRaw?.toLowerCase() ?? null, MAX_SEARCH_LENGTH)

  const category = sanitizeText(
    searchParams.get('category')?.toLowerCase() ?? null,
    MAX_CATEGORY_LENGTH
  )

  return { limit, offset, search, category }
}

const dataCache: Record<string, StoreDataCache> = {}
const CACHE_TTL = 5 * 60 * 1000

async function loadStoreData(store: string): Promise<StoreDataCache> {
  const cached = dataCache[store]
  const jsonPath = path.join(process.cwd(), 'public', 'data', `${store}.json`)

  let fingerprint = ''
  try {
    const stat = await fs.stat(jsonPath)
    fingerprint = `fs:${stat.size}:${Math.floor(stat.mtimeMs)}`
  } catch (error) {
    if (cached) {
      return cached
    }
    console.error(`Failed to stat ${store} data:`, error)
    return { products: [], total: 0, loadedAt: Date.now(), fingerprint }
  }

  if (
    cached &&
    cached.fingerprint === fingerprint &&
    Date.now() - cached.loadedAt < CACHE_TTL
  ) {
    return cached
  }

  try {
    const fileContent = await fs.readFile(jsonPath, 'utf-8')
    const data = JSON.parse(fileContent)

    const result: StoreDataCache = {
      products: data.products || [],
      total: data.total || data.products?.length || 0,
      loadedAt: Date.now(),
      fingerprint,
    }

    dataCache[store] = result
    return result
  } catch (error) {
    console.error(`Failed to load ${store} data:`, error)
    if (cached) {
      return cached
    }
    return { products: [], total: 0, loadedAt: Date.now(), fingerprint }
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: { store: string } }
) {
  try {
    let storeParam = ''
    try {
      storeParam = decodeURIComponent(params.store || '')
    } catch {
      return NextResponse.json(
        { error: 'Invalid store parameter', products: [] },
        { status: 400 }
      )
    }
    const normalizedStore = storeParam.toLowerCase().trim()
    if (!normalizedStore || normalizedStore.length > MAX_STORE_LENGTH || !/^[a-z0-9_]+$/.test(normalizedStore)) {
      return NextResponse.json(
        { error: 'Invalid store parameter', products: [] },
        { status: 400 }
      )
    }

    const { searchParams } = new URL(request.url)
    const { limit, offset, search, category } = validateAndSanitizeParams(searchParams)

    if (!STORES_SET.has(normalizedStore)) {
      return NextResponse.json(
        { error: `Unknown store: ${storeParam}`, products: [] },
        { status: 400 }
      )
    }

    const storeData = await loadStoreData(normalizedStore)
    if (!storeData.products.length) {
      return NextResponse.json({
        store: normalizedStore,
        products: [],
        total: 0,
        message: `No data available for ${normalizedStore}`,
      })
    }

    let filtered = storeData.products
    if (search) {
      filtered = filtered.filter((product) =>
        product.name?.toLowerCase().includes(search) ||
        product.brand?.toLowerCase().includes(search)
      )
    }

    if (category) {
      filtered = filtered.filter((product) =>
        product.category?.toLowerCase().includes(category)
      )
    }

    const total = filtered.length
    const safeOffset = Math.min(offset, total)
    const paginated = filtered.slice(safeOffset, safeOffset + limit)

    return NextResponse.json({
      store: normalizedStore,
      products: paginated,
      total,
      limit,
      offset: safeOffset,
      hasMore: safeOffset + paginated.length < total,
    })
  } catch (error) {
    console.error('Catalog API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', products: [] },
      { status: 500 }
    )
  }
}
