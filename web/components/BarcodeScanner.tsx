'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Camera, X, Loader2, AlertCircle, Flashlight, SwitchCamera, Search } from 'lucide-react'

interface BarcodeScannerProps {
  isOpen: boolean
  onClose: () => void
  onScan: (code: string) => void
}

export function BarcodeScanner({ isOpen, onClose, onScan }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment')
  const [lastScanned, setLastScanned] = useState<string | null>(null)
  const [manualCode, setManualCode] = useState('')
  const [showManualInput, setShowManualInput] = useState(false)

  // Start camera
  const startCamera = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      // Stop existing stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }

      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: facingMode,
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      setIsLoading(false)
    } catch (err) {
      setIsLoading(false)
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          setError('카메라 권한이 거부되었습니다. 설정에서 카메라 권한을 허용해주세요.')
        } else if (err.name === 'NotFoundError') {
          setError('카메라를 찾을 수 없습니다.')
        } else {
          setError(`카메라 오류: ${err.message}`)
        }
      }
    }
  }, [facingMode])

  // Stop camera
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }, [])

  // Scan barcode using BarcodeDetector API (if available) or fallback
  const scanBarcode = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    ctx.drawImage(video, 0, 0)

    // Check if BarcodeDetector is available (Chrome 83+)
    if ('BarcodeDetector' in window) {
      try {
        // @ts-ignore - BarcodeDetector is not yet in TypeScript
        const barcodeDetector = new window.BarcodeDetector({
          formats: ['ean_13', 'ean_8', 'code_128', 'code_39', 'qr_code', 'upc_a', 'upc_e']
        })
        const barcodes = await barcodeDetector.detect(canvas)

        if (barcodes.length > 0) {
          const code = barcodes[0].rawValue
          if (code && code !== lastScanned) {
            setLastScanned(code)
            // Vibrate for feedback
            if (navigator.vibrate) {
              navigator.vibrate(100)
            }
            return code
          }
        }
      } catch (e) {
        console.log('BarcodeDetector error:', e)
      }
    }

    return null
  }, [lastScanned])

  // Scanning loop with race condition protection
  useEffect(() => {
    if (!isOpen || isLoading || error) return

    let animationFrame: number
    const isScanningRef = { current: true }

    const scan = async () => {
      if (!isScanningRef.current) return

      const code = await scanBarcode()

      // Check again after async operation to prevent race condition
      if (!isScanningRef.current) return

      if (code) {
        // Prevent multiple scans
        isScanningRef.current = false
        // Found barcode, call callback
        onScan(code)
        stopCamera()
        onClose()
        return
      }

      if (isScanningRef.current) {
        animationFrame = requestAnimationFrame(scan)
      }
    }

    scan()

    return () => {
      isScanningRef.current = false
      if (animationFrame) {
        cancelAnimationFrame(animationFrame)
      }
    }
  }, [isOpen, isLoading, error, scanBarcode, onScan, onClose, stopCamera])

  // Start/stop camera when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      startCamera()
    } else {
      stopCamera()
      setLastScanned(null)
      setShowManualInput(false)
      setManualCode('')
    }

    return () => {
      stopCamera()
    }
  }, [isOpen, startCamera, stopCamera])

  // Switch camera
  const switchCamera = () => {
    setFacingMode(prev => prev === 'environment' ? 'user' : 'environment')
  }

  // Handle manual input
  const handleManualSubmit = () => {
    if (manualCode.trim()) {
      onScan(manualCode.trim())
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[9999] bg-black flex flex-col"
      onClick={onClose}
    >
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3 bg-gradient-to-b from-black/70 to-transparent">
        <h2 className="text-white font-bold text-lg flex items-center gap-2">
          <Camera className="w-5 h-5" />
          바코드 스캔
        </h2>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onClose()
          }}
          className="p-2 bg-white/20 rounded-full hover:bg-white/30 transition-colors"
        >
          <X className="w-5 h-5 text-white" />
        </button>
      </div>

      {/* Camera View */}
      <div
        className="flex-1 flex items-center justify-center relative"
        onClick={e => e.stopPropagation()}
      >
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black z-20">
            <div className="flex flex-col items-center gap-3 text-white">
              <Loader2 className="w-10 h-10 animate-spin" />
              <p>카메라 시작 중...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black z-20 p-6">
            <div className="flex flex-col items-center gap-4 text-center">
              <AlertCircle className="w-16 h-16 text-red-400" />
              <p className="text-white">{error}</p>
              <div className="flex gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    startCamera()
                  }}
                  className="px-4 py-2 bg-white text-black rounded-lg font-medium"
                >
                  다시 시도
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setShowManualInput(true)
                  }}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg font-medium"
                >
                  직접 입력
                </button>
              </div>
            </div>
          </div>
        )}

        <video
          ref={videoRef}
          className="w-full h-full object-cover"
          playsInline
          muted
        />
        <canvas ref={canvasRef} className="hidden" />

        {/* Scan Guide */}
        {!isLoading && !error && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-64 h-40 relative">
              {/* Corner guides */}
              <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-green-400 rounded-tl-lg" />
              <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-green-400 rounded-tr-lg" />
              <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-green-400 rounded-bl-lg" />
              <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-green-400 rounded-br-lg" />

              {/* Scanning line animation */}
              <div className="absolute left-2 right-2 h-0.5 bg-green-400 animate-scan" />
            </div>
          </div>
        )}
      </div>

      {/* Bottom Controls */}
      <div className="absolute bottom-0 left-0 right-0 z-10 p-4 bg-gradient-to-t from-black/70 to-transparent">
        {showManualInput ? (
          <div className="flex gap-2">
            <input
              type="text"
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleManualSubmit()}
              placeholder="상품 코드를 입력하세요"
              className="flex-1 px-4 py-3 rounded-lg bg-white/90 text-black placeholder-gray-500"
              autoFocus
              onClick={e => e.stopPropagation()}
            />
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleManualSubmit()
              }}
              className="px-4 py-3 bg-green-500 text-white rounded-lg font-medium"
            >
              <Search className="w-5 h-5" />
            </button>
          </div>
        ) : (
          <>
            <p className="text-white/80 text-sm text-center mb-3">
              바코드를 사각형 안에 맞춰주세요
            </p>
            <div className="flex justify-center gap-4">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  switchCamera()
                }}
                className="p-3 bg-white/20 rounded-full hover:bg-white/30 transition-colors"
              >
                <SwitchCamera className="w-6 h-6 text-white" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setShowManualInput(true)
                }}
                className="px-4 py-2 bg-white/20 rounded-full hover:bg-white/30 transition-colors flex items-center gap-2"
              >
                <Search className="w-5 h-5 text-white" />
                <span className="text-white text-sm">직접 입력</span>
              </button>
            </div>
          </>
        )}
      </div>

      <style>{`
        @keyframes scan {
          0%, 100% { top: 10%; opacity: 0.5; }
          50% { top: 85%; opacity: 1; }
        }
        .animate-scan {
          animation: scan 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  )
}

// Hook to manage barcode scanner
export function useBarcodeScanner() {
  const [isOpen, setIsOpen] = useState(false)

  const openScanner = () => setIsOpen(true)
  const closeScanner = () => setIsOpen(false)

  return { isOpen, openScanner, closeScanner }
}
