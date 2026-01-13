export interface StoreLocation {
  name: string
  address: string
  phone: string
}

export interface Product {
  id: number
  video_id: string
  name: string
  price: number | null
  category: string
  reason: string
  timestamp_sec: number | null
  timestamp_text: string | null
  recommendation_quote: string | null  // 추천 이유 스크립트
  keywords: string[]
  store_key: string
  store_name: string
  official_code: string | null
  official_name: string | null
  official_price: number | null
  official_image_url: string | null
  official_product_url: string | null
  image_url?: string | null  // 카탈로그 이미지 URL
  product_url?: string | null  // 카탈로그 상품 URL
  is_matched: boolean
  is_approved: boolean
  source_view_count: number
  created_at: string
  video_title?: string
  channel_title?: string
  thumbnail_url?: string
  video_view_count?: number
  coupang_price?: number | null
  coupang_url?: string | null
  // 매장 정보
  store_locations?: StoreLocation[] | string | null
  product_code_display?: string | null
  availability_note?: string | null
}

export interface Video {
  id: number
  video_id: string
  title: string
  description: string
  channel_id: string
  channel_title: string
  published_at: string
  thumbnail_url: string
  view_count: number
  like_count: number
  store_key: string
  store_name: string
}

export interface Store {
  key: string
  name: string
  icon: string
  color: string
  count: number
}

export interface Category {
  key: string
  name: string
  icon: string
  count: number
}

export interface Stats {
  total_videos: number
  total_products: number
  approved_products: number
  pending_products: number
  by_store: Record<string, number>
  by_category: Record<string, number>
}

// 매장 표시 순서 (중요도 순)
const STORE_ORDER = ['daiso', 'costco', 'ikea', 'oliveyoung', 'traders', 'cu', 'gs25', 'seveneleven', 'emart24', 'coupang'] as const

export const STORES: Record<string, Store> = {
  daiso: { key: 'daiso', name: '다이소', icon: '🏪', color: '#FF6B35', count: 0 },
  costco: { key: 'costco', name: '코스트코', icon: '🛒', color: '#E31837', count: 0 },
  ikea: { key: 'ikea', name: '이케아', icon: '🪑', color: '#0051BA', count: 0 },
  oliveyoung: { key: 'oliveyoung', name: '올리브영', icon: '💄', color: '#009A3D', count: 0 },
  traders: { key: 'traders', name: '트레이더스', icon: '🏬', color: '#004D9B', count: 0 },
  cu: { key: 'cu', name: 'CU', icon: '🟣', color: '#6B2D8A', count: 0 },
  gs25: { key: 'gs25', name: 'GS25', icon: '🔵', color: '#0063C1', count: 0 },
  seveneleven: { key: 'seveneleven', name: '세븐일레븐', icon: '🟢', color: '#00A656', count: 0 },
  emart24: { key: 'emart24', name: '이마트24', icon: '🟡', color: '#FFB800', count: 0 },
  coupang: { key: 'coupang', name: '쿠팡', icon: '📦', color: '#E4002B', count: 0 },
}

// 정렬된 매장 목록
export const STORES_ORDERED = STORE_ORDER.map(key => STORES[key])

export const CATEGORIES: Record<string, Category> = {
  food: { key: 'food', name: '식품', icon: '🍽️', count: 0 },
  beauty: { key: 'beauty', name: '뷰티', icon: '💄', count: 0 },
  living: { key: 'living', name: '생활용품', icon: '🏠', count: 0 },
  kitchen: { key: 'kitchen', name: '주방', icon: '🍳', count: 0 },
  interior: { key: 'interior', name: '인테리어', icon: '🪴', count: 0 },
  fashion: { key: 'fashion', name: '패션', icon: '👕', count: 0 },
  digital: { key: 'digital', name: '디지털', icon: '📱', count: 0 },
  health: { key: 'health', name: '건강', icon: '💊', count: 0 },
  baby: { key: 'baby', name: '유아', icon: '👶', count: 0 },
  pet: { key: 'pet', name: '반려동물', icon: '🐕', count: 0 },
  office: { key: 'office', name: '문구/오피스', icon: '📝', count: 0 },
  outdoor: { key: 'outdoor', name: '아웃도어', icon: '⛺', count: 0 },
}
