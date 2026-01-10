# -*- coding: utf-8 -*-
"""
코스트코 공식몰 스크래퍼
- 상품 검색 및 카탈로그 수집
- Playwright 기반
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
class CostcoProduct:
    """코스트코 상품 정보"""
    product_code: str  # 상품 코드 (예: 666548)
    name: str
    price: int
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    unit_price: str = ""  # 단위 가격 (예: "10g당 300원")
    rating: float = 0.0
    review_count: int = 0

    def to_dict(self) -> dict:
        return {
            "product_code": self.product_code,
            "name": self.name,
            "price": self.price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "unit_price": self.unit_price,
            "rating": self.rating,
            "review_count": self.review_count,
        }


class CostcoScraper:
    """코스트코 공식몰 스크래퍼 (Playwright 기반)"""

    BASE_URL = "https://www.costco.co.kr"
    SEARCH_URL = "https://www.costco.co.kr/search"

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
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
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

    async def search_products(self, query: str, limit: int = 20) -> List[CostcoProduct]:
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
            encoded_query = urllib.parse.quote(query)
            search_url = f"{self.SEARCH_URL}?text={encoded_query}"

            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)  # JavaScript 렌더링 대기

            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 검색 실패 ({query}): {e}")
            return []

    async def _parse_search_results(self, limit: int) -> List[CostcoProduct]:
        """검색 결과 파싱 - JavaScript evaluate 방식"""
        products = []

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];
                const items = document.querySelectorAll('li[class*="product"]');

                items.forEach(item => {
                    try {
                        // 상품 링크에서 코드 추출
                        const link = item.querySelector('a[href*="/p/"]');
                        if (!link) return;

                        const href = link.getAttribute('href') || '';
                        const codeMatch = href.match(/\\/p\\/(\\d+)/);
                        if (!codeMatch) return;

                        const productCode = codeMatch[1];

                        // 상품명 추출
                        const nameEl = item.querySelector('a[href*="/p/"] + a') ||
                                       item.querySelector('a[href*="/p/"]');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        // 가격 추출
                        let price = 0;
                        const priceEl = item.querySelector('[class*="price"]');
                        if (priceEl) {
                            const priceText = priceEl.textContent || '';
                            const priceMatch = priceText.match(/([\\d,]+)원/);
                            if (priceMatch) {
                                price = parseInt(priceMatch[1].replace(/,/g, ''));
                            }
                        }

                        // 이미지 URL
                        const img = item.querySelector('img');
                        const imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '';

                        // 단위 가격
                        let unitPrice = '';
                        const unitPriceEl = item.querySelector('[class*="unit"]');
                        if (unitPriceEl) {
                            unitPrice = unitPriceEl.textContent.trim();
                        }

                        // 평점
                        let rating = 0;
                        let reviewCount = 0;
                        const ratingEl = item.querySelector('[class*="rating"]');
                        if (ratingEl) {
                            const ratingText = ratingEl.textContent || '';
                            const ratingMatch = ratingText.match(/(\\d+\\.?\\d*)\\s*\\((\\d+)\\)/);
                            if (ratingMatch) {
                                rating = parseFloat(ratingMatch[1]);
                                reviewCount = parseInt(ratingMatch[2]);
                            }
                        }

                        if (name && productCode) {
                            results.push({
                                productCode,
                                name,
                                price,
                                imgSrc,
                                href,
                                unitPrice,
                                rating,
                                reviewCount
                            });
                        }
                    } catch (e) {
                        // 개별 상품 파싱 실패 무시
                    }
                });

                return results;
            }''')

            if not product_data:
                print("[경고] 코스트코 상품을 찾지 못함")
                return products

            print(f"[정보] 코스트코에서 {len(product_data)}개 상품 발견")

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

                    href = item.get('href', '')
                    product_url = f"{self.BASE_URL}{href}" if href.startswith('/') else href

                    product = CostcoProduct(
                        product_code=product_code,
                        name=name,
                        price=item.get('price', 0),
                        image_url=item.get('imgSrc', ''),
                        product_url=product_url,
                        unit_price=item.get('unitPrice', ''),
                        rating=item.get('rating', 0),
                        review_count=item.get('reviewCount', 0),
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[에러] 결과 파싱 실패: {e}")

        return products

    async def get_category_products(self, category_url: str, limit: int = 50) -> List[CostcoProduct]:
        """
        카테고리 페이지에서 상품 수집

        Args:
            category_url: 카테고리 URL (예: /c/SpecialPriceOffers)
            limit: 최대 상품 수
        """
        if not self.page:
            await self._init_browser()

        try:
            full_url = f"{self.BASE_URL}{category_url}" if category_url.startswith('/') else category_url
            await self.page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 카테고리 수집 실패: {e}")
            return []

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


# 검색 키워드 설정
COSTCO_SEARCH_KEYWORDS = [
    "과자", "스낵", "견과류", "초콜릿", "커피",
    "음료", "생수", "주스", "차", "우유",
    "고기", "소고기", "돼지고기", "닭고기", "해산물",
    "과일", "채소", "샐러드", "냉동식품", "피자",
    "라면", "즉석밥", "통조림", "소스", "조미료",
    "세제", "화장지", "청소용품", "주방용품", "생활용품",
]

COSTCO_CATEGORIES = [
    "/c/SpecialPriceOffers",  # 스페셜 할인
    "/c/BuyersPick",  # Buyer's Pick
    "/c/whatsnew",  # 신상품
    "/Grocery",  # 그로서리
]


async def main():
    """테스트 실행"""
    print("=== 코스트코 스크래퍼 테스트 ===\n")

    scraper = CostcoScraper(headless=True)

    try:
        # 테스트: 상품 검색
        print("[테스트] 상품 검색: '과자'")
        products = await scraper.search_products("과자", limit=5)
        for p in products:
            print(f"  - {p.name}: {p.price:,}원 (코드: {p.product_code})")
            if p.rating:
                print(f"    평점: {p.rating} ({p.review_count}개 리뷰)")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
