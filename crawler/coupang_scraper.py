# -*- coding: utf-8 -*-
"""
쿠팡 상품 스크래퍼
- 상품 검색 및 카탈로그 수집
- Playwright 기반 + 강화된 봇 탐지 우회
"""
import re
import asyncio
import urllib.parse
import random
from typing import Optional, List, Dict
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[!] Playwright 설치 필요: pip install playwright && playwright install chromium")


@dataclass
class CoupangProduct:
    """쿠팡 상품 정보"""
    product_id: str  # 상품 ID
    name: str
    price: int = 0
    original_price: int = 0  # 정가
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    rating: float = 0.0
    review_count: int = 0
    is_rocket: bool = False  # 로켓배송 여부
    is_rocket_fresh: bool = False  # 로켓프레시 여부
    seller: str = ""

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "price": self.price,
            "original_price": self.original_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "rating": self.rating,
            "review_count": self.review_count,
            "is_rocket": self.is_rocket,
            "is_rocket_fresh": self.is_rocket_fresh,
            "seller": self.seller,
        }


class CoupangScraper:
    """쿠팡 스크래퍼 (Playwright 기반 + 강화된 봇 우회)"""

    BASE_URL = "https://www.coupang.com"
    SEARCH_URL = "https://www.coupang.com/np/search"

    # 다양한 User-Agent 목록
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        """브라우저 초기화 (강화된 봇 탐지 우회)"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다")

        self.playwright = await async_playwright().start()

        # 쿠팡 봇 탐지 우회를 위한 강화된 브라우저 설정
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-background-timer-throttling',
                '--disable-popup-blocking',
                '--disable-extensions',
                '--window-size=1920,1080',
                '--start-maximized',
            ]
        )

        # 랜덤 User-Agent 선택
        user_agent = random.choice(self.USER_AGENTS)

        # 실제 사용자처럼 보이는 컨텍스트 설정
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent,
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
            color_scheme="light",
            # 쿠키 허용
            accept_downloads=True,
        )

        # 강화된 봇 탐지 우회 스크립트
        await self.context.add_init_script("""
            // webdriver 속성 숨기기
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // plugins 속성 설정
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin' }
                    ];
                }
            });

            // languages 설정
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });

            // platform 설정
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            // hardwareConcurrency 설정
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            // chrome 객체 설정
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // permissions 설정
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // 콘솔 로그 숨기기 (디버깅 감지 방지)
            const originalConsole = window.console;
        """)

        self.page = await self.context.new_page()

        # 추가 헤더 설정
        await self.page.set_extra_http_headers({
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        })

    async def _close_browser(self):
        """브라우저 종료"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None

    async def _random_delay(self, min_sec: float = 2, max_sec: float = 5):
        """랜덤 딜레이 (봇 탐지 방지)"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def _human_like_scroll(self):
        """인간처럼 스크롤 (봇 탐지 방지)"""
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(300, 700)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.5, 1.5))

    async def search_products(self, query: str, limit: int = 20) -> List[CoupangProduct]:
        """
        상품 검색

        Args:
            query: 검색어
            limit: 최대 결과 수

        Returns:
            검색된 상품 목록
        """
        if not self.page:
            await self._init_browser()

        try:
            # 먼저 메인 페이지 방문 (쿠키 획득 및 세션 초기화)
            print(f"[쿠팡] 메인 페이지 접속...")
            await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await self._random_delay(3, 5)

            # 인간처럼 스크롤
            await self._human_like_scroll()

            # 검색 페이지로 이동
            encoded_query = urllib.parse.quote(query)
            search_url = f"{self.SEARCH_URL}?q={encoded_query}&channel=user"

            print(f"[쿠팡] 검색: '{query}'")
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self._random_delay(3, 6)

            # 스크롤하여 더 많은 상품 로드
            await self._human_like_scroll()

            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 쿠팡 검색 실패 ({query}): {e}")
            return []

    async def _parse_search_results(self, limit: int) -> List[CoupangProduct]:
        """검색 결과 파싱 - JavaScript evaluate 방식"""
        products = []

        try:
            # 페이지 로딩 대기
            await self.page.wait_for_selector('#productList, .search-product, ul[class*="product"]', timeout=15000)
        except Exception:
            print("[경고] 쿠팡 상품 목록 로딩 타임아웃")
            # 봇 차단 확인
            page_content = await self.page.content()
            if "차단" in page_content or "blocked" in page_content.lower() or len(page_content) < 1000:
                print("[!] 쿠팡 봇 차단 감지됨 - 잠시 후 재시도 필요")
                return products

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];

                // 쿠팡 검색 결과 상품 목록 선택자들
                const selectors = [
                    '#productList li.search-product',
                    'ul.search-product-list li',
                    'li[class*="search-product"]',
                    '.baby-product-list li'
                ];

                let items = [];
                for (const selector of selectors) {
                    items = document.querySelectorAll(selector);
                    if (items.length > 0) break;
                }

                items.forEach(item => {
                    try {
                        // 상품 ID 추출
                        let productId = item.getAttribute('data-product-id') ||
                                       item.getAttribute('data-item-id') || '';

                        // 링크에서 상품 ID 추출
                        const link = item.querySelector('a[href*="/vp/products/"], a.search-product-link');
                        if (!productId && link) {
                            const href = link.getAttribute('href') || '';
                            const match = href.match(/products\\/([0-9]+)/);
                            if (match) productId = match[1];
                        }

                        if (!productId) return;

                        // 상품명
                        const nameEl = item.querySelector('.name, .product-name, .title, [class*="name"]');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        // 가격
                        let price = 0;
                        let originalPrice = 0;

                        const priceEl = item.querySelector('.price-value, .price, [class*="sale-price"]');
                        if (priceEl) {
                            const priceText = priceEl.textContent || '';
                            const priceMatch = priceText.replace(/[^0-9]/g, '');
                            if (priceMatch) price = parseInt(priceMatch);
                        }

                        const origPriceEl = item.querySelector('.base-price, del, .origin-price');
                        if (origPriceEl) {
                            const origText = origPriceEl.textContent || '';
                            const origMatch = origText.replace(/[^0-9]/g, '');
                            if (origMatch) originalPrice = parseInt(origMatch);
                        }

                        // 이미지 URL
                        const img = item.querySelector('img');
                        let imgSrc = '';
                        if (img) {
                            imgSrc = img.getAttribute('src') || img.getAttribute('data-img-src') || '';
                            if (imgSrc.startsWith('//')) imgSrc = 'https:' + imgSrc;
                        }

                        // 상품 URL
                        let productUrl = '';
                        if (link) {
                            productUrl = link.getAttribute('href') || '';
                            if (productUrl.startsWith('/')) {
                                productUrl = 'https://www.coupang.com' + productUrl;
                            }
                        }

                        // 평점
                        let rating = 0;
                        let reviewCount = 0;
                        const ratingEl = item.querySelector('.rating, .star, [class*="rating"]');
                        if (ratingEl) {
                            const ratingText = ratingEl.textContent || ratingEl.getAttribute('data-rating') || '';
                            const ratingMatch = ratingText.match(/(\\d+\\.?\\d*)/);
                            if (ratingMatch) rating = parseFloat(ratingMatch[1]);
                        }
                        const reviewEl = item.querySelector('.rating-total-count, .count, [class*="review"]');
                        if (reviewEl) {
                            const reviewText = reviewEl.textContent || '';
                            const reviewMatch = reviewText.replace(/[^0-9]/g, '');
                            if (reviewMatch) reviewCount = parseInt(reviewMatch);
                        }

                        // 로켓배송 여부
                        const isRocket = !!item.querySelector('.badge-rocket, .rocket, img[alt*="로켓"], [class*="rocket"]');
                        const isRocketFresh = !!item.querySelector('.badge-rocket-fresh, .rocket-fresh, img[alt*="프레시"]');

                        // 판매자
                        const sellerEl = item.querySelector('.merchant-name, .seller');
                        const seller = sellerEl ? sellerEl.textContent.trim() : '';

                        if (name && productId) {
                            results.push({
                                productId,
                                name,
                                price,
                                originalPrice,
                                imgSrc,
                                productUrl,
                                rating,
                                reviewCount,
                                isRocket,
                                isRocketFresh,
                                seller
                            });
                        }
                    } catch (e) {
                        // 개별 상품 파싱 실패 무시
                    }
                });

                return results;
            }''')

            if not product_data:
                print("[경고] 쿠팡 상품을 찾지 못함")
                return products

            print(f"[정보] 쿠팡에서 {len(product_data)}개 상품 발견")

            seen_ids = set()
            for item in product_data:
                try:
                    product_id = item.get('productId', '')
                    if not product_id or product_id in seen_ids:
                        continue

                    seen_ids.add(product_id)

                    name = item.get('name', '')
                    if not name:
                        continue

                    product = CoupangProduct(
                        product_id=product_id,
                        name=name,
                        price=item.get('price', 0),
                        original_price=item.get('originalPrice', 0),
                        image_url=item.get('imgSrc', ''),
                        product_url=item.get('productUrl', ''),
                        rating=item.get('rating', 0),
                        review_count=item.get('reviewCount', 0),
                        is_rocket=item.get('isRocket', False),
                        is_rocket_fresh=item.get('isRocketFresh', False),
                        seller=item.get('seller', ''),
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[에러] 쿠팡 결과 파싱 실패: {e}")

        return products

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


# 검색 키워드 설정 (쿠팡 추천템 관련)
COUPANG_SEARCH_KEYWORDS = [
    "생활용품", "주방용품", "욕실용품", "청소용품", "수납정리",
    "식품", "과자", "음료", "라면", "즉석식품",
    "건강식품", "비타민", "유산균", "다이어트",
    "화장품", "스킨케어", "메이크업", "향수",
    "가전", "주방가전", "생활가전", "계절가전",
]


async def main():
    """테스트 실행"""
    print("=== 쿠팡 스크래퍼 테스트 ===\n")

    scraper = CoupangScraper(headless=True)

    try:
        # 테스트: 상품 검색
        print("[테스트] 상품 검색: '생활용품'")
        products = await scraper.search_products("생활용품", limit=5)

        if products:
            for p in products:
                rocket = "🚀" if p.is_rocket else ""
                print(f"  - {p.name}: {p.price:,}원 {rocket} (ID: {p.product_id})")
                if p.rating:
                    print(f"    평점: {p.rating} ({p.review_count}개 리뷰)")
        else:
            print("  -> 상품을 찾지 못했습니다 (봇 차단 가능성)")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
