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
  const isPullingRef = useRef(false)

  // Use refs to avoid recreating event handlers on every render
  const stateRef = useRef({
    isPulling: false,
    pullDistance: 0,
    isRefreshing: false,
    disabled: false,
    threshold: 80,
    maxPull: 120,
    onRefresh: onRefresh,
  })

  // Update ref values when state/props change
  useEffect(() => {
    stateRef.current = {
      isPulling,
      pullDistance,
      isRefreshing,
      disabled,
      threshold,
      maxPull,
      onRefresh,
    }
  }, [isPulling, pullDistance, isRefreshing, disabled, threshold, maxPull, onRefresh])

  // Stable handlers that read from refs
  const handleTouchStart = useCallback((e: TouchEvent) => {
    const state = stateRef.current
    if (state.disabled || state.isRefreshing) return
    if (window.scrollY > 0) return // 스크롤이 맨 위가 아니면 무시

    startY.current = e.touches[0].clientY
    isPullingRef.current = true
    setIsPulling(true)
  }, [])

  const handleTouchMove = useCallback((e: TouchEvent) => {
    const state = stateRef.current
    if (!isPullingRef.current || state.disabled || state.isRefreshing) return
    if (window.scrollY > 0) {
      isPullingRef.current = false
      setIsPulling(false)
      setPullDistance(0)
      return
    }

    currentY.current = e.touches[0].clientY
    const diff = currentY.current - startY.current

    if (diff > 0) {
      // 저항감 적용 (당길수록 더 어려워짐)
      const resistance = 0.5
      const distance = Math.min(diff * resistance, state.maxPull)
      setPullDistance(distance)

      // 기본 스크롤 방지
      if (distance > 0) {
        e.preventDefault()
      }
    }
  }, [])

  const handleTouchEnd = useCallback(async () => {
    const state = stateRef.current
    if (!state.isPulling || state.disabled) return

    setIsPulling(false)

    if (state.pullDistance >= state.threshold && !state.isRefreshing) {
      setIsRefreshing(true)
      setPullDistance(state.threshold) // 새로고침 중에는 threshold 위치 유지

      try {
        await state.onRefresh()
      } finally {
        setIsRefreshing(false)
        setPullDistance(0)
      }
    } else {
      setPullDistance(0)
    }
  }, [])

  // Event listeners setup - only runs once
  useEffect(() => {
    const container = containerRef.current || document
    const options = { passive: false }

    container.addEventListener('touchstart', handleTouchStart as EventListener, options)
    container.addEventListener('touchmove', handleTouchMove as EventListener, options)
    container.addEventListener('touchend', handleTouchEnd as EventListener)

    return () => {
      container.removeEventListener('touchstart', handleTouchStart as EventListener)
      container.removeEventListener('touchmove', handleTouchMove as EventListener)
      container.removeEventListener('touchend', handleTouchEnd as EventListener)
    }
  }, [handleTouchStart, handleTouchMove, handleTouchEnd])

  return {
    isPulling,
    pullDistance,
    isRefreshing,
    containerRef,
  }
}
