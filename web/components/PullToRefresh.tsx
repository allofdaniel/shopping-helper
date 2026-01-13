'use client'

import { RefreshCw } from 'lucide-react'

interface PullToRefreshIndicatorProps {
  pullDistance: number
  isRefreshing: boolean
  threshold?: number
}

export function PullToRefreshIndicator({
  pullDistance,
  isRefreshing,
  threshold = 80,
}: PullToRefreshIndicatorProps) {
  if (pullDistance === 0 && !isRefreshing) return null

  const progress = Math.min(pullDistance / threshold, 1)
  const rotation = progress * 360
  const opacity = Math.min(progress * 1.5, 1)
  const scale = 0.5 + progress * 0.5

  return (
    <div
      className="fixed left-1/2 z-50 flex items-center justify-center pointer-events-none"
      style={{
        top: `${Math.max(pullDistance - 40, 8)}px`,
        transform: 'translateX(-50%)',
        opacity,
      }}
    >
      <div
        className={`flex items-center justify-center w-10 h-10 rounded-full bg-white dark:bg-gray-800 shadow-lg border border-gray-200 dark:border-gray-700 ${
          isRefreshing ? 'animate-spin' : ''
        }`}
        style={{
          transform: `scale(${scale}) rotate(${isRefreshing ? 0 : rotation}deg)`,
          transition: isRefreshing ? 'none' : 'transform 0.1s ease-out',
        }}
      >
        <RefreshCw
          className={`w-5 h-5 ${
            progress >= 1 || isRefreshing
              ? 'text-orange-500'
              : 'text-gray-400 dark:text-gray-500'
          }`}
        />
      </div>
    </div>
  )
}
