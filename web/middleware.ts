import { NextRequest, NextResponse } from 'next/server'

// Simple in-memory rate limiter for Middleware runtime
const rateLimitMap = new Map<string, { count: number; resetTime: number }>()
const RATE_LIMIT_WINDOW = 60 * 1000 // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 60 // /api default
const PROXY_IMAGE_MAX_REQUESTS = 30 // /api/proxy-image tighter limit

function sanitizeIp(rawIp: string | null): string | null {
  if (!rawIp) return null

  let value = rawIp.trim()
  if (!value) return null

  // Handle bracketed IPv6 with port: [::1]:3000
  if (value.startsWith('[')) {
    const match = value.match(/^\[([^\]]+)\](?::\d+)?$/)
    value = match ? match[1] : value
  } else if (/^\d{1,3}(?:\.\d{1,3}){3}:\d+$/.test(value)) {
    // IPv4 with port
    value = value.replace(/:\d+$/, '')
  }

  // Remove whitespace and allow only safe IP-like values to reduce spoofing attempts
  value = value.split(',')[0]?.trim() ?? ''
  if (!/^[0-9a-fA-F:.\-_%]+$/.test(value)) return null

  return value
}

function extractClientIp(request: NextRequest): string {
  const candidates = [
    request.headers.get('cf-connecting-ip'),
    request.headers.get('x-real-ip'),
    request.headers.get('x-client-ip'),
    request.headers.get('x-forwarded-for'),
    request.headers.get('forwarded'),
  ]

  for (const candidate of candidates) {
    if (!candidate) continue

    if (candidate.toLowerCase().startsWith('for=')) {
      const match = candidate.match(/for=([^;,]+)/i)
      const parsed = match ? sanitizeIp(match[1].replace(/"/g, '')) : sanitizeIp(candidate)
      if (parsed) return parsed
    }

    const parsed = sanitizeIp(candidate)
    if (parsed) return parsed
  }

  return 'unknown'
}

function getRateLimitConfig(pathname: string): { max: number } {
  if (pathname.startsWith('/api/proxy-image')) {
    return { max: PROXY_IMAGE_MAX_REQUESTS }
  }
  if (pathname.startsWith('/api/')) {
    return { max: RATE_LIMIT_MAX_REQUESTS }
  }
  return { max: 0 }
}

function isRateLimited(key: string, maxRequests: number): { limited: boolean; remaining: number; retryAfter: number } {
  const now = Date.now()
  const record = rateLimitMap.get(key)

  // Cleanup stale entries when map grows
  if (rateLimitMap.size > 10000) {
    rateLimitMap.forEach((v, k) => {
      if (v.resetTime < now) rateLimitMap.delete(k)
    })
  }

  if (!record || record.resetTime < now) {
    rateLimitMap.set(key, { count: 1, resetTime: now + RATE_LIMIT_WINDOW })
    return { limited: false, remaining: maxRequests - 1, retryAfter: RATE_LIMIT_WINDOW / 1000 }
  }

  record.count += 1
  if (record.count > maxRequests) {
    return {
      limited: true,
      remaining: 0,
      retryAfter: Math.max(1, Math.ceil((record.resetTime - now) / 1000)),
    }
  }

  return { limited: false, remaining: maxRequests - record.count, retryAfter: Math.ceil((record.resetTime - now) / 1000) }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const response = NextResponse.next()
  const { max } = getRateLimitConfig(pathname)

  if (max > 0) {
    const key = `${request.nextUrl.hostname}:${extractClientIp(request)}:${pathname}`
    const { limited, remaining, retryAfter } = isRateLimited(key, max)

    if (limited) {
      return new NextResponse(
        JSON.stringify({ error: 'Too many requests. Please try again later.' }),
        {
          status: 429,
          headers: {
            'Content-Type': 'application/json',
            'Retry-After': String(retryAfter),
            'X-RateLimit-Limit': String(max),
            'X-RateLimit-Remaining': '0',
          },
        }
      )
    }

    response.headers.set('X-RateLimit-Limit', String(max))
    response.headers.set('X-RateLimit-Remaining', String(remaining))
  }

  // Content Security Policy
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://www.youtube.com https://*.youtube.com",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https://*.daisomall.co.kr https://img.youtube.com https://*.ytimg.com https://*.coupang.com https://*.costco.co.kr https://*.ikea.com https://*.oliveyoung.co.kr",
    "font-src 'self'",
    "frame-src https://www.youtube.com https://*.youtube.com",
    "connect-src 'self' https://www.youtube.com https://*.youtube.com https://*.daisomall.co.kr",
    "media-src 'self' https:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'self'",
    'upgrade-insecure-requests',
  ].join('; ')

  response.headers.set('Content-Security-Policy', csp)
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('X-Frame-Options', 'SAMEORIGIN')
  response.headers.set('X-XSS-Protection', '0')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  response.headers.set('Permissions-Policy', 'camera=(self), microphone=(), geolocation=(self)')
  response.headers.set('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload')

  return response
}

export const config = {
  matcher: [
    // Match all paths except static files
    '/((?!_next/static|_next/image|favicon.ico|icon-|manifest.json|sw.js|data/).*)',
  ],
}
