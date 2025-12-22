'use client'

import { ExternalLink, Play, ShoppingCart, TrendingUp } from 'lucide-react'
import type { Product } from '@/lib/types'
import { STORES } from '@/lib/types'
import { formatPrice, formatViewCount, getYoutubeVideoUrl, getYoutubeThumbnail } from '@/lib/api'

interface ProductCardProps {
  product: Product
}

export function ProductCard({ product }: ProductCardProps) {
  const store = STORES[product.store_key]
  const hasOfficialInfo = product.is_matched && product.official_product_url

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-shadow overflow-hidden">
      {/* 이미지 영역 */}
      <div className="relative aspect-square bg-gray-100 dark:bg-gray-700">
        {product.official_image_url ? (
          <img
            src={product.official_image_url}
            alt={product.name}
            className="w-full h-full object-contain p-2"
          />
        ) : (
          <img
            src={getYoutubeThumbnail(product.video_id)}
            alt={product.video_title || product.name}
            className="w-full h-full object-cover"
          />
        )}

        {/* 스토어 배지 */}
        <div
          className="absolute top-2 left-2 px-2 py-1 rounded-md text-white text-xs font-bold"
          style={{ backgroundColor: store?.color || '#666' }}
        >
          {store?.icon} {store?.name || product.store_name}
        </div>

        {/* 매칭 배지 */}
        {product.is_matched && (
          <div className="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded-md text-xs">
            공식 매칭
          </div>
        )}
      </div>

      {/* 정보 영역 */}
      <div className="p-4">
        {/* 상품명 */}
        <h3 className="font-bold text-lg mb-1 line-clamp-2">
          {product.official_name || product.name}
        </h3>

        {/* 가격 */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl font-bold text-red-500">
            {formatPrice(product.official_price || product.price)}
          </span>
          {product.coupang_price && product.official_price && (
            <span className="text-sm text-gray-500 line-through">
              쿠팡 {formatPrice(product.coupang_price)}
            </span>
          )}
        </div>

        {/* 카테고리 */}
        {product.category && (
          <span className="inline-block bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs px-2 py-1 rounded-full mb-2">
            {product.category}
          </span>
        )}

        {/* 추천 이유 */}
        {product.reason && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
            "{product.reason}"
          </p>
        )}

        {/* 영상 정보 */}
        <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
          <TrendingUp className="w-3 h-3" />
          <span>{formatViewCount(product.source_view_count)}회 조회</span>
          {product.channel_title && (
            <>
              <span>·</span>
              <span>{product.channel_title}</span>
            </>
          )}
        </div>

        {/* 버튼들 */}
        <div className="flex gap-2">
          {/* 영상 보기 */}
          <a
            href={getYoutubeVideoUrl(product.video_id, product.timestamp_sec || 0)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-1 bg-red-500 hover:bg-red-600 text-white py-2 px-3 rounded-lg text-sm transition-colors"
          >
            <Play className="w-4 h-4" />
            영상
          </a>

          {/* 공식몰 이동 */}
          {hasOfficialInfo && (
            <a
              href={product.official_product_url!}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-1 text-white py-2 px-3 rounded-lg text-sm transition-colors"
              style={{ backgroundColor: store?.color || '#666' }}
            >
              <ShoppingCart className="w-4 h-4" />
              구매
            </a>
          )}

          {/* 쿠팡 비교 */}
          {product.coupang_url && (
            <a
              href={product.coupang_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-1 bg-orange-500 hover:bg-orange-600 text-white py-2 px-3 rounded-lg text-sm transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
