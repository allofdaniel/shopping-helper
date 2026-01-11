'use client'

import {
  ShoppingCart, SlidersHorizontal, Globe, Sun, Moon, RefreshCw
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
          className="p-1.5 rounded-lg bg-gradient-to-r from-orange-400 to-red-500 text-white transition-all relative mr-0.5"
          title={t('shopping')}
        >
          <ShoppingCart className="w-3.5 h-3.5" />
          <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-white text-orange-500 text-[8px]
                         rounded-full flex items-center justify-center font-bold shadow-sm">
            {wishlistCount}
          </span>
        </button>
      )}

      {/* 고급 필터 버튼 */}
      <button
        onClick={onOpenFilter}
        className={`p-1.5 rounded-lg transition-colors relative
                   ${activeFilterCount > 0
                     ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-500'
                     : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400'
                   }`}
        title={t('advancedFilters')}
      >
        <SlidersHorizontal className="w-3.5 h-3.5" />
        {activeFilterCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-orange-500 text-white text-[8px]
                         rounded-full flex items-center justify-center font-bold">
            {activeFilterCount}
          </span>
        )}
      </button>

      {/* 언어 선택 */}
      <div className="relative">
        <button
          onClick={() => setShowLangMenu(!showLangMenu)}
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title={t('language')}
        >
          <Globe className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
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
        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        title={resolvedTheme === 'dark' ? t('lightMode') : t('darkMode')}
      >
        {resolvedTheme === 'dark' ? (
          <Sun className="w-3.5 h-3.5 text-yellow-400" />
        ) : (
          <Moon className="w-3.5 h-3.5 text-gray-500" />
        )}
      </button>

      {/* 새로고침 */}
      <button
        onClick={onRefetch}
        disabled={isFetching}
        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        title={t('refresh')}
      >
        <RefreshCw className={`w-3.5 h-3.5 text-gray-500 dark:text-gray-400 ${isFetching ? 'animate-spin' : ''}`} />
      </button>
    </div>
  )
}
