'use client'

import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'shopping_helper_recent_searches'
const MAX_RECENT_SEARCHES = 10

export function useRecentSearch() {
  const [recentSearches, setRecentSearches] = useState<string[]>([])

  // 로컬스토리지에서 불러오기
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved) {
          const parsed = JSON.parse(saved)
          if (Array.isArray(parsed)) {
            setRecentSearches(parsed.slice(0, MAX_RECENT_SEARCHES))
          }
        }
      } catch (e) {
        console.error('Failed to load recent searches:', e)
      }
    }
  }, [])

  // 검색어 추가
  const addSearch = useCallback((query: string) => {
    const trimmed = query.trim()
    if (!trimmed || trimmed.length < 2) return

    setRecentSearches((prev) => {
      const filtered = prev.filter((s) => s.toLowerCase() !== trimmed.toLowerCase())
      const updated = [trimmed, ...filtered].slice(0, MAX_RECENT_SEARCHES)

      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
      }
      return updated
    })
  }, [])

  // 검색어 삭제
  const removeSearch = useCallback((query: string) => {
    setRecentSearches((prev) => {
      const updated = prev.filter((s) => s !== query)
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
      }
      return updated
    })
  }, [])

  // 전체 삭제
  const clearAll = useCallback(() => {
    setRecentSearches([])
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  return {
    recentSearches,
    addSearch,
    removeSearch,
    clearAll,
  }
}
