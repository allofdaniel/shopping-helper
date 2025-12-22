'use client'

import { CATEGORIES } from '@/lib/types'

interface CategoryFilterProps {
  selectedCategory: string
  onSelectCategory: (category: string) => void
  counts?: Record<string, number>
}

export function CategoryFilter({ selectedCategory, onSelectCategory, counts = {} }: CategoryFilterProps) {
  const categories = [
    { key: 'all', name: '전체', icon: '📦' },
    ...Object.values(CATEGORIES),
  ]

  return (
    <div className="flex flex-wrap gap-2">
      {categories.map((category) => {
        const isSelected = selectedCategory === category.key
        const count = category.key === 'all'
          ? Object.values(counts).reduce((a, b) => a + b, 0)
          : counts[category.key] || 0

        return (
          <button
            key={category.key}
            onClick={() => onSelectCategory(category.key)}
            className={`
              flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
              transition-all duration-200
              ${isSelected
                ? 'bg-blue-500 text-white shadow-sm'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }
            `}
          >
            <span>{category.icon}</span>
            <span>{category.name}</span>
            {count > 0 && (
              <span className={`
                text-xs
                ${isSelected ? 'text-blue-100' : 'text-gray-400'}
              `}>
                ({count})
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
