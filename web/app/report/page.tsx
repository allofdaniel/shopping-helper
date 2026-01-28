import type { Metadata } from 'next'
import { promises as fs } from 'fs'
import path from 'path'
import Link from 'next/link'

export const metadata: Metadata = {
  title: '크롤링 리포트',
  description: '꿀템장바구니 데이터 수집 현황 대시보드',
}

export const dynamic = 'force-dynamic'

interface StoreInfo {
  key: string
  name: string
  icon: string
  count: number
  new_today: number
  pct: number
}

interface PopularProduct {
  name: string
  store: string
  store_name: string
  price: number | null
  image_url: string | null
  views: number
  category: string
}

interface CategoryInfo {
  name: string
  count: number
}

interface ReportData {
  updated_at: string
  total_products: number
  total_videos: number
  matched_products: number
  match_rate: number
  new_today: number
  stores: StoreInfo[]
  popular_products: PopularProduct[]
  categories: CategoryInfo[]
  price_stats: { min: number; max: number; avg: number }
}

const STORE_COLORS: Record<string, string> = {
  daiso: '#FF6B35',
  costco: '#E31837',
  ikea: '#0051BA',
  oliveyoung: '#009A3D',
  traders: '#004D9B',
  convenience: '#FFA500',
}

function formatNumber(n: number): string {
  return new Intl.NumberFormat('ko-KR').format(n)
}

function formatPrice(price: number | null): string {
  if (!price) return '가격 미정'
  if (price >= 10000) return `${formatNumber(Math.round(price / 1000) * 1000)}원`
  return `${formatNumber(price)}원`
}

