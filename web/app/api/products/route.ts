import { NextRequest, NextResponse } from 'next/server'
import path from 'path'
import Database from 'better-sqlite3'

// DB 경로 설정
const DB_PATH = process.env.DB_PATH || path.join(process.cwd(), '..', 'data', 'products.db')

interface ProductRow {
  id: number
  video_id: string
  name: string
  price: number | null
  category: string | null
  reason: string | null
  timestamp_sec: number | null
  keywords: string | null
  store_key: string
  store_name: string
  official_code: string | null
  official_name: string | null
  official_price: number | null
  official_image_url: string | null
  official_product_url: string | null
  is_matched: number
  is_approved: number
  is_hidden: number
  source_view_count: number | null
  created_at: string
  video_title: string | null
  channel_title: string | null
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)

    // 쿼리 파라미터
    const store = searchParams.get('store')
    const category = searchParams.get('category')
    const search = searchParams.get('search')
    const sort = searchParams.get('sort') || 'popular'
    const limit = parseInt(searchParams.get('limit') || '100')
    const offset = parseInt(searchParams.get('offset') || '0')
    const includeHidden = searchParams.get('includeHidden') === 'true'

    // DB 연결
    let db: Database.Database
    try {
      db = new Database(DB_PATH, { readonly: true })
    } catch (dbError) {
      console.error('Database connection error:', dbError)
      return NextResponse.json(
        { error: 'Database not available', products: [] },
        { status: 503 }
      )
    }

    // 기본 쿼리
    let query = `
      SELECT
        p.id,
        p.video_id,
        p.name,
        p.price,
        p.category,
        p.reason,
        p.timestamp_sec,
        p.keywords,
        p.store_key,
        p.store_name,
        p.official_code,
        p.official_name,
        p.official_price,
        p.official_image_url,
        p.official_product_url,
        p.is_matched,
        p.is_approved,
        p.is_hidden,
        p.source_view_count,
        p.created_at,
        v.title as video_title,
        v.channel_title
      FROM products p
      LEFT JOIN videos v ON p.video_id = v.video_id
      WHERE 1=1
    `

    const params: (string | number)[] = []

    // 숨김 상품 제외 (기본)
    if (!includeHidden) {
      query += ` AND (p.is_hidden = 0 OR p.is_hidden IS NULL)`
    }

    // 매장 필터
    if (store && store !== 'all') {
      query += ` AND p.store_key = ?`
      params.push(store)
    }

    // 카테고리 필터
    if (category && category !== 'all') {
      query += ` AND p.category = ?`
      params.push(category)
    }

    // 검색
    if (search) {
      query += ` AND (
        p.name LIKE ? OR
        p.official_name LIKE ? OR
        p.keywords LIKE ? OR
        v.channel_title LIKE ?
      )`
      const searchTerm = `%${search}%`
      params.push(searchTerm, searchTerm, searchTerm, searchTerm)
    }

    // 정렬
    switch (sort) {
      case 'popular':
        query += ` ORDER BY p.source_view_count DESC NULLS LAST`
        break
      case 'newest':
        query += ` ORDER BY p.created_at DESC`
        break
      case 'price_low':
        query += ` ORDER BY COALESCE(p.official_price, p.price) ASC NULLS LAST`
        break
      case 'price_high':
        query += ` ORDER BY COALESCE(p.official_price, p.price) DESC NULLS LAST`
        break
      default:
        query += ` ORDER BY p.source_view_count DESC NULLS LAST`
    }

    // 페이지네이션
    query += ` LIMIT ? OFFSET ?`
    params.push(limit, offset)

    // 쿼리 실행
    const rows = db.prepare(query).all(...params) as ProductRow[]

    // 총 개수 쿼리
    let countQuery = `
      SELECT COUNT(*) as total
      FROM products p
      LEFT JOIN videos v ON p.video_id = v.video_id
      WHERE 1=1
    `
    const countParams: (string | number)[] = []

    if (!includeHidden) {
      countQuery += ` AND (p.is_hidden = 0 OR p.is_hidden IS NULL)`
    }
    if (store && store !== 'all') {
      countQuery += ` AND p.store_key = ?`
      countParams.push(store)
    }
    if (category && category !== 'all') {
      countQuery += ` AND p.category = ?`
      countParams.push(category)
    }
    if (search) {
      countQuery += ` AND (p.name LIKE ? OR p.official_name LIKE ? OR p.keywords LIKE ? OR v.channel_title LIKE ?)`
      const searchTerm = `%${search}%`
      countParams.push(searchTerm, searchTerm, searchTerm, searchTerm)
    }

    const countResult = db.prepare(countQuery).get(...countParams) as { total: number }
    const total = countResult?.total || 0

    db.close()

    // 응답 변환
    const products = rows.map(row => ({
      id: row.id,
      video_id: row.video_id,
      name: row.name,
      price: row.price,
      category: row.category || '기타',
      reason: row.reason || '',
      timestamp_sec: row.timestamp_sec,
      timestamp_text: row.timestamp_sec ? formatTimestamp(row.timestamp_sec) : null,
      recommendation_quote: null,
      keywords: row.keywords ? JSON.parse(row.keywords) : [],
      store_key: row.store_key,
      store_name: row.store_name,
      official_code: row.official_code,
      official_name: row.official_name,
      official_price: row.official_price,
      official_image_url: row.official_image_url,
      official_product_url: row.official_product_url,
      is_matched: row.is_matched === 1,
      is_approved: row.is_approved === 1,
      source_view_count: row.source_view_count || 0,
      created_at: row.created_at,
      video_title: row.video_title,
      channel_title: row.channel_title,
      thumbnail_url: `https://img.youtube.com/vi/${row.video_id}/mqdefault.jpg`,
    }))

    return NextResponse.json({
      products,
      total,
      limit,
      offset,
      hasMore: offset + products.length < total,
    })

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', products: [] },
      { status: 500 }
    )
  }
}

function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
