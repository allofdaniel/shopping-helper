'use client'

import { useState, useEffect, useCallback, createContext, useContext } from 'react'

export type Locale = 'ko' | 'en' | 'ja'

// 번역 데이터
export const translations = {
  ko: {
    // 앱 이름
    appName: '꿀템장바구니',
    appTagline: '유튜버 추천 오프라인 매장 꿀템 모음',

    // 네비게이션
    home: '홈',
    wishlist: '찜 목록',
    shopping: '쇼핑 모드',
    settings: '설정',

    // 필터
    all: '전체',
    popular: '인기순',
    new: '최신순',
    newest: '최신순',
    recommended: '추천',
    favorites: '찜',

    // 카테고리
    kitchen: '주방',
    living: '생활',
    beauty: '뷰티',
    interior: '인테리어',
    food: '식품',
    digital: '디지털',

    // 검색
    searchPlaceholder: '상품명, 채널명으로 검색...',
    searchResults: '검색결과',
    noResults: '상품이 없습니다',
    tryDifferentSearch: '다른 검색어나 필터를 시도해보세요',

    // 상품 카드
    watchVideo: '영상 보기',
    buyNow: '구매하기',
    copyCode: '복사',
    copied: '복사됨!',
    views: '조회',
    price: '가격',
    productCode: '품번',
    youtuberRecommend: '유튜버 추천 이유',

    // 찜하기
    addToWishlist: '찜하기',
    removeFromWishlist: '찜 해제',
    noWishlist: '찜한 상품이 없습니다',
    addSomeProducts: '마음에 드는 상품의 ❤️ 버튼을 눌러보세요',
    viewAllProducts: '전체 상품 보기',
    exportWishlist: '내보내기',

    // 쇼핑 모드
    shoppingChecklist: '쇼핑 체크리스트',
    checkAtStore: '매장 방문시 체크하세요',
    completed: '완료',
    remaining: '남은 상품',
    estimatedTotal: '예상 금액',
    searchInStore: '매장에서 검색',
    checkWhenFound: '매장에서 상품을 찾으면 체크해보세요',

    // 비교
    compare: '비교',
    compareProducts: '상품 비교',
    maxCompareReached: '최대 4개까지 비교 가능',

    // 공유
    share: '공유하기',
    shareProduct: '상품 공유',
    shareWishlist: '찜 목록 공유',

    // 기타
    loading: '로딩 중...',
    refresh: '새로고침',
    lastUpdated: '업데이트',
    products: '개 상품',
    darkMode: '다크 모드',
    lightMode: '라이트 모드',
    language: '언어',
    close: '닫기',
    cancel: '취소',
    confirm: '확인',
    error: '오류가 발생했습니다',
    retry: '다시 시도',
    networkError: '네트워크 연결을 확인하고 다시 시도해주세요',
    resetFilters: '필터 초기화',
    advancedFilters: '상세 필터',
    stores: '매장',
    visitOfflineStore: '오프라인 매장에서 직접 확인해보세요!',
  },

  en: {
    appName: 'HoneyCart',
    appTagline: 'YouTuber-recommended offline store picks',

    home: 'Home',
    wishlist: 'Wishlist',
    shopping: 'Shopping Mode',
    settings: 'Settings',

    all: 'All',
    popular: 'Popular',
    new: 'Newest',
    newest: 'Newest',
    recommended: 'Recommended',
    favorites: 'Favorites',

    kitchen: 'Kitchen',
    living: 'Living',
    beauty: 'Beauty',
    interior: 'Interior',
    food: 'Food',
    digital: 'Digital',

    searchPlaceholder: 'Search products, channels...',
    searchResults: 'Search results',
    noResults: 'No products found',
    tryDifferentSearch: 'Try a different search or filter',

    watchVideo: 'Watch Video',
    buyNow: 'Buy Now',
    copyCode: 'Copy',
    copied: 'Copied!',
    views: 'views',
    price: 'Price',
    productCode: 'Product Code',
    youtuberRecommend: 'YouTuber Recommendation',

    addToWishlist: 'Add to Wishlist',
    removeFromWishlist: 'Remove from Wishlist',
    noWishlist: 'No items in wishlist',
    addSomeProducts: 'Tap ❤️ on products you like',
    viewAllProducts: 'View All Products',
    exportWishlist: 'Export',

    shoppingChecklist: 'Shopping Checklist',
    checkAtStore: 'Check off items at the store',
    completed: 'Completed',
    remaining: 'Remaining',
    estimatedTotal: 'Estimated Total',
    searchInStore: 'Search in Store',
    checkWhenFound: 'Check items when you find them',

    compare: 'Compare',
    compareProducts: 'Compare Products',
    maxCompareReached: 'Maximum 4 items for comparison',

    share: 'Share',
    shareProduct: 'Share Product',
    shareWishlist: 'Share Wishlist',

    loading: 'Loading...',
    refresh: 'Refresh',
    lastUpdated: 'Updated',
    products: 'products',
    darkMode: 'Dark Mode',
    lightMode: 'Light Mode',
    language: 'Language',
    close: 'Close',
    cancel: 'Cancel',
    confirm: 'Confirm',
    error: 'An error occurred',
    retry: 'Retry',
    networkError: 'Please check your connection and try again',
    resetFilters: 'Reset Filters',
    advancedFilters: 'Advanced Filters',
    stores: 'Stores',
    visitOfflineStore: 'Visit the store to check it out!',
  },

  ja: {
    appName: 'ハニーカート',
    appTagline: 'YouTuberおすすめのオフラインショップ商品',

    home: 'ホーム',
    wishlist: 'お気に入り',
    shopping: 'ショッピングモード',
    settings: '設定',

    all: 'すべて',
    popular: '人気順',
    new: '新着順',
    newest: '新着順',
    recommended: 'おすすめ',
    favorites: 'お気に入り',

    kitchen: 'キッチン',
    living: '生活',
    beauty: 'ビューティー',
    interior: 'インテリア',
    food: 'フード',
    digital: 'デジタル',

    searchPlaceholder: '商品名、チャンネルで検索...',
    searchResults: '検索結果',
    noResults: '商品が見つかりません',
    tryDifferentSearch: '別のキーワードやフィルターをお試しください',

    watchVideo: '動画を見る',
    buyNow: '購入する',
    copyCode: 'コピー',
    copied: 'コピーしました！',
    views: '再生回数',
    price: '価格',
    productCode: '品番',
    youtuberRecommend: 'YouTuberのおすすめ理由',

    addToWishlist: 'お気に入りに追加',
    removeFromWishlist: 'お気に入りから削除',
    noWishlist: 'お気に入りがありません',
    addSomeProducts: '気に入った商品の❤️ボタンをタップ',
    viewAllProducts: 'すべての商品を見る',
    exportWishlist: 'エクスポート',

    shoppingChecklist: 'ショッピングチェックリスト',
    checkAtStore: '店舗でチェックしてください',
    completed: '完了',
    remaining: '残り',
    estimatedTotal: '合計予想',
    searchInStore: '店舗で検索',
    checkWhenFound: '商品を見つけたらチェック',

    compare: '比較',
    compareProducts: '商品を比較',
    maxCompareReached: '最大4つまで比較可能',

    share: 'シェア',
    shareProduct: '商品をシェア',
    shareWishlist: 'お気に入りをシェア',

    loading: '読み込み中...',
    refresh: '更新',
    lastUpdated: '更新',
    products: '商品',
    darkMode: 'ダークモード',
    lightMode: 'ライトモード',
    language: '言語',
    close: '閉じる',
    cancel: 'キャンセル',
    confirm: '確認',
    error: 'エラーが発生しました',
    retry: '再試行',
    networkError: '接続を確認して再試行してください',
    resetFilters: 'フィルターをリセット',
    advancedFilters: '詳細フィルター',
    stores: 'ストア',
    visitOfflineStore: '店舗でご確認ください！',
  },
}

