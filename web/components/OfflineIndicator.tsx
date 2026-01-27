'use client'

import { WifiOff, Wifi, X } from 'lucide-react'
import { useOnlineStatus } from '@/lib/useOnlineStatus'

export function OfflineIndicator() {
  const { isOnline, wasOffline, dismissOfflineMessage } = useOnlineStatus()

  // Show nothing if online and hasn't been offline
  if (isOnline && !wasOffline) return null

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-[9999] transition-transform duration-300 ${
        isOnline && !wasOffline ? '-translate-y-full' : 'translate-y-0'
      }`}
    >
      <div
        className={`flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium ${
          isOnline
            ? 'bg-green-500 text-white'
            : 'bg-gray-800 text-white'
        }`}
      >
        {isOnline ? (
          <>
            <Wifi className="w-4 h-4" />
            <span>다시 온라인 상태입니다</span>
          </>
        ) : (
          <>
            <WifiOff className="w-4 h-4" />
            <span>오프라인 모드 - 저장된 데이터를 표시합니다</span>
          </>
        )}
        {isOnline && wasOffline && (
          <button
            onClick={dismissOfflineMessage}
            className="ml-2 p-0.5 hover:bg-green-600 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  )
}

// Offline-aware wrapper for data loading
export function OfflineFallback({ children }: { children: React.ReactNode }) {
  const { isOnline } = useOnlineStatus()

  return (
    <div className={isOnline ? '' : 'opacity-90'}>
      {children}
    </div>
  )
}
