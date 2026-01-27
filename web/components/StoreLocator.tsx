'use client'

import { useState, useEffect, useCallback } from 'react'
import { MapPin, Navigation, Phone, Clock, ExternalLink, X, Loader2, AlertCircle } from 'lucide-react'
import { STORES, type StoreKey } from '@/lib/types'

interface StoreLocation {
  id: string
  name: string
  storeKey: StoreKey
  address: string
  phone?: string
  hours?: string
  lat: number
  lng: number
  distance?: number
}

// Sample store data (in production, this would come from an API)
const SAMPLE_STORES: StoreLocation[] = [
  // Daiso stores
  { id: 'daiso-1', name: '다이소 강남역점', storeKey: 'daiso', address: '서울 강남구 강남대로 396', phone: '02-1234-5678', lat: 37.4979, lng: 127.0276 },
  { id: 'daiso-2', name: '다이소 홍대점', storeKey: 'daiso', address: '서울 마포구 양화로 188', phone: '02-2345-6789', lat: 37.5563, lng: 126.9220 },
  { id: 'daiso-3', name: '다이소 신촌점', storeKey: 'daiso', address: '서울 서대문구 신촌로 83', phone: '02-3456-7890', lat: 37.5551, lng: 126.9368 },
  // Costco stores
  { id: 'costco-1', name: '코스트코 양재점', storeKey: 'costco', address: '서울 서초구 양재대로2길 21', phone: '02-4567-8901', hours: '10:00-22:00', lat: 37.4714, lng: 127.0352 },
  { id: 'costco-2', name: '코스트코 상봉점', storeKey: 'costco', address: '서울 중랑구 망우로 353', phone: '02-5678-9012', hours: '10:00-22:00', lat: 37.5965, lng: 127.0854 },
  // IKEA stores
  { id: 'ikea-1', name: '이케아 광명점', storeKey: 'ikea', address: '경기 광명시 일직로 17', phone: '02-6789-0123', hours: '10:00-22:00', lat: 37.4252, lng: 126.8826 },
  { id: 'ikea-2', name: '이케아 고양점', storeKey: 'ikea', address: '경기 고양시 덕양구 권율대로 420', phone: '02-7890-1234', hours: '10:00-22:00', lat: 37.6440, lng: 126.8959 },
  // Olive Young stores
  { id: 'oliveyoung-1', name: '올리브영 명동본점', storeKey: 'oliveyoung', address: '서울 중구 명동길 53', phone: '02-8901-2345', lat: 37.5636, lng: 126.9850 },
  { id: 'oliveyoung-2', name: '올리브영 강남역점', storeKey: 'oliveyoung', address: '서울 강남구 강남대로 390', phone: '02-9012-3456', lat: 37.4975, lng: 127.0282 },
]

interface StoreLocatorProps {
  isOpen: boolean
  onClose: () => void
  filterStore?: string
}

// Calculate distance between two coordinates (Haversine formula)
function calculateDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371 // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLng/2) * Math.sin(dLng/2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  return R * c
}