export type TranslationKey = keyof typeof translations.ko

const LOCALE_KEY = 'shopping_helper_locale'

// 브라우저 언어 감지
const detectBrowserLocale = (): Locale => {
  if (typeof window === 'undefined') return 'ko'

  const browserLang = navigator.language.toLowerCase()
  if (browserLang.startsWith('ja')) return 'ja'
  if (browserLang.startsWith('en')) return 'en'
  return 'ko'
}

export function useLocale() {
  const [locale, setLocaleState] = useState<Locale>('ko')
  const [isLoaded, setIsLoaded] = useState(false)

  // 로컬스토리지에서 불러오기
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(LOCALE_KEY) as Locale | null
      if (saved && ['ko', 'en', 'ja'].includes(saved)) {
        setLocaleState(saved)
      } else {
        // 브라우저 언어로 기본값 설정
        setLocaleState(detectBrowserLocale())
      }
      setIsLoaded(true)
    }
  }, [])

  // 언어 변경
  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale)
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCALE_KEY, newLocale)
    }
  }, [])

  // 번역 함수
  const t = useCallback(
    (key: TranslationKey): string => {
      return translations[locale][key] || translations.ko[key] || key
    },
    [locale]
  )

  return {
    locale,
    setLocale,
    t,
    isLoaded,
    locales: ['ko', 'en', 'ja'] as Locale[],
    localeNames: {
      ko: '한국어',
      en: 'English',
      ja: '日本語',
    },
  }
}

// Context for global access
interface LocaleContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: TranslationKey) => string
}

export const LocaleContext = createContext<LocaleContextValue | null>(null)

export function useTranslation() {
  const context = useContext(LocaleContext)
  if (!context) {
    // Fallback if not in context
    return {
      locale: 'ko' as Locale,
      setLocale: () => {},
      t: (key: TranslationKey) => translations.ko[key] || key,
    }
  }
  return context
}
