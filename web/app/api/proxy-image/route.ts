import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'edge'

// 허용된 도메인 목록 (보안을 위해)
const ALLOWED_DOMAINS = [
  'daisomall.co.kr',
  'www.daisomall.co.kr',
  'image.daisomall.co.kr',
]

// Referer 매핑 (핫링크 보호 우회)
const REFERER_MAP: Record<string, string> = {
  'daisomall.co.kr': 'https://www.daisomall.co.kr/',
  'www.daisomall.co.kr': 'https://www.daisomall.co.kr/',
  'image.daisomall.co.kr': 'https://www.daisomall.co.kr/',
}

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

    // 도메인 검증
    const hostname = parsedUrl.hostname
    if (!ALLOWED_DOMAINS.some(domain => hostname.includes(domain))) {
      return new NextResponse('Domain not allowed', { status: 403 })
    }

    // 이미지 페치 (Referer 헤더 추가)
    const referer = REFERER_MAP[hostname] || `https://${hostname}/`

    const response = await fetch(imageUrl, {
      headers: {
        'Referer': referer,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
      },
    })

    if (!response.ok) {
      console.error(`Proxy fetch failed: ${response.status} for ${imageUrl}`)
      return new NextResponse('Image not found', { status: 404 })
    }

    // 이미지 데이터 반환
    const contentType = response.headers.get('content-type') || 'image/jpeg'
    const imageData = await response.arrayBuffer()

    return new NextResponse(imageData, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400, s-maxage=604800', // 1일 브라우저, 7일 CDN 캐시
        'Access-Control-Allow-Origin': '*',
      },
    })
  } catch (error) {
    console.error('Proxy error:', error)
    return new NextResponse('Internal server error', { status: 500 })
  }
}
