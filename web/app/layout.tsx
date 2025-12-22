import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '꿀템장바구니 - 유튜버 추천 상품 모음',
  description: '다이소, 코스트코, 트레이더스, 이케아, 올리브영 등 유튜버가 추천한 꿀템을 한눈에!',
  keywords: ['다이소', '코스트코', '트레이더스', '이케아', '올리브영', '편의점', '쿠팡', '꿀템', '추천'],
  openGraph: {
    title: '꿀템장바구니',
    description: '유튜버가 추천한 꿀템을 한눈에!',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
