'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

interface UseInfiniteScrollOptions<T> {
  items: T[]
  pageSize?: number
  threshold?: number // intersection observer threshold (0-1)
  rootMargin?: string // e.g., '100px'
}

interface UseInfiniteScrollResult<T> {
  displayedItems: T[]
  hasMore: boolean
  loadMore: () => void
  reset: () => void
  isLoadingMore: boolean
  loaderRef: (node: HTMLDivElement | null) => void
}

export function useInfiniteScroll<T>({
  items,
  pageSize = 20,
  threshold = 0.1,
  rootMargin = '200px',
}: UseInfiniteScrollOptions<T>): UseInfiniteScrollResult<T> {
  const [displayCount, setDisplayCount] = useState(pageSize)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loaderNodeRef = useRef<HTMLDivElement | null>(null)

  // Stable refs for callback values - prevents observer recreation
  const stateRef = useRef({ hasMore: false, isLoadingMore: false, itemsLength: 0, pageSize })

  // Reset when items change
  useEffect(() => {
    setDisplayCount(pageSize)
  }, [items.length, pageSize])

  const displayedItems = items.slice(0, displayCount)
  const hasMore = displayCount < items.length

  // Update refs with latest values (no re-render trigger)
  stateRef.current = { hasMore, isLoadingMore, itemsLength: items.length, pageSize }

  const loadMore = useCallback(() => {
    const { hasMore: canLoad, isLoadingMore: loading, itemsLength, pageSize: size } = stateRef.current
    if (!canLoad || loading) return

    setIsLoadingMore(true)
    // Simulate a slight delay for smoother UX
    requestAnimationFrame(() => {
      setDisplayCount(prev => Math.min(prev + size, itemsLength))
      setIsLoadingMore(false)
    })
  }, []) // Empty deps - uses stateRef for latest values

  const reset = useCallback(() => {
    setDisplayCount(stateRef.current.pageSize)
  }, [])

  // Stable Intersection Observer callback - never changes
  const handleIntersect = useCallback((entries: IntersectionObserverEntry[]) => {
    const { hasMore: canLoad, isLoadingMore: loading } = stateRef.current
    if (entries[0]?.isIntersecting && canLoad && !loading) {
      loadMore()
    }
  }, [loadMore]) // loadMore is now stable

  // Create observer only when threshold/rootMargin change (should be rare)
  useEffect(() => {
    // Cleanup previous observer
    if (observerRef.current) {
      observerRef.current.disconnect()
    }

    // Create new observer with stable callback
    observerRef.current = new IntersectionObserver(handleIntersect, {
      threshold,
      rootMargin,
    })

    // Observe the loader element if it exists
    if (loaderNodeRef.current) {
      observerRef.current.observe(loaderNodeRef.current)
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [handleIntersect, threshold, rootMargin])

  // Stable callback ref for the loader element
  const loaderRef = useCallback((node: HTMLDivElement | null) => {
    loaderNodeRef.current = node

    if (observerRef.current) {
      observerRef.current.disconnect()
    }

    if (node && observerRef.current) {
      observerRef.current.observe(node)
    }
  }, [])

  return {
    displayedItems,
    hasMore,
    loadMore,
    reset,
    isLoadingMore,
    loaderRef,
  }
}
