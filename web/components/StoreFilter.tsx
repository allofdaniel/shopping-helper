'use client'

import { STORES_ORDERED } from '@/lib/types'

interface StoreFilterProps {
  selectedStore: string
  onSelectStore: (store: string) => void
  counts?: Record<string, number>
}

export function StoreFilter({ selectedStore, onSelectStore, counts = {} }: StoreFilterProps) {
  const stores = [
    { key: 'all', name: '전체', icon: '🏠', color: '#333' },
    ...STORES_ORDERED,
  ]

  return (
    <div className="flex flex-wrap gap-2">
      {stores.map((store) => {
        const isSelected = selectedStore === store.key
        const count = store.key === 'all'
          ? Object.values(counts).reduce((a, b) => a + b, 0)
          : counts[store.key] || 0

        return (
          <button
            key={store.key}
            onClick={() => onSelectStore(store.key)}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium
              transition-all duration-200
              ${isSelected
                ? 'text-white shadow-md scale-105'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }
            `}
            style={isSelected ? { backgroundColor: store.color } : undefined}
          >
            <span>{store.icon}</span>
            <span>{store.name}</span>
            {count > 0 && (
              <span className={`
                px-2 py-0.5 rounded-full text-xs
                ${isSelected ? 'bg-white/20' : 'bg-gray-200 dark:bg-gray-600'}
              `}>
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