export function StoreLocator({ isOpen, onClose, filterStore }: StoreLocatorProps) {
  const [userLocation, setUserLocation] = useState<{lat: number, lng: number} | null>(null)
  const [isLoadingLocation, setIsLoadingLocation] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [selectedStoreFilter, setSelectedStoreFilter] = useState(filterStore || 'all')
  const [stores, setStores] = useState<StoreLocation[]>([])

  // Get user's location
  const getUserLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('이 브라우저에서는 위치 서비스를 지원하지 않습니다.')
      return
    }

    setIsLoadingLocation(true)
    setLocationError(null)

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        })
        setIsLoadingLocation(false)
      },
      (error) => {
        setIsLoadingLocation(false)
        switch (error.code) {
          case error.PERMISSION_DENIED:
            setLocationError('위치 권한이 거부되었습니다. 설정에서 위치 권한을 허용해주세요.')
            break
          case error.POSITION_UNAVAILABLE:
            setLocationError('위치 정보를 가져올 수 없습니다.')
            break
          case error.TIMEOUT:
            setLocationError('위치 요청 시간이 초과되었습니다.')
            break
          default:
            setLocationError('알 수 없는 오류가 발생했습니다.')
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000 // 5 minutes cache
      }
    )
  }, [])

  // Calculate distances and sort stores
  useEffect(() => {
    let filteredStores = SAMPLE_STORES

    // Filter by store type
    if (selectedStoreFilter !== 'all') {
      filteredStores = filteredStores.filter(s => s.storeKey === selectedStoreFilter)
    }

    // Calculate distances if user location is available
    if (userLocation) {
      filteredStores = filteredStores.map(store => ({
        ...store,
        distance: calculateDistance(userLocation.lat, userLocation.lng, store.lat, store.lng)
      })).sort((a, b) => (a.distance || 0) - (b.distance || 0))
    }

    setStores(filteredStores)
  }, [userLocation, selectedStoreFilter])

  // Request location when modal opens
  useEffect(() => {
    if (isOpen && !userLocation && !isLoadingLocation) {
      getUserLocation()
    }
  }, [isOpen, userLocation, isLoadingLocation, getUserLocation])

  // Open in maps app
  const openInMaps = (store: StoreLocation) => {
    const url = `https://maps.google.com/maps?q=${store.lat},${store.lng}&z=17`
    window.open(url, '_blank')
  }

  // Open navigation
  const openNavigation = (store: StoreLocation) => {
    let url: string
    // Try to detect platform and use appropriate maps app
    if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
      url = `maps://maps.apple.com/?daddr=${store.lat},${store.lng}`
    } else {
      url = `https://www.google.com/maps/dir/?api=1&destination=${store.lat},${store.lng}`
    }
    window.open(url, '_blank')
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[9999] bg-black/60 flex items-end sm:items-center justify-center"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-900 w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[90vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
        style={{ animation: 'slideUp 0.25s ease-out' }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-900 border-b dark:border-gray-800 px-4 py-3 flex items-center justify-between z-10">
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-green-500" />
            <h2 className="font-bold text-lg text-gray-900 dark:text-white">주변 매장 찾기</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Store filter */}
        <div className="px-4 py-3 border-b dark:border-gray-800">
          <div className="flex gap-2 overflow-x-auto scrollbar-hide">
            <button
              onClick={() => setSelectedStoreFilter('all')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                selectedStoreFilter === 'all'
                  ? 'bg-gray-800 dark:bg-white text-white dark:text-gray-900'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
              }`}
            >
              전체
            </button>
            {Object.entries(STORES).map(([key, store]) => (
              <button
                key={key}
                onClick={() => setSelectedStoreFilter(key)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-1 ${
                  selectedStoreFilter === key
                    ? 'text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                }`}
                style={selectedStoreFilter === key ? { backgroundColor: store.color } : {}}
              >
                {store.icon} {store.name}
              </button>
            ))}
          </div>
        </div>

        {/* Location status */}
        {(isLoadingLocation || locationError) && (
          <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/50">
            {isLoadingLocation ? (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>현재 위치를 확인하는 중...</span>
              </div>
            ) : locationError ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-red-500">
                  <AlertCircle className="w-4 h-4" />
                  <span>{locationError}</span>
                </div>
                <button
                  onClick={getUserLocation}
                  className="text-sm text-blue-500 hover:underline"
                >
                  다시 시도
                </button>
              </div>
            ) : null}
          </div>
        )}

        {/* Store list */}
        <div className="overflow-y-auto max-h-[60vh]">
          {stores.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <MapPin className="w-12 h-12 mb-3" />
              <p className="text-sm">주변에 매장이 없습니다</p>
            </div>
          ) : (
            <div className="divide-y dark:divide-gray-800">
              {stores.map(store => {
                const storeInfo = STORES[store.storeKey]
                return (
                  <div key={store.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <div className="flex items-start gap-3">
                      {/* Store icon */}
                      <div
                        className="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg flex-shrink-0"
                        style={{ backgroundColor: storeInfo?.color || '#666' }}
                      >
                        {storeInfo?.icon}
                      </div>

                      {/* Store info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-gray-900 dark:text-white truncate">
                            {store.name}
                          </h3>
                          {store.distance !== undefined && (
                            <span className="text-xs text-orange-500 font-medium whitespace-nowrap">
                              {store.distance < 1
                                ? `${Math.round(store.distance * 1000)}m`
                                : `${store.distance.toFixed(1)}km`
                              }
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                          {store.address}
                        </p>
                        {store.hours && (
                          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {store.hours}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div className="flex gap-2 mt-3 ml-13">
                      <button
                        onClick={() => openNavigation(store)}
                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-green-500 text-white rounded-lg text-sm font-medium hover:bg-green-600 transition-colors"
                      >
                        <Navigation className="w-4 h-4" />
                        길찾기
                      </button>
                      <button
                        onClick={() => openInMaps(store)}
                        className="flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                        지도
                      </button>
                      {store.phone && (
                        <a
                          href={`tel:${store.phone}`}
                          className="flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                        >
                          <Phone className="w-4 h-4" />
                          전화
                        </a>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); opacity: 0.5; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  )
}

// Hook to manage store locator
export function useStoreLocator() {
  const [isOpen, setIsOpen] = useState(false)
  const [filterStore, setFilterStore] = useState<string | undefined>()

  const openLocator = (storeKey?: string) => {
    setFilterStore(storeKey)
    setIsOpen(true)
  }

  const closeLocator = () => {
    setIsOpen(false)
    setFilterStore(undefined)
  }

  return { isOpen, filterStore, openLocator, closeLocator }
}
