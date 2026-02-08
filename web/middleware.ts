import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Simple in-memory rate limiter for Edge Runtime
const rateLimitMap = new Map<string, { count: number; resetTime: number }>()
const RATE_LIMIT_WINDOW = 60 * 1000 // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 60 // 60 requests per minute per IP

function getRateLimitKey(request: NextRequest): string {
  const forwarded = request.headers.get('x-forwarded-for')
  const ip = forwarded?.split(',')[0]?.trim() || request.headers.get('x-real-ip') || 'unknown'
  return ip
}

function isRateLimited(key: string): { limited: boolean; remaining: number } {
  const now = Date.now()
  const record = rateLimitMap.get(key)

  // Clean up old entries periodically
  if (rateLimitMap.size > 10000) {
    rateLimitMap.forEach((v, k) => {
      if (v.resetTime < now) rateLimitMap.delete(k)
    })
  }

  if (!record || record.resetTime < now) {
    rateLimitMap.set(key, { count: 1, resetTime: now + RATE_LIMIT_WINDOW })
    return { limited: false, remaining: RATE_LIMIT_MAX_REQUESTS - 1 }
  }

  record.count++
  if (record.count > RATE_LIMIT_MAX_REQUESTS) {
    return { limited: true, remaining: 0 }
  }

  return { limited: false, remaining: RATE_LIMIT_MAX_REQUESTS - record.count }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Rate limiting for API routes
  if (pathname.startsWith('/api/')) {
    const key = getRateLimitKey(request)
    const { limited, remaining } = isRateLimited(key)

    if (limited) {
      return new NextResponse(
        JSON.stringify({ error: 'Too many requests. Please try again later.' }),
        {
          status: 429,
          headers: {
            'Content-Type': 'application/json',
            'Retry-After': '60',
            'X-RateLimit-Limit': String(RATE_LIMIT_MAX_REQUESTS),
            'X-RateLimit-Remaining': '0',
          },
        }
      )
    }

    const response = NextResponse.next()
    response.headers.set('X-RateLimit-Limit', String(RATE_LIMIT_MAX_REQUESTS))
    response.headers.set('X-RateLimit-Remaining', String(remaining))
    return response
  }

  const response = NextResponse.next()

  // Content Security Policy (stricter - unsafe-inline only for style due to Tailwind)
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
    "upgrade-insecure-requests",
  ].join('; ')

  response.headers.set('Content-Security-Policy', csp)

  // Additional security headers
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
