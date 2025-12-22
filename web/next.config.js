/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '*.daisomall.co.kr' },
      { protocol: 'https', hostname: '*.costco.co.kr' },
      { protocol: 'https', hostname: '*.ikea.com' },
      { protocol: 'https', hostname: '*.oliveyoung.co.kr' },
      { protocol: 'https', hostname: '*.ssg.com' },
      { protocol: 'https', hostname: '*.coupang.com' },
      { protocol: 'https', hostname: 'img.youtube.com' },
      { protocol: 'https', hostname: 'i.ytimg.com' },
      { protocol: 'https', hostname: '*.amazonaws.com' },
    ],
  },
}

module.exports = nextConfig
