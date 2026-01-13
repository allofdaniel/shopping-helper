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

  // Reset when items change
  useEffect(() => {
    setDisplayCount(pageSize)
  }, [items.length, pageSize])

  const displayedItems = items.slice(0, displayCount)
  const hasMore = displayCount < items.length

  const loadMore = useCallback(() => {
    if (!hasMore || isLoadingMore) return

    setIsLoadingMore(true)
    // Simulate a slight delay for smoother UX
    requestAnimationFrame(() => {
      setDisplayCount(prev => Math.min(prev + pageSize, items.length))
      setIsLoadingMore(false)
    })
  }, [hasMore, isLoadingMore, pageSize, items.length])

  const reset = useCallback(() => {
    setDisplayCount(pageSize)
  }, [pageSize])

  // Intersection Observer callback
  const handleIntersect = useCallback((entries: IntersectionObserverEntry[]) => {
    if (entries[0]?.isIntersecting && hasMore && !isLoadingMore) {
      loadMore()
    }
  }, [hasMore, isLoadingMore, loadMore])

  // Create/update observer when dependencies change
  useEffect(() => {
    // Cleanup previous observer
    if (observerRef.current) {
      observerRef.current.disconnect()
    }

    // Create new observer
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

  // Callback ref for the loader element
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
