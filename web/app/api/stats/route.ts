import { NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

async function loadSummary() {
  try {
    const summaryPath = path.join(process.cwd(), 'public', 'data', 'summary.json')
    const content = await fs.readFile(summaryPath, 'utf-8')
    return JSON.parse(content)
  } catch {
    return null
  }
}

export async function GET() {
  try {
    const summary = await loadSummary()

    if (!summary) {
      return NextResponse.json({
        catalog_counts: {},
        total_products: 0,
        updated_at: new Date().toISOString(),
      })
    }

    const catalogCounts: Record<string, number> = {}
    for (const [key, store] of Object.entries(summary.stores || {})) {
      catalogCounts[key] = (store as any).total || 0
    }

    return NextResponse.json({
      catalog_counts: catalogCounts,
      total_products: summary.total_products || 0,
      stores: summary.stores,
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
