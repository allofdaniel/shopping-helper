'use client'

import { ChevronUp } from 'lucide-react'
import { useEffect, useState, useCallback } from 'react'

interface ScrollTopButtonProps {
  threshold?: number
}

export function ScrollTopButton({ threshold = 500 }: ScrollTopButtonProps) {
  const [showButton, setShowButton] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setShowButton(window.scrollY > threshold)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [threshold])

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  if (!showButton) return null

  return (
    <button
      onClick={scrollToTop}
      className="fixed bottom-20 left-4 z-40 p-3 bg-white dark:bg-gray-800 rounded-full shadow-lg
               border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700
               transition-all duration-300 animate-fade-in"
    >
      <ChevronUp className="w-5 h-5 text-gray-600 dark:text-gray-400" />
    </button>
  )
}
