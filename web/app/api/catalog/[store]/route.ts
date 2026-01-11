import { NextRequest, NextResponse } from 'next/server'
import path from 'path'
import Database from 'better-sqlite3'

const DB_PATH = process.env.DB_PATH || path.join(process.cwd(), '..', 'data', 'products.db')

// 매장별 테이블 및 컬럼 매핑
const CATALOG_CONFIG: Record<string, { table: string; idColumn: string; nameColumn: string }> = {
  daiso: { table: 'daiso_catalog', idColumn: 'product_no', nameColumn: 'name' },
  costco: { table: 'costco_catalog', idColumn: 'product_code', nameColumn: 'name' },
  oliveyoung: { table: 'oliveyoung_catalog', idColumn: 'product_code', nameColumn: 'name' },
  coupang: { table: 'coupang_catalog', idColumn: 'product_id', nameColumn: 'name' },
  traders: { table: 'traders_catalog', idColumn: 'item_id', nameColumn: 'name' },
  ikea: { table: 'ikea_catalog', idColumn: 'product_id', nameColumn: 'name' },
  convenience: { table: 'convenience_catalog', idColumn: 'product_id', nameColumn: 'name' },
}

export async function GET(
  request: NextRequest,
  { params }: { params: { store: string } }
) {
  try {
    const store = params.store
    const { searchParams } = new URL(request.url)

    const search = searchParams.get('search')
    const limit = parseInt(searchParams.get('limit') || '50')
    const offset = parseInt(searchParams.get('offset') || '0')

    // 매장 설정 확인
    const config = CATALOG_CONFIG[store]
    if (!config) {
      return NextResponse.json(
        { error: `Unknown store: ${store}`, products: [] },
        { status: 400 }
      )
    }

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

    // 테이블 존재 확인
    const tableExists = db.prepare(`
      SELECT name FROM sqlite_master WHERE type='table' AND name=?
    `).get(config.table)

    if (!tableExists) {
      db.close()
      return NextResponse.json({
        products: [],
        total: 0,
        message: `Catalog table not found for ${store}`,
      })
    }

    // 쿼리 구성
    let query = `SELECT * FROM ${config.table} WHERE 1=1`
    const queryParams: (string | number)[] = []

    if (search) {
      query += ` AND ${config.nameColumn} LIKE ?`
      queryParams.push(`%${search}%`)
    }

    // 총 개수
    const countQuery = query.replace('SELECT *', 'SELECT COUNT(*) as count')
    const countResult = db.prepare(countQuery).get(...queryParams) as { count: number }

    // 페이지네이션
    query += ` LIMIT ? OFFSET ?`
    queryParams.push(limit, offset)

    const products = db.prepare(query).all(...queryParams)

    db.close()

    return NextResponse.json({
      store,
      products,
      total: countResult?.count || 0,
      limit,
      offset,
      hasMore: offset + products.length < (countResult?.count || 0),
    })

  } catch (error) {
    console.error('Catalog API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', products: [] },
      { status: 500 }
    )
  }
}
