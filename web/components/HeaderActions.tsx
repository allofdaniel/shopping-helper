'use client'

import {
  ShoppingCart, SlidersHorizontal, Globe, Sun, Moon, RefreshCw, MapPin, ScanBarcode
} from 'lucide-react'
import { useState } from 'react'
import type { TranslationKey } from '@/lib/i18n'

interface HeaderActionsProps {
  // 쇼핑 모드
  wishlistCount: number
  onOpenShoppingMode: () => void

  // 필터
  activeFilterCount: number
  onOpenFilter: () => void

  // 매장 찾기
  onOpenStoreLocator: () => void

  // 바코드 스캔
  onOpenBarcodeScanner: () => void

  // 언어
  locale: string
  setLocale: (locale: 'ko' | 'en' | 'ja') => void
  localeNames: Record<string, string>

  // 테마
  resolvedTheme: string | undefined
  toggleTheme: () => void

  // 새로고침
  isFetching: boolean
  onRefetch: () => void

  // 번역
  t: (key: TranslationKey) => string
}

export function HeaderActions({
  wishlistCount,
  onOpenShoppingMode,
  activeFilterCount,
  onOpenFilter,
  onOpenStoreLocator,
  onOpenBarcodeScanner,
  locale,
  setLocale,
  localeNames,
  resolvedTheme,
  toggleTheme,
  isFetching,
  onRefetch,
  t,
}: HeaderActionsProps) {
  const [showLangMenu, setShowLangMenu] = useState(false)

  return (
    <div className="flex items-center">
      {/* 쇼핑 모드 버튼 (찜 목록이 있을 때만) */}
      {wishlistCount > 0 && (
        <button
          onClick={onOpenShoppingMode}
          className="min-w-[44px] min-h-[44px] p-2.5 rounded-lg bg-gradient-to-r from-orange-400 to-red-500 text-white transition-all relative mr-0.5 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-orange-400 focus:ring-offset-2"
          aria-label={`${t('shopping')} (${wishlistCount}개 상품)`}
        >
          <ShoppingCart className="w-5 h-5" aria-hidden="true" />
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-white text-orange-500 text-[10px]
                         rounded-full flex items-center justify-center font-bold shadow-sm"
                aria-hidden="true">
            {wishlistCount}
          </span>
        </button>
      )}

      {/* 고급 필터 버튼 */}
      <button
        onClick={onOpenFilter}
        className={`min-w-[44px] min-h-[44px] p-2.5 rounded-lg transition-colors relative flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-orange-400 focus:ring-offset-2
                   ${activeFilterCount > 0
                     ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-500'
                     : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400'
                   }`}
        aria-label={activeFilterCount > 0 ? `${t('advancedFilters')} (${activeFilterCount}개 적용됨)` : t('advancedFilters')}
      >
        <SlidersHorizontal className="w-5 h-5" aria-hidden="true" />
        {activeFilterCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-orange-500 text-white text-[10px]
                         rounded-full flex items-center justify-center font-bold"
                aria-hidden="true">
            {activeFilterCount}
          </span>
        )}
      </button>

      {/* 매장 찾기 버튼 */}
      <button
        onClick={onOpenStoreLocator}
        className="min-w-[44px] min-h-[44px] p-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-green-500 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-offset-2"
        aria-label="주변 매장 찾기"
      >
        <MapPin className="w-5 h-5" aria-hidden="true" />
      </button>

      {/* 바코드 스캔 버튼 */}
      <button
        onClick={onOpenBarcodeScanner}
        className="min-w-[44px] min-h-[44px] p-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-purple-500 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2"
        aria-label="바코드 스캔"
      >
        <ScanBarcode className="w-5 h-5" aria-hidden="true" />
      </button>

      {/* 언어 선택 */}
      <div className="relative">
        <button
          onClick={() => setShowLangMenu(!showLangMenu)}
          className="min-w-[44px] min-h-[44px] p-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2"
          aria-label={`${t('language')} (${localeNames[locale]})`}
          aria-expanded={showLangMenu}
          aria-haspopup="menu"
        >
          <Globe className="w-5 h-5 text-gray-500 dark:text-gray-400" aria-hidden="true" />
        </button>
        {showLangMenu && (
          <div className="absolute right-0 top-full mt-0.5 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-0.5 min-w-[90px] z-50">
            {(['ko', 'en', 'ja'] as const).map((lang) => (
              <button
                key={lang}
                onClick={() => {
                  setLocale(lang)
                  setShowLangMenu(false)
                }}
                className={`w-full px-2.5 py-1.5 text-left text-xs hover:bg-gray-100 dark:hover:bg-gray-700
                          ${locale === lang ? 'text-orange-500 font-medium' : 'text-gray-700 dark:text-gray-300'}`}
              >
                {localeNames[lang]}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 다크모드 토글 */}
      <button
        onClick={toggleTheme}
        className="min-w-[44px] min-h-[44px] p-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:ring-offset-2"
        aria-label={resolvedTheme === 'dark' ? t('lightMode') : t('darkMode')}
        aria-pressed={resolvedTheme === 'dark'}
      >
        {resolvedTheme === 'dark' ? (
          <Sun className="w-5 h-5 text-yellow-400" aria-hidden="true" />
        ) : (
          <Moon className="w-5 h-5 text-gray-500" aria-hidden="true" />
        )}
      </button>

      {/* 새로고침 */}
      <button
        onClick={onRefetch}
        disabled={isFetching}
        className="min-w-[44px] min-h-[44px] p-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
        aria-label={isFetching ? '새로고침 중...' : t('refresh')}
        aria-busy={isFetching}
      >
        <RefreshCw className={`w-5 h-5 text-gray-500 dark:text-gray-400 ${isFetching ? 'animate-spin' : ''}`} aria-hidden="true" />
      </button>
    </div>
  )
}
