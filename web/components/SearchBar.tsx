'use client'

import { useState, useRef, useEffect } from 'react'
import { Search, X, Clock, TrendingUp, Trash2 } from 'lucide-react'

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
  onClear: () => void
  placeholder?: string
  isFocused?: boolean
  onFocus?: () => void
  onBlur?: () => void
  // 최근 검색어 기능
  recentSearches?: string[]
  onSelectRecent?: (query: string) => void
  onRemoveRecent?: (query: string) => void
  onClearAllRecent?: () => void
  // 인기 검색어 (자동완성)
  popularKeywords?: string[]
}

// 인기 검색어 (하드코딩 또는 API에서 가져올 수 있음)
const DEFAULT_POPULAR = ['밀폐용기', '수납', '청소용품', '화장품', '간식', '주방용품']

export function SearchBar({
  value,
  onChange,
  onClear,
  placeholder = '검색어를 입력하세요',
  isFocused = false,
  onFocus,
  onBlur,
  recentSearches = [],
  onSelectRecent,
  onRemoveRecent,
  onClearAllRecent,
  popularKeywords = DEFAULT_POPULAR,
}: SearchBarProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 드롭다운 외부 클릭 감지
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleFocus = () => {
    setShowDropdown(true)
    onFocus?.()
  }

  const handleBlur = () => {
    // 드롭다운 클릭 시 blur 무시
    setTimeout(() => {
      onBlur?.()
    }, 100)
  }

  const handleSelect = (query: string) => {
    onChange(query)
    onSelectRecent?.(query)
    setShowDropdown(false)
    inputRef.current?.blur()
  }

  const filteredRecent = recentSearches.filter(
    (s) => s.toLowerCase().includes(value.toLowerCase())
  ).slice(0, 5)

  const filteredPopular = popularKeywords.filter(
    (k) => k.toLowerCase().includes(value.toLowerCase())
  ).slice(0, 4)

  const hasContent = filteredRecent.length > 0 || filteredPopular.length > 0 || !value

  return (
    <div className="flex-1 relative" role="search" ref={dropdownRef}>
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none z-10" aria-hidden="true" />
      <label htmlFor="product-search" className="sr-only">상품 검색</label>
      <input
        ref={inputRef}
        id="product-search"
        type="search"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={handleFocus}
        onBlur={handleBlur}
        aria-label="상품 검색"
        autoComplete="off"
        className={`w-full pl-8 pr-8 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs
                   text-gray-900 dark:text-white placeholder-gray-400
                   focus:outline-none focus:ring-2 focus:ring-orange-400 focus:bg-white dark:focus:bg-gray-800
                   transition-all duration-200
                   ${isFocused ? 'bg-white dark:bg-gray-800 shadow-lg' : ''}`}
      />
      {value && (
        <button
          onClick={onClear}
          aria-label="검색어 지우기"
          className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full z-10"
        >
          <X className="w-3.5 h-3.5 text-gray-400" aria-hidden="true" />
        </button>
      )}

      {/* 드롭다운 */}
      {showDropdown && hasContent && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden z-50 max-h-72 overflow-y-auto">
          {/* 최근 검색어 */}
          {!value && recentSearches.length > 0 && (
            <div className="p-2">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-medium text-gray-500 dark:text-gray-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  최근 검색어
                </span>
                {onClearAllRecent && (
                  <button
                    onClick={(e) => {
                      e.preventDefault()
                      onClearAllRecent()
                    }}
                    className="text-[9px] text-gray-400 hover:text-red-500 flex items-center gap-0.5"
                  >
                    <Trash2 className="w-2.5 h-2.5" />
                    전체삭제
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-1">
                {recentSearches.slice(0, 8).map((query) => (
                  <button
                    key={query}
                    onClick={() => handleSelect(query)}
                    className="group flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-[10px] text-gray-600 dark:text-gray-300 hover:bg-orange-100 dark:hover:bg-orange-900/30 hover:text-orange-600 transition-colors"
                  >
                    <span>{query}</span>
                    {onRemoveRecent && (
                      <X
                        className="w-2.5 h-2.5 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => {
                          e.stopPropagation()
                          onRemoveRecent(query)
                        }}
                      />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 검색 중 - 일치하는 최근 검색어 */}
          {value && filteredRecent.length > 0 && (
            <div className="p-2 border-b border-gray-100 dark:border-gray-700">
              <span className="text-[10px] font-medium text-gray-500 dark:text-gray-400 flex items-center gap-1 mb-1">
                <Clock className="w-3 h-3" />
                최근 검색
              </span>
              {filteredRecent.map((query) => (
                <button
                  key={query}
                  onClick={() => handleSelect(query)}
                  className="w-full text-left px-2 py-1.5 text-xs text-gray-700 dark:text-gray-300 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded transition-colors"
                >
                  {query}
                </button>
              ))}
            </div>
          )}

          {/* 인기 검색어 / 추천 */}
          {((!value && popularKeywords.length > 0) || (value && filteredPopular.length > 0)) && (
            <div className="p-2">
              <span className="text-[10px] font-medium text-gray-500 dark:text-gray-400 flex items-center gap-1 mb-1">
                <TrendingUp className="w-3 h-3" />
                {value ? '추천 검색어' : '인기 검색어'}
              </span>
              <div className="flex flex-wrap gap-1">
                {(value ? filteredPopular : popularKeywords.slice(0, 6)).map((keyword) => (
                  <button
                    key={keyword}
                    onClick={() => handleSelect(keyword)}
                    className="px-2 py-1 bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 rounded-full text-[10px] hover:bg-orange-100 dark:hover:bg-orange-900/40 transition-colors"
                  >
                    {keyword}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
