import { MetadataRoute } from 'next'

const SITE_URL = 'https://web-keprojects.vercel.app'

export default function sitemap(): MetadataRoute.Sitemap {
  const stores = ['daiso', 'costco', 'ikea', 'oliveyoung', 'convenience']
  const categories = ['kitchen', 'living', 'beauty', 'interior', 'food', 'digital']

  // 기본 페이지
  const mainPages: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
  ]

  // 매장별 페이지
  const storePages: MetadataRoute.Sitemap = stores.map((store) => ({
    url: `${SITE_URL}?store=${store}`,
    lastModified: new Date(),
    changeFrequency: 'daily' as const,
    priority: 0.8,
  }))

  // 카테고리별 페이지
  const categoryPages: MetadataRoute.Sitemap = categories.map((category) => ({
    url: `${SITE_URL}?category=${category}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.6,
  }))

  return [...mainPages, ...storePages, ...categoryPages]
}
