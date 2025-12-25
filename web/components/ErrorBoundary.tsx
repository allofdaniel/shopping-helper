'use client'

import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-6 text-center">
          <AlertTriangle className="w-16 h-16 text-orange-500 mb-4" />
          <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200 mb-2">
            오류가 발생했습니다
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4 max-w-md">
            {this.state.error?.message || '알 수 없는 오류가 발생했습니다.'}
          </p>
          <button
            onClick={this.handleRetry}
            className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg
                     hover:bg-orange-600 transition-colors font-medium"
          >
            <RefreshCw className="w-4 h-4" />
            다시 시도
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

// API 에러 표시 컴포넌트
export function ApiErrorDisplay({
  error,
  onRetry,
  isRetrying = false,
}: {
  error: Error | null
  onRetry?: () => void
  isRetrying?: boolean
}) {
  if (!error) return null

  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
      <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
        <AlertTriangle className="w-8 h-8 text-red-500" />
      </div>
      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2">
        데이터를 불러올 수 없습니다
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 max-w-sm">
        네트워크 연결을 확인하고 다시 시도해주세요.
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          disabled={isRetrying}
          className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg
                   hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed
                   transition-colors font-medium"
        >
          <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
          {isRetrying ? '로딩 중...' : '다시 시도'}
        </button>
      )}
    </div>
  )
}

// 토스트 알림 컴포넌트
export function Toast({
  message,
  type = 'info',
  isVisible,
  onClose,
}: {
  message: string
  type?: 'success' | 'error' | 'info' | 'warning'
  isVisible: boolean
  onClose: () => void
}) {
  if (!isVisible) return null

  const bgColors = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
    warning: 'bg-orange-500',
  }

  return (
    <div
      className={`fixed bottom-24 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg text-white
                 text-sm font-medium shadow-lg ${bgColors[type]} animate-fade-in`}
      onClick={onClose}
    >
      {message}
    </div>
  )
}
