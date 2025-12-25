'use client'

import { useState, useEffect, useCallback } from 'react'

type Theme = 'light' | 'dark' | 'system'

const THEME_KEY = 'shopping_helper_theme'

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>('system')
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light')
  const [mounted, setMounted] = useState(false)

  // 시스템 테마 감지
  const getSystemTheme = useCallback((): 'light' | 'dark' => {
    if (typeof window === 'undefined') return 'light'
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }, [])

  // 테마 적용
  const applyTheme = useCallback((newTheme: Theme) => {
    const root = document.documentElement
    const resolved = newTheme === 'system' ? getSystemTheme() : newTheme

    if (resolved === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }

    setResolvedTheme(resolved)
  }, [getSystemTheme])

  // 초기화
  useEffect(() => {
    const saved = localStorage.getItem(THEME_KEY) as Theme | null
    const initialTheme = saved || 'system'
    setThemeState(initialTheme)
    applyTheme(initialTheme)
    setMounted(true)
  }, [applyTheme])

  // 시스템 테마 변경 감지
  useEffect(() => {
    if (theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme('system')

    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [theme, applyTheme])

  // 테마 변경
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem(THEME_KEY, newTheme)
    applyTheme(newTheme)
  }, [applyTheme])

  // 테마 토글 (라이트 ↔ 다크)
  const toggleTheme = useCallback(() => {
    const newTheme = resolvedTheme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
  }, [resolvedTheme, setTheme])

  return {
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme,
    mounted,
  }
}
