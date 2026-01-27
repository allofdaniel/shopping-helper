import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const response = NextResponse.next()

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
    // Match all paths except static files and api routes
    '/((?!_next/static|_next/image|favicon.ico|icon-|manifest.json|sw.js|data/).*)',
  ],
}
