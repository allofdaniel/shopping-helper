/**
 * Category matching utilities
 * Centralizes category matching logic to avoid duplication
 */

export type CategoryKey = 'all' | 'kitchen' | 'living' | 'beauty' | 'interior' | 'food' | 'digital'

// Category keywords mapping
const CATEGORY_KEYWORDS: Record<Exclude<CategoryKey, 'all'>, string[]> = {
  food: ['식품', '간식', '음료'],
  beauty: ['뷰티', '화장', '미용'],
  living: ['생활', '청소', '세탁'],
  kitchen: ['주방', '밀폐', '유리', '실리콘'],
  interior: ['인테리어', '수납', '조명'],
  digital: ['디지털', '케이블', '전자'],
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
] as const
