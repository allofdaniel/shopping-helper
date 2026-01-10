# -*- coding: utf-8 -*-
"""
올리브영 공식몰 스크래퍼
- 상품 검색 및 카탈로그 수집
- Playwright 기반 + 봇 탐지 우회
"""
import re
import asyncio
import urllib.parse
from typing import Optional, List, Dict
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[!] Playwright 설치 필요: pip install playwright && playwright install chromium")


@dataclass
class OliveyoungProduct:
    """올리브영 상품 정보"""
    product_code: str  # 상품 코드
    name: str
    brand: str = ""
    price: int = 0
    original_price: int = 0  # 정가
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    rating: float = 0.0
    review_count: int = 0
    is_best: bool = False
    is_sale: bool = False

    def to_dict(self) -> dict:
        return {
            "product_code": self.product_code,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "original_price": self.original_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "rating": self.rating,
            "review_count": self.review_count,
            "is_best": self.is_best,
            "is_sale": self.is_sale,
        }


class OliveyoungScraper:
    """올리브영 공식몰 스크래퍼 (Playwright 기반 + 봇 우회)"""

    BASE_URL = "https://www.oliveyoung.co.kr"
    SEARCH_URL = "https://www.oliveyoung.co.kr/store/search/getSearchMain.do"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        """브라우저 초기화 (봇 탐지 우회 적용)"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다")

        self.playwright = await async_playwright().start()

        # 봇 탐지 우회를 위한 브라우저 설정
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
            ]
        )

        # 실제 사용자처럼 보이는 컨텍스트 설정
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            # 봇 탐지 우회
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
        )

        # webdriver 속성 숨기기
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });
            window.chrome = { runtime: {} };
        """)

        self.page = await self.context.new_page()

        # 추가 헤더 설정
        await self.page.set_extra_http_headers({
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
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

    async def _random_delay(self, min_sec: float = 1, max_sec: float = 3):
        """랜덤 딜레이 (봇 탐지 방지)"""
        import random
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def search_products(self, query: str, limit: int = 20) -> List[OliveyoungProduct]:
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
            # 먼저 메인 페이지 방문 (쿠키 획득)
            print(f"[올리브영] 메인 페이지 접속...")
            await self.page.goto(f"{self.BASE_URL}/store/main/main.do", wait_until="domcontentloaded", timeout=30000)
            await self._random_delay(2, 4)

            # 검색 페이지로 이동
            encoded_query = urllib.parse.quote(query)
            search_url = f"{self.SEARCH_URL}?query={encoded_query}"

            print(f"[올리브영] 검색: '{query}'")
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self._random_delay(3, 5)  # 검색 결과 로딩 대기

            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 올리브영 검색 실패 ({query}): {e}")
            return []

    async def _parse_search_results(self, limit: int) -> List[OliveyoungProduct]:
        """검색 결과 파싱 - JavaScript evaluate 방식"""
        products = []

        try:
            # 페이지 로딩 대기
            await self.page.wait_for_selector('ul.cate_prd_list, div.search_list, #Contents', timeout=10000)
        except Exception:
            print("[경고] 올리브영 상품 목록 로딩 타임아웃")

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];

                // 검색 결과 상품 목록 선택자들
                const selectors = [
                    'ul.cate_prd_list li',
                    'div.prd_info',
                    '.search_list li',
                    '#Contents ul li[data-ref-goodsno]'
                ];

                let items = [];
                for (const selector of selectors) {
                    items = document.querySelectorAll(selector);
                    if (items.length > 0) break;
                }

                items.forEach(item => {
                    try {
                        // 상품 코드 추출
                        let productCode = item.getAttribute('data-ref-goodsno') ||
                                         item.getAttribute('data-goods-no') || '';

                        // 링크에서 상품 코드 추출
                        const link = item.querySelector('a[href*="goodsNo="]');
                        if (!productCode && link) {
                            const href = link.getAttribute('href') || '';
                            const match = href.match(/goodsNo=([A-Z0-9]+)/i);
                            if (match) productCode = match[1];
                        }

                        if (!productCode) return;

                        // 브랜드명
                        const brandEl = item.querySelector('.tx_brand, .brand, .prd_brand');
                        const brand = brandEl ? brandEl.textContent.trim() : '';

                        // 상품명
                        const nameEl = item.querySelector('.tx_name, .prd_name, .name a');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        // 가격
                        let price = 0;
                        let originalPrice = 0;
                        const priceEl = item.querySelector('.tx_cur, .prd_price .price, .price');
                        if (priceEl) {
                            const priceText = priceEl.textContent || '';
                            const priceMatch = priceText.replace(/[^0-9]/g, '');
                            if (priceMatch) price = parseInt(priceMatch);
                        }

                        const origPriceEl = item.querySelector('.tx_org, .prd_price del, .org_price');
                        if (origPriceEl) {
                            const origText = origPriceEl.textContent || '';
                            const origMatch = origText.replace(/[^0-9]/g, '');
                            if (origMatch) originalPrice = parseInt(origMatch);
                        }

                        // 이미지 URL
                        const img = item.querySelector('img');
                        let imgSrc = '';
                        if (img) {
                            imgSrc = img.getAttribute('src') || img.getAttribute('data-src') || '';
                            if (imgSrc.startsWith('//')) imgSrc = 'https:' + imgSrc;
                        }

                        // 상품 URL
                        let productUrl = '';
                        if (link) {
                            productUrl = link.getAttribute('href') || '';
                            if (productUrl.startsWith('/')) {
                                productUrl = 'https://www.oliveyoung.co.kr' + productUrl;
                            }
                        }

                        // 평점
                        let rating = 0;
                        let reviewCount = 0;
                        const ratingEl = item.querySelector('.point, .review_point');
                        if (ratingEl) {
                            const ratingText = ratingEl.textContent || '';
                            const ratingMatch = ratingText.match(/(\\d+\\.?\\d*)/);
                            if (ratingMatch) rating = parseFloat(ratingMatch[1]);
                        }
                        const reviewEl = item.querySelector('.count, .review_count');
                        if (reviewEl) {
                            const reviewText = reviewEl.textContent || '';
                            const reviewMatch = reviewText.replace(/[^0-9]/g, '');
                            if (reviewMatch) reviewCount = parseInt(reviewMatch);
                        }

                        // 베스트/세일 뱃지
                        const isBest = !!item.querySelector('.badge_best, .best, .icon_best');
                        const isSale = !!item.querySelector('.badge_sale, .sale, .icon_sale') || originalPrice > price;

                        if (name && productCode) {
                            results.push({
                                productCode,
                                name,
                                brand,
                                price,
                                originalPrice,
                                imgSrc,
                                productUrl,
                                rating,
                                reviewCount,
                                isBest,
                                isSale
                            });
                        }
                    } catch (e) {
                        // 개별 상품 파싱 실패 무시
                    }
                });

                return results;
            }''')

            if not product_data:
                print("[경고] 올리브영 상품을 찾지 못함 - 페이지 구조 확인 필요")
                # 디버깅: 현재 페이지 HTML 일부 출력
                page_content = await self.page.content()
                if "blocked" in page_content.lower() or "captcha" in page_content.lower():
                    print("[!] 봇 차단 또는 캡챠 감지됨")
                return products

            print(f"[정보] 올리브영에서 {len(product_data)}개 상품 발견")

            seen_codes = set()
            for item in product_data:
                try:
                    product_code = item.get('productCode', '')
                    if not product_code or product_code in seen_codes:
                        continue

                    seen_codes.add(product_code)

                    name = item.get('name', '')
                    if not name:
                        continue

                    product = OliveyoungProduct(
                        product_code=product_code,
                        name=name,
                        brand=item.get('brand', ''),
                        price=item.get('price', 0),
                        original_price=item.get('originalPrice', 0),
                        image_url=item.get('imgSrc', ''),
                        product_url=item.get('productUrl', ''),
                        rating=item.get('rating', 0),
                        review_count=item.get('reviewCount', 0),
                        is_best=item.get('isBest', False),
                        is_sale=item.get('isSale', False),
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[에러] 올리브영 결과 파싱 실패: {e}")

        return products

    async def get_category_products(self, category_code: str, limit: int = 50) -> List[OliveyoungProduct]:
        """
        카테고리 페이지에서 상품 수집

        Args:
            category_code: 카테고리 코드 (예: 100000100010013)
            limit: 최대 상품 수
        """
        if not self.page:
            await self._init_browser()

        try:
            category_url = f"{self.BASE_URL}/store/display/getMCategoryList.do?dispCatNo={category_code}"
            print(f"[올리브영] 카테고리 접속: {category_code}")
            await self.page.goto(category_url, wait_until="domcontentloaded", timeout=30000)
            await self._random_delay(3, 5)

            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 올리브영 카테고리 수집 실패: {e}")
            return []

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


# 검색 키워드 설정
OLIVEYOUNG_SEARCH_KEYWORDS = [
    "선크림", "클렌징", "토너", "에센스", "크림",
    "마스크팩", "립스틱", "파운데이션", "쿠션", "아이라이너",
    "샴푸", "트리트먼트", "바디로션", "핸드크림", "향수",
    "비타민", "영양제", "다이어트", "건강식품", "유산균",
]

# 주요 카테고리 코드
OLIVEYOUNG_CATEGORIES = {
    "스킨케어": "100000100010013",
    "마스크팩": "100000100010014",
    "클렌징": "100000100010010",
    "선케어": "100000100010015",
    "메이크업": "100000100020000",
    "헤어케어": "100000100050000",
    "바디케어": "100000100060000",
    "건강식품": "100000100100000",
}


async def main():
    """테스트 실행"""
    print("=== 올리브영 스크래퍼 테스트 ===\n")

    scraper = OliveyoungScraper(headless=True)

    try:
        # 테스트: 상품 검색
        print("[테스트] 상품 검색: '선크림'")
        products = await scraper.search_products("선크림", limit=5)

        if products:
            for p in products:
                print(f"  - [{p.brand}] {p.name}: {p.price:,}원 (코드: {p.product_code})")
                if p.rating:
                    print(f"    평점: {p.rating} ({p.review_count}개 리뷰)")
        else:
            print("  -> 상품을 찾지 못했습니다")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
