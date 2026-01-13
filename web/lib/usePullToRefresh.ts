'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

interface UsePullToRefreshOptions {
  onRefresh: () => Promise<void> | void
  threshold?: number // 얼마나 당겨야 새로고침 되는지 (px)
  maxPull?: number // 최대 당김 거리 (px)
  disabled?: boolean
}

interface UsePullToRefreshResult {
  isPulling: boolean
  pullDistance: number
  isRefreshing: boolean
  containerRef: React.RefObject<HTMLDivElement>
}

export function usePullToRefresh({
  onRefresh,
  threshold = 80,
  maxPull = 120,
  disabled = false,
}: UsePullToRefreshOptions): UsePullToRefreshResult {
  const [isPulling, setIsPulling] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const startY = useRef(0)
  const currentY = useRef(0)

  const handleTouchStart = useCallback((e: TouchEvent) => {
    if (disabled || isRefreshing) return
    if (window.scrollY > 0) return // 스크롤이 맨 위가 아니면 무시

    startY.current = e.touches[0].clientY
    setIsPulling(true)
  }, [disabled, isRefreshing])

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!isPulling || disabled || isRefreshing) return
    if (window.scrollY > 0) {
      setIsPulling(false)
      setPullDistance(0)
      return
    }

    currentY.current = e.touches[0].clientY
    const diff = currentY.current - startY.current

    if (diff > 0) {
      // 저항감 적용 (당길수록 더 어려워짐)
      const resistance = 0.5
      const distance = Math.min(diff * resistance, maxPull)
      setPullDistance(distance)

      // 기본 스크롤 방지
      if (distance > 0) {
        e.preventDefault()
      }
    }
  }, [isPulling, disabled, isRefreshing, maxPull])

  const handleTouchEnd = useCallback(async () => {
    if (!isPulling || disabled) return

    setIsPulling(false)

    if (pullDistance >= threshold && !isRefreshing) {
      setIsRefreshing(true)
      setPullDistance(threshold) // 새로고침 중에는 threshold 위치 유지

      try {
        await onRefresh()
      } finally {
        setIsRefreshing(false)
        setPullDistance(0)
      }
    } else {
      setPullDistance(0)
    }
  }, [isPulling, pullDistance, threshold, isRefreshing, disabled, onRefresh])

  useEffect(() => {
    const container = containerRef.current || document
    const options = { passive: false }

    container.addEventListener('touchstart', handleTouchStart as any, options)
    container.addEventListener('touchmove', handleTouchMove as any, options)
    container.addEventListener('touchend', handleTouchEnd as any)

    return () => {
      container.removeEventListener('touchstart', handleTouchStart as any)
      container.removeEventListener('touchmove', handleTouchMove as any)
      container.removeEventListener('touchend', handleTouchEnd as any)
    }
  }, [handleTouchStart, handleTouchMove, handleTouchEnd])

  return {
    isPulling,
    pullDistance,
    isRefreshing,
    containerRef,
  }
}