function formatViews(views: number): string {
  if (views >= 10000) return `${(views / 10000).toFixed(1)}만`
  if (views >= 1000) return `${(views / 1000).toFixed(1)}천`
  return views.toString()
}

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 60) return `${diffMin}분 전`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}시간 전`
  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay}일 전`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleString('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

async function loadReport(): Promise<ReportData | null> {
  try {
    const filePath = path.join(process.cwd(), 'public', 'data', 'report.json')
    const content = await fs.readFile(filePath, 'utf-8')
    return JSON.parse(content)
  } catch {
    return null
  }
}

export default async function ReportPage() {
  const report = await loadReport()

  if (!report) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <p className="text-6xl mb-4">📊</p>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">리포트 준비 중</h1>
          <p className="text-gray-500">아직 수집된 데이터가 없습니다.</p>
          <Link href="/" className="mt-4 inline-block text-orange-500 hover:underline">
            홈으로 돌아가기
          </Link>
        </div>
      </div>
    )
  }

  const maxStoreCount = Math.max(...report.stores.map(s => s.count))
  const maxCategoryCount = Math.max(...report.categories.map(c => c.count))

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-gradient-to-r from-violet-600 to-purple-700 text-white">
        <div className="max-w-3xl mx-auto px-4 py-8">
          <div className="flex items-center justify-between mb-1">
            <Link href="/" className="text-white/70 hover:text-white text-sm transition">
              &larr; 꿀템장바구니
            </Link>
            <span className="text-white/60 text-xs bg-white/10 px-2 py-1 rounded-full">
              {timeAgo(report.updated_at)}
            </span>
          </div>
          <h1 className="text-2xl font-bold mt-3">크롤링 리포트</h1>
          <p className="text-white/70 text-sm mt-1">{formatDate(report.updated_at)}</p>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 -mt-4 pb-12">
        {/* Metric Cards */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <MetricCard
            value={formatNumber(report.total_products)}
            label="전체 상품"
            accent="text-violet-600 dark:text-violet-400"
          />
          <MetricCard
            value={report.new_today.toString()}
            label="오늘 신규"
            accent={report.new_today > 0 ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}
          />
          <MetricCard
            value={`${report.match_rate}%`}
            label="카탈로그 매칭"
            accent="text-blue-600 dark:text-blue-400"
          />
        </div>

        {/* Summary Prose */}
        <section className="bg-white dark:bg-gray-800 rounded-2xl p-5 mb-6 shadow-sm">
          <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
            현재 총 <strong>{formatNumber(report.total_products)}개</strong>의 상품이 등록되어 있으며,{' '}
            <strong>{formatNumber(report.total_videos)}개</strong>의 유튜브 영상에서 수집한 데이터입니다.{' '}
            이 중 <strong>{formatNumber(report.matched_products)}개({report.match_rate}%)</strong>가
            공식 카탈로그와 매칭되어 정확한 가격과 이미지를 제공하고 있습니다.
          </p>
          {report.new_today > 0 ? (
            <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed mt-3">
              오늘 <strong className="text-green-600">{report.new_today}개</strong>의 신규 상품이 추가되었습니다.
            </p>
          ) : (
            <p className="text-gray-400 dark:text-gray-500 text-sm mt-3">
              오늘 새로 추가된 상품은 없습니다. 기존 데이터가 유지되고 있습니다.
            </p>
          )}
        </section>

        {/* Store Breakdown */}
        <section className="bg-white dark:bg-gray-800 rounded-2xl p-5 mb-6 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">매장별 현황</h2>
          <div className="space-y-4">
            {report.stores.map((store) => (
              <div key={store.key}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{store.icon}</span>
                    <span className="font-medium text-gray-900 dark:text-white text-sm">{store.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      {formatNumber(store.count)}개
                    </span>
                    <span className="text-xs text-gray-400">{store.pct}%</span>
                  </div>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2.5">
                  <div
                    className="h-2.5 rounded-full transition-all duration-500"
                    style={{
                      width: `${(store.count / maxStoreCount) * 100}%`,
                      backgroundColor: STORE_COLORS[store.key] || '#6b7280',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Popular Products */}
        <section className="bg-white dark:bg-gray-800 rounded-2xl p-5 mb-6 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">인기 상품 TOP 10</h2>
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {report.popular_products.map((product, i) => (
              <div key={i} className="flex items-center gap-3 py-3">
                <div
                  className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{
                    backgroundColor: i < 3 ? '#8b5cf6' : '#f3f4f6',
                    color: i < 3 ? '#fff' : '#6b7280',
                  }}
                >
                  {i + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {product.name}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {product.store_name} &middot; {formatPrice(product.price)}
                    {product.views > 0 && (
                      <span className="ml-2">
                        &middot; 조회 {formatViews(product.views)}회
                      </span>
                    )}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Categories */}
        <section className="bg-white dark:bg-gray-800 rounded-2xl p-5 mb-6 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">카테고리 분포</h2>
          <div className="space-y-3">
            {report.categories.map((cat) => (
              <div key={cat.name}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-700 dark:text-gray-300">{cat.name}</span>
                  <span className="text-xs text-gray-400">{cat.count}개</span>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="h-2 rounded-full bg-violet-400 dark:bg-violet-500 transition-all duration-500"
                    style={{ width: `${(cat.count / maxCategoryCount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Price Stats */}
        <section className="bg-white dark:bg-gray-800 rounded-2xl p-5 mb-6 shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">가격 통계</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xl font-bold text-green-600 dark:text-green-400">
                {formatPrice(report.price_stats.min)}
              </p>
              <p className="text-xs text-gray-400 mt-1">최저가</p>
            </div>
            <div>
              <p className="text-xl font-bold text-violet-600 dark:text-violet-400">
                {formatPrice(report.price_stats.avg)}
              </p>
              <p className="text-xs text-gray-400 mt-1">평균가</p>
            </div>
            <div>
              <p className="text-xl font-bold text-red-500 dark:text-red-400">
                {formatPrice(report.price_stats.max)}
              </p>
              <p className="text-xs text-gray-400 mt-1">최고가</p>
            </div>
          </div>
        </section>

        {/* Data Source Info */}
        <section className="text-center text-xs text-gray-400 dark:text-gray-500 space-y-1">
          <p>데이터 수집: 매일 오전 9시, 오후 9시 자동 크롤링</p>
          <p>출처: YouTube 추천 영상 + 공식 카탈로그 매칭</p>
          <p className="pt-2">
            <Link href="/" className="text-violet-500 hover:underline">
              꿀템장바구니 바로가기 &rarr;
            </Link>
          </p>
        </section>
      </main>
    </div>
  )
}

function MetricCard({
  value,
  label,
  accent,
}: {
  value: string
  label: string
  accent: string
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm text-center">
      <p className={`text-2xl font-bold ${accent}`}>{value}</p>
      <p className="text-xs text-gray-400 mt-1">{label}</p>
    </div>
  )
}
