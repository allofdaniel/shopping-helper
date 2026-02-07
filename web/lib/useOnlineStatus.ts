'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(true)
  const [wasOffline, setWasOffline] = useState(false)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    // Initial check
    setIsOnline(navigator.onLine)

    const handleOnline = () => {
      setIsOnline(true)
      // Show "back online" message briefly when coming back online
      setWasOffline(true)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      timeoutRef.current = setTimeout(() => setWasOffline(false), 3000)
    }

    const handleOffline = () => {
      setIsOnline(false)
      setWasOffline(true)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  const dismissOfflineMessage = useCallback(() => {
    setWasOffline(false)
  }, [])

  return { isOnline, wasOffline, dismissOfflineMessage }
}
