'use client'

import { Play, ShoppingCart, Clock, MessageCircle, Eye, X, ChevronRight, MapPin, Phone, Copy, Check, Tag, ExternalLink, Youtube, Star, Calendar, Package, Heart, Scale, Share2, ImageOff } from 'lucide-react'
import type { Product, StoreLocation } from '@/lib/types'
import { STORES } from '@/lib/types'
import { formatPrice, getYoutubeVideoUrl, getYoutubeThumbnail, formatViewCount } from '@/lib/api'
import { useState, useCallback, memo } from 'react'

interface ProductCardProps {
  product: Product
  isInWishlist?: boolean
  onToggleWishlist?: (productId: number) => void
  isInCompare?: boolean
  onToggleCompare?: (productId: number) => void
  compareCount?: number
  maxCompare?: number
  onShare?: () => void
  compact?: boolean  // 작은 아이콘 뷰
}

// UX Law: Fitts's Law - 중요한 버튼은 크고 가까워야 함
// UX Law: Miller's Law - 정보를 5~7개 그룹으로 청킹
// UX Law: Doherty Threshold - 400ms 이내 반응

export const ProductCard = memo(function ProductCard({
  product,
  isInWishlist = false,
  onToggleWishlist,
  isInCompare = false,
  onToggleCompare,
  compareCount = 0,
  maxCompare = 4,
  onShare,
  compact = false,
}: ProductCardProps) {
  const store = STORES[product.store_key]
  const hasOfficialInfo = product.official_product_url
  const [imgError, setImgError] = useState(false)
  const [imgLoaded, setImgLoaded] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [copiedCode, setCopiedCode] = useState(false)
  const [showVideo, setShowVideo] = useState(false)

  // 이미지 URL: image_url (카탈로그) 또는 official_image_url (공식) 사용
  const imageUrl = !imgError && (product.image_url || product.official_image_url)
    ? (product.image_url || product.official_image_url)
    : null

  // 타임스탬프 포맷팅
  const formatTimestamp = (seconds: number | null, text: string | null): string => {
    if (text) return text
    if (!seconds) return ''
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const timestampDisplay = formatTimestamp(product.timestamp_sec, product.timestamp_text)

  // 매장 정보 파싱
  const parseStoreLocations = (): StoreLocation[] => {
    if (!product.store_locations) return []
    if (typeof product.store_locations === 'string') {
      try {
        return JSON.parse(product.store_locations)
      } catch {
        return []
      }
    }
    return product.store_locations
  }

  const storeLocations = parseStoreLocations()

  // 상품코드 복사
  const handleCopyCode = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation()
    const code = product.official_code || ''
    if (code) {
      try {
        await navigator.clipboard.writeText(code)
        setCopiedCode(true)
        setTimeout(() => setCopiedCode(false), 2000)
      } catch (err) {
        console.error('Failed to copy:', err)
      }
    }
  }, [product.official_code])

  // 클릭 핸들러 - Doherty Threshold 적용 (즉각 반응)
  const handleCardClick = useCallback(() => {
    setShowDetail(true)
  }, [])

  const handleCloseDetail = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setShowDetail(false)
    setShowVideo(false) // 영상도 멈춤
  }, [])

  // 찜하기 토글
  const handleWishlistToggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (onToggleWishlist) {
      onToggleWishlist(product.id)
    }
  }, [onToggleWishlist, product.id])

  // 비교 토글
  const handleCompareToggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (onToggleCompare) {
      onToggleCompare(product.id)
    }
  }, [onToggleCompare, product.id])

  // 공유하기
  const handleShare = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (onShare) {
      onShare()
    }
  }, [onShare])

  // 날짜 포맷
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' })
    } catch {
      return ''
    }
  }

  return (
    <>
      {/* 카드 - 터치 영역 44x44 이상 (Fitts's Law) */}
      <article
        onClick={handleCardClick}
        onKeyDown={(e) => e.key === 'Enter' && handleCardClick()}
        role="button"
        tabIndex={0}
        aria-label={`${product.name}, ${store?.name}, ${formatPrice(product.official_price || product.price)}`}
        className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden cursor-pointer
                   active:scale-[0.98] transition-transform duration-100
                   hover:shadow-md dark:shadow-gray-900/50
                   border border-transparent dark:border-gray-700
                   focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2
                   ${compact ? 'min-h-[140px]' : 'min-h-[180px]'}`}
      >
        {/* 이미지 영역 */}
        <div className="relative aspect-[4/3] bg-gray-100 dark:bg-gray-700 overflow-hidden">
          {imageUrl ? (
            <>
              {/* 이미지 로딩 중 스켈레톤 */}
              {!imgLoaded && (
                <div className="absolute inset-0 bg-gray-200 dark:bg-gray-600 animate-pulse" />
              )}
              <img
                src={imageUrl}
                alt={product.name}
                className={`w-full h-full object-contain p-1 transition-opacity duration-300 ${
                  imgLoaded ? 'opacity-100' : 'opacity-0'
                }`}
                onError={() => setImgError(true)}
                onLoad={() => setImgLoaded(true)}
                loading="lazy"
                decoding="async"
              />
            </>
          ) : product.video_id ? (
            <div className="relative w-full h-full">
              <img
                src={getYoutubeThumbnail(product.video_id)}
                alt={product.name}
                className="w-full h-full object-cover"
                loading="lazy"
                decoding="async"
              />
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                <Play className="w-8 h-8 text-white" fill="white" />
              </div>
            </div>
          ) : (
            // 이미지 없는 카탈로그 상품용 플레이스홀더
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800">
              <Package className="w-12 h-12 text-gray-300 dark:text-gray-500" />
            </div>
          )}

          {/* 스토어 배지 - 좌상단 (Jakob's Law - 표준 위치) */}
          <span
            className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded-full text-white text-[10px] font-bold shadow-sm"
            style={{ backgroundColor: store?.color || '#666' }}
          >
            {store?.icon} {store?.name}
          </span>

          {/* 우상단 액션 버튼들 */}
          <div className="absolute top-1.5 right-1.5 flex flex-col gap-1">
            {/* 찜하기 버튼 */}
            {onToggleWishlist && (
              <button
                onClick={handleWishlistToggle}
                className={`p-1.5 rounded-full shadow-md transition-all
                           ${isInWishlist
                             ? 'bg-red-500 text-white'
                             : 'bg-white/90 dark:bg-gray-800/90 text-gray-400 hover:text-red-500'}`}
                aria-label={isInWishlist ? '찜 해제' : '찜하기'}
              >
                <Heart
                  className="w-4 h-4"
                  fill={isInWishlist ? 'white' : 'none'}
                />
              </button>
            )}

            {/* 비교 버튼 */}
            {onToggleCompare && (
              <button
                onClick={handleCompareToggle}
                disabled={!isInCompare && compareCount >= maxCompare}
                className={`p-1.5 rounded-full shadow-md transition-all
                           ${isInCompare
                             ? 'bg-orange-500 text-white'
                             : compareCount >= maxCompare
                               ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                               : 'bg-white/90 dark:bg-gray-800/90 text-gray-400 hover:text-orange-500'}`}
                aria-label={isInCompare ? '비교 해제' : '비교하기'}
                title={compareCount >= maxCompare && !isInCompare ? `최대 ${maxCompare}개까지 비교 가능` : ''}
              >
                <Scale className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* 타임스탬프 배지 */}
          {timestampDisplay && (
            <span className="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 bg-black/70 rounded text-white text-[10px] flex items-center gap-0.5">
              <Clock className="w-2.5 h-2.5" />
              {timestampDisplay}
            </span>
          )}

          {/* 추천 이유 표시 - 있을 때만 */}
          {product.recommendation_quote && (
            <div className="absolute bottom-1.5 left-1.5 px-1.5 py-0.5 bg-yellow-400 rounded text-[9px] font-medium flex items-center gap-0.5">
              <MessageCircle className="w-2.5 h-2.5" />
              추천
            </div>
          )}
        </div>

        {/* 정보 영역 - Miller's Law: 청킹 적용 */}
        <div className="p-2">
          {/* 그룹 1: 상품명 */}
          <h3 className="font-medium text-xs leading-tight line-clamp-2 mb-1 min-h-[28px]
                         text-gray-900 dark:text-gray-100">
            {product.official_name || product.name}
          </h3>

          {/* 그룹 2: 가격 + 품번 */}
          <div className="flex items-center justify-between mb-1">
            <p className="text-sm font-bold text-red-500 dark:text-red-400">
              {formatPrice(product.official_price || product.price)}
            </p>
            {product.official_code && (
              <button
                onClick={handleCopyCode}
                className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] transition-all
                          ${copiedCode
                            ? 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400'
                            : 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'}`}
              >
                <Tag className="w-2.5 h-2.5" />
                {copiedCode ? '복사!' : product.official_code.slice(0, 8)}
              </button>
            )}
          </div>

          {/* 그룹 3: 채널 + 조회수 */}
          <div className="flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400">
            <span className="truncate flex-1">{product.channel_title || ''}</span>
            {product.source_view_count > 0 && (
              <span className="flex items-center gap-0.5 ml-1">
                <Eye className="w-2.5 h-2.5" />
                {formatViewCount(product.source_view_count)}
              </span>
            )}
          </div>
        </div>
      </article>

      {/* 상세 모달 - 풀스크린 방식으로 변경 */}
      {showDetail && (
        <div
          className="fixed inset-0 z-[9999] bg-black/60 flex items-end sm:items-center justify-center"
          onClick={handleCloseDetail}
          role="dialog"
          aria-modal="true"
          aria-labelledby={`product-detail-${product.id}`}
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}
        >
          <div
            className="bg-white dark:bg-gray-900 w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[92vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
            style={{
              animation: 'slideUp 0.25s ease-out',
            }}
          >
            {/* 모달 헤더 - 고정 */}
            <div className="sticky top-0 bg-white dark:bg-gray-900 border-b dark:border-gray-800 px-4 py-3 flex items-center justify-between z-10">
              <div className="flex items-center gap-2">
                <span
                  className="px-2 py-0.5 rounded-full text-white text-xs font-bold"
                  style={{ backgroundColor: store?.color || '#666' }}
                >
                  {store?.icon} {store?.name}
                </span>
                <h2 className="font-bold text-base text-gray-900 dark:text-white">상품 상세</h2>
              </div>
              <div className="flex items-center gap-1">
                {/* 공유 버튼 */}
                {onShare && (
                  <button
                    onClick={handleShare}
                    className="p-2 rounded-full transition-colors text-gray-400 hover:text-blue-500 dark:hover:text-blue-400"
                    aria-label="공유하기"
                  >
                    <Share2 className="w-5 h-5" />
                  </button>
                )}
                {/* 비교 버튼 */}
                {onToggleCompare && (
                  <button
                    onClick={handleCompareToggle}
                    disabled={!isInCompare && compareCount >= maxCompare}
                    className={`p-2 rounded-full transition-colors
                               ${isInCompare
                                 ? 'text-orange-500'
                                 : compareCount >= maxCompare
                                   ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                                   : 'text-gray-400 hover:text-orange-500'}`}
                    aria-label={isInCompare ? '비교 해제' : '비교하기'}
                  >
                    <Scale className="w-5 h-5" />
                  </button>
                )}
                {/* 찜하기 버튼 */}
                {onToggleWishlist && (
                  <button
                    onClick={handleWishlistToggle}
                    className={`p-2 rounded-full transition-colors
                               ${isInWishlist ? 'text-red-500' : 'text-gray-400 hover:text-red-500'}`}
                    aria-label={isInWishlist ? '찜 해제' : '찜하기'}
                  >
                    <Heart className="w-5 h-5" fill={isInWishlist ? 'currentColor' : 'none'} />
                  </button>
                )}
                <button
                  onClick={handleCloseDetail}
                  className="p-2 -mr-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors text-gray-500 dark:text-gray-400"
                  aria-label="닫기"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* 상품 이미지 / 영상 */}
            <div className="relative aspect-video bg-gray-100 dark:bg-gray-800">
              {showVideo && product.video_id ? (
                // YouTube 임베드 플레이어
                <iframe
                  src={`https://www.youtube.com/embed/${product.video_id}?autoplay=1&start=${product.timestamp_sec || 0}`}
                  title={product.video_title || product.name}
                  className="w-full h-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              ) : imageUrl ? (
                <div className="relative w-full h-full">
                  <img
                    src={imageUrl}
                    alt={product.name}
                    className="w-full h-full object-contain"
                  />
                  {/* 영상 재생 버튼 오버레이 - video_id 있을 때만 */}
                  {product.video_id && (
                    <button
                      onClick={() => setShowVideo(true)}
                      className="absolute bottom-3 right-3 flex items-center gap-1.5 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors shadow-lg"
                    >
                      <Play className="w-4 h-4" fill="white" />
                      영상 보기
                    </button>
                  )}
                </div>
              ) : product.video_id ? (
                <div
                  className="relative w-full h-full cursor-pointer"
                  onClick={() => setShowVideo(true)}
                >
                  <img
                    src={getYoutubeThumbnail(product.video_id)}
                    alt={product.name}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-black/30 flex items-center justify-center hover:bg-black/40 transition-colors">
                    <div className="bg-red-600 rounded-full p-4">
                      <Play className="w-10 h-10 text-white" fill="white" />
                    </div>
                  </div>
                  <span className="absolute bottom-2 left-2 text-white text-xs bg-black/70 px-2 py-1 rounded">
                    클릭하여 영상 재생
                  </span>
                </div>
              ) : (
                // 이미지/영상 없는 카탈로그 상품
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800">
                  <Package className="w-16 h-16 text-gray-300 dark:text-gray-500" />
                </div>
              )}
            </div>

            {/* 상품 정보 */}
            <div className="p-4 space-y-4">

              {/* 섹션 1: 상품명 + 가격 */}
              <div className="bg-gradient-to-r from-gray-50 to-white dark:from-gray-800 dark:to-gray-900 rounded-xl p-4 border dark:border-gray-700">
                <h3 className="font-bold text-lg mb-2 leading-tight text-gray-900 dark:text-white">
                  {product.official_name || product.name}
                </h3>
                <div className="flex items-end gap-3">
                  <p className="text-2xl font-bold text-red-500 dark:text-red-400">
                    {formatPrice(product.official_price || product.price)}
                  </p>
                  {product.source_view_count > 0 && (
                    <span className="text-sm text-gray-400 dark:text-gray-500 flex items-center gap-1 mb-1">
                      <Eye className="w-4 h-4" />
                      조회 {formatViewCount(product.source_view_count)}
                    </span>
                  )}
                </div>
                {product.category && (
                  <span className="inline-block mt-2 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-md text-xs text-gray-600 dark:text-gray-300">
                    📁 {product.category}
                  </span>
                )}
              </div>

              {/* 섹션 2: 추천 이유 - 핵심 정보 (있을 때만) */}
              {product.recommendation_quote && (
                <div className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/30 dark:to-orange-900/30 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-yellow-700 dark:text-yellow-400 font-semibold text-sm mb-2">
                    <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                    유튜버 추천 이유
                    {timestampDisplay && (
                      <span className="ml-auto text-yellow-600 dark:text-yellow-500 text-xs font-normal flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {timestampDisplay}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed italic">
                    "{product.recommendation_quote}"
                  </p>
                </div>
              )}

              {/* 섹션 3: 상품코드 (있을 때만) */}
              {(product.product_code_display || product.official_code) && (
                <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Tag className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                        {product.product_code_display || `상품번호: ${product.official_code}`}
                      </span>
                    </div>
                    <button
                      onClick={handleCopyCode}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 dark:bg-blue-800 hover:bg-blue-200 dark:hover:bg-blue-700 rounded-lg text-xs font-medium text-blue-700 dark:text-blue-200 transition-colors"
                    >
                      {copiedCode ? (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          복사됨!
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          복사
                        </>
                      )}
                    </button>
                  </div>
                  {product.availability_note && (
                    <p className="text-xs text-blue-600 dark:text-blue-400 mt-2 flex items-center gap-1">
                      <Package className="w-3 h-3" />
                      {product.availability_note}
                    </p>
                  )}
                </div>
              )}

              {/* 섹션 4: 매장 위치 정보 (있을 때만) */}
              {storeLocations.length > 0 && (
                <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-400 font-semibold text-sm mb-3">
                    <MapPin className="w-4 h-4" />
                    주요 매장 안내
                    <span className="text-xs font-normal text-green-600 dark:text-green-500">
                      ({storeLocations.length}개 매장)
                    </span>
                  </div>
                  <div className="space-y-3">
                    {storeLocations.slice(0, 4).map((loc, idx) => (
                      <div key={idx} className="flex items-start gap-3 bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-100 dark:border-green-900">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm text-gray-800 dark:text-gray-200">{loc.name}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{loc.address}</p>
                        </div>
                        {loc.phone && (
                          <a
                            href={`tel:${loc.phone}`}
                            className="flex items-center gap-1.5 px-3 py-2 bg-green-100 dark:bg-green-800 hover:bg-green-200 dark:hover:bg-green-700 rounded-lg text-xs font-medium text-green-700 dark:text-green-200 transition-colors shrink-0"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Phone className="w-3.5 h-3.5" />
                            전화
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                  {storeLocations.length > 4 && (
                    <p className="text-xs text-green-600 dark:text-green-400 mt-3 text-center font-medium">
                      + {storeLocations.length - 4}개 매장 더 있음
                    </p>
                  )}
                </div>
              )}

              {/* 섹션 5: 영상 정보 - video_id가 있을 때만 */}
              {product.video_id && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 border dark:border-gray-700">
                  <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300 font-semibold text-sm mb-3">
                    <Youtube className="w-4 h-4 text-red-500" />
                    추천 영상 정보
                  </div>
                  <div className="bg-white dark:bg-gray-900 rounded-lg p-3 border dark:border-gray-700">
                    <p className="font-medium text-sm line-clamp-2 mb-2 text-gray-900 dark:text-white">
                      {product.video_title || '영상 정보'}
                    </p>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
                      <span className="flex items-center gap-1">
                        👤 {product.channel_title || '채널 정보 없음'}
                      </span>
                      {product.source_view_count > 0 && (
                        <span className="flex items-center gap-1">
                          <Eye className="w-3 h-3" />
                          {formatViewCount(product.source_view_count)}회
                        </span>
                      )}
                      {product.created_at && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(product.created_at)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* 섹션 6: 추가 정보 (키워드가 있을 때) */}
              {product.keywords && product.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {product.keywords.slice(0, 6).map((keyword, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-md text-xs"
                    >
                      #{keyword}
                    </span>
                  ))}
                </div>
              )}

              {/* CTA 버튼 - Fitts's Law: 큰 터치 영역 (최소 48px) */}
              {/* Hick's Law: 핵심 액션 2개만 표시 */}
              <div className="flex gap-3 pt-3 sticky bottom-0 bg-white dark:bg-gray-900 pb-2">
                {/* 영상 재생/멈춤 토글 버튼 - video_id 있을 때만 */}
                {product.video_id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setShowVideo(!showVideo)
                    }}
                    className={`flex-1 flex items-center justify-center gap-2 py-4 rounded-xl text-base font-bold transition-all shadow-lg ${
                      showVideo
                        ? 'bg-gray-600 hover:bg-gray-700 text-white'
                        : 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white shadow-red-500/25'
                    }`}
                  >
                    <Play className="w-5 h-5" fill="white" />
                    {showVideo ? '영상 멈춤' : '영상 재생'}
                    {!showVideo && timestampDisplay && <span className="text-red-200 text-sm">({timestampDisplay})</span>}
                  </button>
                )}

                {/* 장바구니 담기 버튼 */}
                {onToggleWishlist && (
                  <button
                    onClick={handleWishlistToggle}
                    className={`flex-1 flex items-center justify-center gap-2 py-4 rounded-xl text-base font-bold transition-all shadow-lg ${
                      isInWishlist
                        ? 'bg-orange-500 hover:bg-orange-600 text-white shadow-orange-500/25'
                        : 'bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white shadow-orange-500/25'
                    }`}
                  >
                    <ShoppingCart className="w-5 h-5" />
                    {isInWishlist ? '장바구니에서 빼기' : '장바구니 담기'}
                  </button>
                )}
              </div>

              {/* 온라인 구매 링크 (있을 때만) */}
              {(product.official_product_url || product.product_url) && (
                <a
                  href={product.official_product_url || product.product_url || ''}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all border-2"
                  style={{
                    borderColor: store?.color || '#666',
                    color: store?.color || '#666'
                  }}
                >
                  <ExternalLink className="w-4 h-4" />
                  온라인 매장에서 보기
                </a>
              )}

              {/* 공식 상품 링크 (없을 때 대체) */}
              {!product.official_product_url && !product.product_url && (
                <p className="text-center text-xs text-gray-400 dark:text-gray-500">
                  📍 오프라인 매장에서 직접 확인해보세요!
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* CSS 애니메이션 - 글로벌 스타일 */}
      <style>{`
        @keyframes slideUp {
          from {
            transform: translateY(100%);
            opacity: 0.5;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </>
  )
})
