# -*- coding: utf-8 -*-
"""
이케아 코리아 스크래퍼
- 상품 검색 및 카탈로그 수집
- Playwright 기반
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
class IkeaProduct:
    """이케아 상품 정보"""
    product_id: str  # 상품 ID (예: 00468539)
    name: str
    type_name: str = ""  # 상품 타입 (예: "책상", "수납장")
    price: int = 0
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    color: str = ""
    size: str = ""
    rating: float = 0.0
    review_count: int = 0

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "type_name": self.type_name,
            "price": self.price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "color": self.color,
            "size": self.size,
            "rating": self.rating,
            "review_count": self.review_count,
        }


class IkeaScraper:
    """이케아 코리아 스크래퍼"""

    BASE_URL = "https://www.ikea.com/kr/ko"
    SEARCH_URL = "https://www.ikea.com/kr/ko/search/"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        """브라우저 초기화"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ko-KR",
        )

        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        self.page = await self.context.new_page()

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

    async def search_products(self, query: str, limit: int = 20) -> List[IkeaProduct]:
        """상품 검색"""
        if not self.page:
            await self._init_browser()

        try:
            encoded_query = urllib.parse.quote(query)
            search_url = f"{self.SEARCH_URL}?q={encoded_query}"

            print(f"[이케아] 검색: '{query}'")
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)  # 이케아 로딩 느림

            # 쿠키 동의 팝업 닫기
            try:
                cookie_btn = await self.page.query_selector('#onetrust-accept-btn-handler')
                if cookie_btn:
                    await cookie_btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 이케아 검색 실패 ({query}): {e}")
            return []

    async def _parse_search_results(self, limit: int) -> List[IkeaProduct]:
        """검색 결과 파싱"""
        products = []

        try:
            await self.page.wait_for_selector('.plp-product-list, .search-results, .pip-product-compact', timeout=15000)
        except Exception:
            print("[경고] 이케아 상품 목록 로딩 타임아웃")

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];

                // 이케아 상품 카드 선택자
                const items = document.querySelectorAll('.pip-product-compact, .plp-product-list__item, [data-testid="product-card"]');

                items.forEach(item => {
                    try {
                        // 상품 링크에서 ID 추출
                        const link = item.querySelector('a[href*="/p/"]');
                        if (!link) return;

                        const href = link.getAttribute('href') || '';
                        const idMatch = href.match(/-([0-9]{8})/);
                        if (!idMatch) return;

                        const productId = idMatch[1];

                        // 상품명 (IKEA는 이름과 타입이 분리됨)
                        const nameEl = item.querySelector('.pip-header-section__title--small, .pip-header-section__title, [class*="product-name"]');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        const typeEl = item.querySelector('.pip-header-section__description-text, .pip-header-section__description, [class*="product-type"]');
                        const typeName = typeEl ? typeEl.textContent.trim() : '';

                        // 가격
                        let price = 0;
                        const priceEl = item.querySelector('.pip-temp-price__integer, .pip-price__integer, [class*="price"]');
                        if (priceEl) {
                            const priceText = priceEl.textContent || '';
                            price = parseInt(priceText.replace(/[^0-9]/g, '')) || 0;
                        }

                        // 이미지
                        const img = item.querySelector('img');
                        let imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '';

                        // 상품 URL
                        let productUrl = href;
                        if (productUrl.startsWith('/')) {
                            productUrl = 'https://www.ikea.com' + productUrl;
                        }

                        // 평점
                        let rating = 0;
                        let reviewCount = 0;
                        const ratingEl = item.querySelector('[class*="rating"]');
                        if (ratingEl) {
                            const ratingText = ratingEl.textContent || '';
                            const ratingMatch = ratingText.match(/(\\d+\\.?\\d*)/);
                            if (ratingMatch) rating = parseFloat(ratingMatch[1]);
                        }

                        if (name && productId) {
                            results.push({
                                productId,
                                name,
                                typeName,
                                price,
                                imgSrc,
                                productUrl,
                                rating,
                                reviewCount
                            });
                        }
                    } catch (e) {}
                });

                return results;
            }''')

            if not product_data:
                print("[경고] 이케아 상품을 찾지 못함")
                return products

            print(f"[정보] 이케아에서 {len(product_data)}개 상품 발견")

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

                    product = IkeaProduct(
                        product_id=product_id,
                        name=name,
                        type_name=item.get('typeName', ''),
                        price=item.get('price', 0),
                        image_url=item.get('imgSrc', ''),
                        product_url=item.get('productUrl', ''),
                        rating=item.get('rating', 0),
                        review_count=item.get('reviewCount', 0),
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception:
                    continue

        except Exception as e:
            print(f"[에러] 이케아 결과 파싱 실패: {e}")

        return products

    async def get_category_products(self, category_path: str, limit: int = 50) -> List[IkeaProduct]:
        """카테고리별 상품 수집"""
        if not self.page:
            await self._init_browser()

        try:
            category_url = f"{self.BASE_URL}/{category_path}"
            print(f"[이케아] 카테고리 접속: {category_path}")
            await self.page.goto(category_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            # 쿠키 동의
            try:
                cookie_btn = await self.page.query_selector('#onetrust-accept-btn-handler')
                if cookie_btn:
                    await cookie_btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 이케아 카테고리 수집 실패: {e}")
            return []

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


IKEA_SEARCH_KEYWORDS = [
    "책상", "의자", "수납장", "선반", "옷장",
    "소파", "테이블", "침대", "조명", "거울",
    "러그", "커튼", "쿠션", "이불", "베개",
    "주방용품", "식기", "냄비", "프라이팬", "수저",
    "수납", "정리", "바구니", "박스", "행거",
]

IKEA_CATEGORIES = [
    "cat/storage-furniture-10397",
    "cat/desks-20649",
    "cat/kitchen-products-20633",
    "cat/decoration-10757",
]


async def main():
    """테스트"""
    print("=== 이케아 스크래퍼 테스트 ===\n")
    scraper = IkeaScraper(headless=True)
    try:
        products = await scraper.search_products("책상", limit=5)
        for p in products:
            print(f"  - {p.name} ({p.type_name}): {p.price:,}원")
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
