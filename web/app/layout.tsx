import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({ subsets: ['latin'] })

const SITE_URL = 'https://web-keprojects.vercel.app'

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#1f2937' },
  ],
}

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: '꿀템장바구니 - 유튜버 추천 오프라인 매장 꿀템 모음',
    template: '%s | 꿀템장바구니',
  },
  description: '다이소, 코스트코, 이케아, 올리브영 등 유튜버가 실제 구매하고 추천한 꿀템만 모았습니다. 유튜버 추천 이유와 함께 확인하세요!',
  keywords: [
    '다이소 추천', '다이소 꿀템', '코스트코 추천', '코스트코 필수템',
    '이케아 추천', '올리브영 추천', '편의점 신상', '유튜버 추천',
    '쇼핑 추천', '가성비 추천', '오프라인 매장 추천'
  ],
  authors: [{ name: '꿀템장바구니' }],
  creator: '꿀템장바구니',
  publisher: '꿀템장바구니',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'ko_KR',
    url: SITE_URL,
    title: '꿀템장바구니 - 유튜버 추천 꿀템 모음',
    description: '유튜버가 실제 구매하고 추천한 다이소, 코스트코, 이케아 꿀템을 한눈에!',
    siteName: '꿀템장바구니',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: '꿀템장바구니 - 유튜버 추천 꿀템 모음',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: '꿀템장바구니 - 유튜버 추천 꿀템 모음',
    description: '유튜버가 실제 구매하고 추천한 다이소, 코스트코, 이케아 꿀템!',
    images: ['/og-image.png'],
  },
  verification: {
    google: 'google-site-verification-code', // TODO: 실제 코드로 교체
  },
  alternates: {
    canonical: SITE_URL,
    languages: {
      'ko-KR': SITE_URL,
      'en-US': `${SITE_URL}?lang=en`,
      'ja-JP': `${SITE_URL}?lang=ja`,
    },
  },
  category: 'shopping',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="꿀템장바구니" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="format-detection" content="telephone=no" />
      </head>
      <body className={inter.className}>
        <Providers>
          {children}
        </Providers>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js').then(function(registration) {
                    console.log('ServiceWorker registered: ', registration.scope);
                  }, function(err) {
                    console.log('ServiceWorker registration failed: ', err);
                  });
                });
              }
            `,
          }}
        />
      </body>
    </html>
  )
}
