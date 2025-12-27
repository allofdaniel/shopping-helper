'use client'

import type { Product } from '@/lib/types'

const SITE_URL = 'https://web-keprojects.vercel.app'

// 웹사이트 구조화 데이터
export function WebsiteJsonLd() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: '꿀템장바구니',
    alternateName: 'HoneyCart',
    url: SITE_URL,
    description: '유튜버가 추천한 다이소, 코스트코, 이케아 꿀템을 한눈에 모아보세요',
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${SITE_URL}?search={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  )
}

// 상품 목록 구조화 데이터
export function ProductListJsonLd({ products }: { products: Product[] }) {
  const itemListElements = products.slice(0, 50).map((product, index) => ({
    '@type': 'ListItem',
    position: index + 1,
    item: {
      '@type': 'Product',
      name: product.official_name || product.name,
      description: product.recommendation || `${product.channel_name}님이 추천한 ${product.name}`,
      image: product.thumbnail,
      offers: {
        '@type': 'Offer',
        price: product.official_price || product.price || 0,
        priceCurrency: 'KRW',
        availability: 'https://schema.org/InStock',
      },
      brand: {
        '@type': 'Brand',
        name: product.store_key === 'daiso' ? '다이소' :
              product.store_key === 'costco' ? '코스트코' :
              product.store_key === 'ikea' ? '이케아' :
              product.store_key === 'oliveyoung' ? '올리브영' : '기타',
      },
    },
  }))

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: '유튜버 추천 꿀템 목록',
    description: '유튜버가 실제 구매하고 추천한 상품 목록',
    numberOfItems: products.length,
    itemListElement: itemListElements,
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  )
}

// 조직 구조화 데이터
export function OrganizationJsonLd() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: '꿀템장바구니',
    url: SITE_URL,
    logo: `${SITE_URL}/icon-512.png`,
    sameAs: [],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  )
}

// FAQ 구조화 데이터
export function FaqJsonLd() {
  const faqs = [
    {
      question: '꿀템장바구니는 어떤 서비스인가요?',
      answer: '유튜버가 실제로 구매하고 추천한 다이소, 코스트코, 이케아 등 오프라인 매장의 상품들을 모아서 보여주는 서비스입니다. 유튜버의 추천 이유와 함께 상품 정보를 확인할 수 있습니다.',
    },
    {
      question: '상품 정보는 얼마나 자주 업데이트 되나요?',
      answer: '매일 오전 9시와 오후 9시(한국 시간)에 자동으로 새로운 영상을 수집하여 상품 정보를 업데이트합니다.',
    },
    {
      question: '어떤 매장의 상품을 볼 수 있나요?',
      answer: '현재 다이소, 코스트코, 이케아, 올리브영, 편의점(CU, GS25, 세븐일레븐) 상품을 확인할 수 있습니다.',
    },
  ]

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((faq) => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  )
}
