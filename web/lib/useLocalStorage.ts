'use client'

import { useState, useEffect, useCallback } from 'react'

/**
 * Custom hook for persistent localStorage state with SSR support
 * Replaces duplicated localStorage patterns across multiple hooks
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  options?: {
    serialize?: (value: T) => string
    deserialize?: (value: string) => T
  }
): [T, (value: T | ((prev: T) => T)) => void, boolean] {
  const serialize = options?.serialize ?? JSON.stringify
  const deserialize = options?.deserialize ?? JSON.parse

  // Initialize with a function to avoid running on every render
  const [storedValue, setStoredValue] = useState<T>(initialValue)
  const [isLoaded, setIsLoaded] = useState(false)

  // Load from localStorage on mount (client-side only)
  useEffect(() => {
    if (typeof window === 'undefined') return

    try {
      const item = localStorage.getItem(key)
      if (item !== null) {
        const parsed = deserialize(item)
        setStoredValue(parsed)
      }
    } catch (error) {
      console.warn(`[useLocalStorage] Failed to load "${key}":`, error)
      // If parsing fails, remove corrupted data
      try {
        localStorage.removeItem(key)
      } catch {
        // Ignore removal errors
      }
    } finally {
      setIsLoaded(true)
    }
  }, [key, deserialize])

  // Save to localStorage whenever value changes (after initial load)
  useEffect(() => {
    if (!isLoaded) return
    if (typeof window === 'undefined') return

    try {
      const serialized = serialize(storedValue)
      localStorage.setItem(key, serialized)
    } catch (error) {
      console.warn(`[useLocalStorage] Failed to save "${key}":`, error)
    }
  }, [key, storedValue, isLoaded, serialize])

  // Setter function that supports both direct values and updater functions
  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    setStoredValue((prev) => {
      const nextValue = value instanceof Function ? value(prev) : value
      return nextValue
    })
  }, [])

  return [storedValue, setValue, isLoaded]
}

/**
 * Simpler version that returns just the value and setter
 * Use when you don't need to know the loading state
 */
export function useLocalStorageSimple<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  const [value, setValue] = useLocalStorage(key, initialValue)
  return [value, setValue]
}

/**
 * Hook for storing arrays in localStorage with helper methods
 */
export function useLocalStorageArray<T>(
  key: string,
  initialValue: T[] = []
): {
  items: T[]
  add: (item: T) => void
  remove: (predicate: (item: T) => boolean) => void
  toggle: (item: T, isEqual?: (a: T, b: T) => boolean) => void
  includes: (item: T, isEqual?: (a: T, b: T) => boolean) => boolean
  clear: () => void
  isLoaded: boolean
} {
  const [items, setItems, isLoaded] = useLocalStorage<T[]>(key, initialValue)

  const add = useCallback((item: T) => {
    setItems((prev) => [...prev, item])
  }, [setItems])

  const remove = useCallback((predicate: (item: T) => boolean) => {
    setItems((prev) => prev.filter((item) => !predicate(item)))
  }, [setItems])

  const toggle = useCallback((item: T, isEqual: (a: T, b: T) => boolean = (a, b) => a === b) => {
    setItems((prev) => {
      const exists = prev.some((i) => isEqual(i, item))
      if (exists) {
        return prev.filter((i) => !isEqual(i, item))
      }
      return [...prev, item]
    })
  }, [setItems])

  const includes = useCallback((item: T, isEqual: (a: T, b: T) => boolean = (a, b) => a === b) => {
    return items.some((i) => isEqual(i, item))
  }, [items])

  const clear = useCallback(() => {
    setItems([])
  }, [setItems])

  return { items, add, remove, toggle, includes, clear, isLoaded }
}
