'use client'

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/Header'
import { StoreFilter } from '@/components/StoreFilter'
import { CategoryFilter } from '@/components/CategoryFilter'
import { ProductCard } from '@/components/ProductCard'
import { fetchProducts } from '@/lib/api'
import type { Product } from '@/lib/types'
import { Loader2, Package } from 'lucide-react'

export default function Home() {
  const [selectedStore, setSelectedStore] = useState('all')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  const { data: products = [], isLoading, refetch } = useQuery({
    queryKey: ['products'],
    queryFn: () => fetchProducts(),
  })

  // 필터링된 상품
  const filteredProducts = useMemo(() => {
    let result = products

    // 스토어 필터
    if (selectedStore !== 'all') {
      result = result.filter((p: Product) => p.store_key === selectedStore)
    }

    // 카테고리 필터
    if (selectedCategory !== 'all') {
      result = result.filter((p: Product) =>
        p.category?.toLowerCase().includes(selectedCategory) ||
        p.keywords?.some((k: string) => k.includes(selectedCategory))
      )
    }

    // 검색어 필터
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter((p: Product) =>
        p.name.toLowerCase().includes(query) ||
        p.official_name?.toLowerCase().includes(query) ||
        p.reason?.toLowerCase().includes(query)
      )
    }

    return result
  }, [products, selectedStore, selectedCategory, searchQuery])

  // 스토어별 개수
  const storeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    products.forEach((p: Product) => {
      counts[p.store_key] = (counts[p.store_key] || 0) + 1
    })
    return counts
  }, [products])

  // 카테고리별 개수
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    const currentProducts = selectedStore === 'all'
      ? products
      : products.filter((p: Product) => p.store_key === selectedStore)

    currentProducts.forEach((p: Product) => {
      if (p.category) {
        const cat = p.category.toLowerCase()
        // 카테고리 매핑
        if (cat.includes('식품') || cat.includes('간식') || cat.includes('음료')) counts.food = (counts.food || 0) + 1
        else if (cat.includes('뷰티') || cat.includes('화장품')) counts.beauty = (counts.beauty || 0) + 1
        else if (cat.includes('생활') || cat.includes('청소')) counts.living = (counts.living || 0) + 1
        else if (cat.includes('주방')) counts.kitchen = (counts.kitchen || 0) + 1
        else if (cat.includes('인테리어') || cat.includes('수납')) counts.interior = (counts.interior || 0) + 1
        else counts.etc = (counts.etc || 0) + 1
      }
    })
    return counts
  }, [products, selectedStore])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header
        onSearch={setSearchQuery}
        onRefresh={() => refetch()}
        isLoading={isLoading}
      />

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* 스토어 필터 */}
        <section className="mb-6">
          <h2 className="text-sm font-medium text-gray-500 mb-3">매장 선택</h2>
          <StoreFilter
            selectedStore={selectedStore}
            onSelectStore={setSelectedStore}
            counts={storeCounts}
          />
        </section>

        {/* 카테고리 필터 */}
        <section className="mb-6">
          <h2 className="text-sm font-medium text-gray-500 mb-3">카테고리</h2>
          <CategoryFilter
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
            counts={categoryCounts}
          />
        </section>

        {/* 상품 수 */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-gray-600 dark:text-gray-400">
            총 <span className="font-bold text-gray-900 dark:text-white">{filteredProducts.length}</span>개 상품
          </p>
        </div>

        {/* 로딩 */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
          </div>
        )}

        {/* 상품 없음 */}
        {!isLoading && filteredProducts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <Package className="w-16 h-16 mb-4" />
            <p className="text-lg">상품이 없습니다</p>
            <p className="text-sm">다른 필터를 선택해보세요</p>
          </div>
        )}

        {/* 상품 그리드 */}
        {!isLoading && filteredProducts.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredProducts.map((product: Product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </main>

      {/* 푸터 */}
      <footer className="border-t border-gray-200 dark:border-gray-700 mt-12 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-gray-500 text-sm">
          <p>유튜버가 추천한 꿀템을 한눈에! 📺</p>
          <p className="mt-2">
            데이터는 유튜브 영상에서 자동 수집되며, 상품 정보는 각 공식몰에서 매칭됩니다.
          </p>
        </div>
      </footer>
    </div>
  )
}
