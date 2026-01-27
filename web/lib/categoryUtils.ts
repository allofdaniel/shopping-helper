/**
 * Category matching utilities
 * Centralizes category matching logic to avoid duplication
 */

export type CategoryKey = 'all' | 'kitchen' | 'living' | 'beauty' | 'interior' | 'food' | 'digital' | 'fashion' | 'health' | 'baby' | 'pet' | 'office' | 'outdoor'

// Category keywords mapping
const CATEGORY_KEYWORDS: Record<Exclude<CategoryKey, 'all'>, string[]> = {
  food: ['식품', '간식', '음료', '과자', '커피', '차', '라면'],
  beauty: ['뷰티', '화장', '미용', '스킨', '로션', '향수', '네일'],
  living: ['생활', '청소', '세탁', '욕실', '화장지', '세제'],
  kitchen: ['주방', '밀폐', '유리', '실리콘', '냄비', '프라이팬', '식기'],
  interior: ['인테리어', '수납', '조명', '커튼', '쿠션', '액자'],
  digital: ['디지털', '케이블', '전자', '충전', '이어폰', '스피커'],
  fashion: ['패션', '의류', '옷', '신발', '가방', '악세서리', '모자'],
  health: ['건강', '비타민', '영양', '운동', '마스크', '체온'],
  baby: ['유아', '아기', '어린이', '아동', '키즈', '장난감'],
  pet: ['반려', '애견', '고양이', '강아지', '사료', '간식'],
  office: ['문구', '오피스', '펜', '노트', '스티커', '테이프'],
  outdoor: ['아웃도어', '캠핑', '등산', '낚시', '텐트', '자전거'],
}

/**
 * Check if a product category matches a filter category
 * @param productCategory - The product's category string
 * @param filterCategory - The category key to filter by
 * @returns true if the product matches the filter category
 */
export function matchesCategory(
  productCategory: string | null | undefined,
  filterCategory: CategoryKey
): boolean {
  if (filterCategory === 'all') return true
  if (!productCategory) return false

  const cat = productCategory.toLowerCase()
  const keywords = CATEGORY_KEYWORDS[filterCategory]

  if (!keywords) return false

  return keywords.some(keyword => cat.includes(keyword))
}

/**
 * Filter products by category
 * @param products - Array of products with category field
 * @param filterCategory - The category key to filter by
 * @returns Filtered array of products
 */
export function filterByCategory<T extends { category?: string | null }>(
  products: T[],
  filterCategory: CategoryKey
): T[] {
  if (filterCategory === 'all') return products
  return products.filter(p => matchesCategory(p.category, filterCategory))
}

/**
 * Get all available category keys
 */
export const CATEGORY_KEYS: readonly CategoryKey[] = [
  'all',
  'kitchen',
  'living',
  'beauty',
  'interior',
  'food',
  'digital',
  'fashion',
  'health',
  'baby',
  'pet',
  'office',
  'outdoor',
] as const
