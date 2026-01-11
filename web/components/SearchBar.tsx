'use client'

import { Search, X } from 'lucide-react'

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
  onClear: () => void
  placeholder?: string
  isFocused?: boolean
  onFocus?: () => void
  onBlur?: () => void
}

export function SearchBar({
  value,
  onChange,
  onClear,
  placeholder = '검색어를 입력하세요',
  isFocused = false,
  onFocus,
  onBlur,
}: SearchBarProps) {
  return (
    <div className="flex-1 relative" role="search">
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" aria-hidden="true" />
      <label htmlFor="product-search" className="sr-only">상품 검색</label>
      <input
        id="product-search"
        type="search"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={onFocus}
        onBlur={onBlur}
        aria-label="상품 검색"
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
          className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full"
        >
          <X className="w-3.5 h-3.5 text-gray-400" aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
