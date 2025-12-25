'use client'

import { useState, useEffect, useCallback } from 'react'

const CHECKLIST_KEY = 'shopping_helper_checklist'

export function useChecklist() {
  const [checkedIds, setCheckedIds] = useState<number[]>([])
  const [isLoaded, setIsLoaded] = useState(false)

  // 로컬스토리지에서 불러오기
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(CHECKLIST_KEY)
      if (saved) {
        try {
          setCheckedIds(JSON.parse(saved))
        } catch {
          setCheckedIds([])
        }
      }
      setIsLoaded(true)
    }
  }, [])

  // 변경시 로컬스토리지에 저장
  useEffect(() => {
    if (isLoaded && typeof window !== 'undefined') {
      localStorage.setItem(CHECKLIST_KEY, JSON.stringify(checkedIds))
    }
  }, [checkedIds, isLoaded])

  // 체크 토글
  const toggleCheck = useCallback((productId: number) => {
    setCheckedIds((prev) => {
      if (prev.includes(productId)) {
        return prev.filter((id) => id !== productId)
      }
      return [...prev, productId]
    })
  }, [])

  // 체크 여부 확인
  const isChecked = useCallback(
    (productId: number) => checkedIds.includes(productId),
    [checkedIds]
  )

  // 체크 리스트 초기화
  const clearChecklist = useCallback(() => {
    setCheckedIds([])
  }, [])

  // 특정 상품들만 체크 해제 (찜 목록에서 제거된 것들)
  const removeFromChecklist = useCallback((productId: number) => {
    setCheckedIds((prev) => prev.filter((id) => id !== productId))
  }, [])

  return {
    checkedIds,
    checkedCount: checkedIds.length,
    isLoaded,
    toggleCheck,
    isChecked,
    clearChecklist,
    removeFromChecklist,
  }
}
