import { NextRequest, NextResponse } from 'next/server'

// Node.js runtime 사용 (Edge 대신) - 헤더 처리가 더 안정적
export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

// 허용된 도메인 목록 (보안을 위해)
const ALLOWED_DOMAINS = [
  'daisomall.co.kr',
  'www.daisomall.co.kr',
  'image.daisomall.co.kr',
]

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const imageUrl = searchParams.get('url')

    if (!imageUrl) {
      return new NextResponse('Missing url parameter', { status: 400 })
    }

    // URL 검증
    let parsedUrl: URL
    try {
      parsedUrl = new URL(imageUrl)
    } catch {
      return new NextResponse('Invalid URL', { status: 400 })
    }

    // 도메인 검증 (SSRF 방지 - 정확한 매칭)
    const hostname = parsedUrl.hostname.toLowerCase()
    const isAllowedDomain = ALLOWED_DOMAINS.some(domain =>
      hostname === domain || hostname.endsWith('.' + domain)
    )
    if (!isAllowedDomain) {
      return new NextResponse('Domain not allowed', { status: 403 })
    }

    // 프로토콜 검증 (SSRF 방지)
    if (parsedUrl.protocol !== 'https:') {
      return new NextResponse('Only HTTPS allowed', { status: 403 })
    }

    // 이미지 페치 - 타임아웃 + 브라우저 헤더
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)

    let response: Response
    try {
      response = await fetch(imageUrl, {
        method: 'GET',
        headers: {
          'Host': hostname,
          'Referer': 'https://www.daisomall.co.kr/',
          'Origin': 'https://www.daisomall.co.kr',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
          'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
          'Accept-Encoding': 'gzip, deflate, br',
          'Connection': 'keep-alive',
          'Sec-Fetch-Dest': 'image',
          'Sec-Fetch-Mode': 'no-cors',
          'Sec-Fetch-Site': 'same-origin',
          'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
          'Sec-Ch-Ua-Mobile': '?0',
          'Sec-Ch-Ua-Platform': '"Windows"',
        },
        redirect: 'follow',
        signal: controller.signal,
      })
    } finally {
      clearTimeout(timeoutId)
    }

    if (!response.ok) {
      console.error(`[Proxy] Fetch failed: ${response.status} ${response.statusText} for ${imageUrl}`)
      return new NextResponse('Image not found', { status: 404 })
    }

    // Content-Type 검증
    const contentType = response.headers.get('content-type') || 'image/jpeg'
    if (!contentType.startsWith('image/')) {
      return new NextResponse('Not an image', { status: 403 })
    }

    // 응답 크기 제한 (5MB)
    const contentLength = parseInt(response.headers.get('content-length') || '0')
    if (contentLength > 5 * 1024 * 1024) {
      return new NextResponse('Image too large', { status: 413 })
    }

    const imageData = await response.arrayBuffer()

    return new NextResponse(imageData, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400, s-maxage=604800', // 1일 브라우저, 7일 CDN 캐시
        'Access-Control-Allow-Origin': 'https://web-keprojects.vercel.app',
      },
    })
  } catch (error) {
    console.error('[Proxy] Error:', error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
