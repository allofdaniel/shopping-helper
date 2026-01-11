import { NextResponse } from 'next/server'
import path from 'path'
import Database from 'better-sqlite3'

const DB_PATH = process.env.DB_PATH || path.join(process.cwd(), '..', 'data', 'products.db')

export async function GET() {
  try {
    let db: Database.Database
    try {
      db = new Database(DB_PATH, { readonly: true })
    } catch (dbError) {
      console.error('Database connection error:', dbError)
      return NextResponse.json(
        { error: 'Database not available' },
        { status: 503 }
      )
    }

    // 총 영상 수
    const videoCount = db.prepare(`SELECT COUNT(*) as count FROM videos`).get() as { count: number }

    // 총 상품 수
    const productCount = db.prepare(`
      SELECT COUNT(*) as count FROM products
      WHERE is_hidden = 0 OR is_hidden IS NULL
    `).get() as { count: number }

    // 승인된 상품
    const approvedCount = db.prepare(`
      SELECT COUNT(*) as count FROM products
      WHERE is_approved = 1 AND (is_hidden = 0 OR is_hidden IS NULL)
    `).get() as { count: number }

    // 매칭된 상품
    const matchedCount = db.prepare(`
      SELECT COUNT(*) as count FROM products
      WHERE is_matched = 1 AND (is_hidden = 0 OR is_hidden IS NULL)
    `).get() as { count: number }

    // 매장별 상품 수
    const byStore = db.prepare(`
      SELECT store_key, COUNT(*) as count
      FROM products
      WHERE is_hidden = 0 OR is_hidden IS NULL
      GROUP BY store_key
    `).all() as { store_key: string; count: number }[]

    // 카테고리별 상품 수
    const byCategory = db.prepare(`
      SELECT category, COUNT(*) as count
      FROM products
      WHERE is_hidden = 0 OR is_hidden IS NULL
      GROUP BY category
    `).all() as { category: string; count: number }[]

    // 카탈로그 통계
    const catalogStats: Record<string, number> = {}

    const catalogTables = [
      { table: 'daiso_catalog', key: 'daiso' },
      { table: 'costco_catalog', key: 'costco' },
      { table: 'oliveyoung_catalog', key: 'oliveyoung' },
      { table: 'coupang_catalog', key: 'coupang' },
      { table: 'traders_catalog', key: 'traders' },
      { table: 'ikea_catalog', key: 'ikea' },
      { table: 'convenience_catalog', key: 'convenience' },
    ]

    for (const { table, key } of catalogTables) {
      try {
        const result = db.prepare(`SELECT COUNT(*) as count FROM ${table}`).get() as { count: number }
        catalogStats[key] = result?.count || 0
      } catch {
        catalogStats[key] = 0
      }
    }

    db.close()

    return NextResponse.json({
      total_videos: videoCount?.count || 0,
      total_products: productCount?.count || 0,
      approved_products: approvedCount?.count || 0,
      matched_products: matchedCount?.count || 0,
      pending_products: (productCount?.count || 0) - (approvedCount?.count || 0),
      by_store: Object.fromEntries(byStore.map(r => [r.store_key, r.count])),
      by_category: Object.fromEntries(byCategory.map(r => [r.category || '기타', r.count])),
      catalog_counts: catalogStats,
      updated_at: new Date().toISOString(),
    })

  } catch (error) {
    console.error('Stats API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
