# -*- coding: utf-8 -*-
"""
트레이더스 (SSG.COM) 스크래퍼
- 이마트 트레이더스 상품 검색 및 카탈로그 수집
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
class TradersProduct:
    """트레이더스 상품 정보"""
    item_id: str  # 상품 ID
    name: str
    price: int = 0
    original_price: int = 0
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    brand: str = ""
    unit_price: str = ""  # 단위가격

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "price": self.price,
            "original_price": self.original_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "brand": self.brand,
            "unit_price": self.unit_price,
        }


class TradersScraper:
    """트레이더스 스크래퍼 (SSG.COM 기반)"""

    BASE_URL = "https://www.ssg.com"
    SEARCH_URL = "https://www.ssg.com/search.ssg"
    TRADERS_FILTER = "shpp_ctg=6005"  # 트레이더스 필터

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

    async def search_products(self, query: str, limit: int = 20) -> List[TradersProduct]:
        """
        상품 검색 (트레이더스 상품만)
        """
        if not self.page:
            await self._init_browser()

        try:
            encoded_query = urllib.parse.quote(query)
            # 트레이더스 상품만 필터링
            search_url = f"{self.SEARCH_URL}?target=all&query={encoded_query}&{self.TRADERS_FILTER}"

            print(f"[트레이더스] 검색: '{query}'")
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 트레이더스 검색 실패 ({query}): {e}")
            return []

    async def _parse_search_results(self, limit: int) -> List[TradersProduct]:
        """검색 결과 파싱"""
        products = []

        try:
            await self.page.wait_for_selector('ul.cunit_thmb_lst, #idProductImg, .cunit_prod', timeout=10000)
        except Exception:
            print("[경고] 트레이더스 상품 목록 로딩 타임아웃")

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];

                // SSG 상품 목록 선택자
                const items = document.querySelectorAll('li.cunit_t232, li.cunit_thmb_item, div.cunit_prod');

                items.forEach(item => {
                    try {
                        // 상품 ID
                        let itemId = item.getAttribute('data-info') || '';
                        if (itemId) {
                            try {
                                const info = JSON.parse(itemId);
                                itemId = info.itemId || '';
                            } catch (e) {
                                itemId = '';
                            }
                        }

                        const link = item.querySelector('a[href*="itemId="]');
                        if (!itemId && link) {
                            const href = link.getAttribute('href') || '';
                            const match = href.match(/itemId=([0-9]+)/);
                            if (match) itemId = match[1];
                        }

                        if (!itemId) return;

                        // 상품명
                        const nameEl = item.querySelector('.title, .cunit_info a em, .tit');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        // 브랜드
                        const brandEl = item.querySelector('.opt, .brand');
                        const brand = brandEl ? brandEl.textContent.trim() : '';

                        // 가격
                        let price = 0;
                        let originalPrice = 0;

                        const priceEl = item.querySelector('.ssg_price, .price .sale em, .new_price');
                        if (priceEl) {
                            const priceText = priceEl.textContent || '';
                            price = parseInt(priceText.replace(/[^0-9]/g, '')) || 0;
                        }

                        const origEl = item.querySelector('.old_price, del, .org_price');
                        if (origEl) {
                            const origText = origEl.textContent || '';
                            originalPrice = parseInt(origText.replace(/[^0-9]/g, '')) || 0;
                        }

                        // 이미지
                        const img = item.querySelector('img');
                        let imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '';
                        if (imgSrc.startsWith('//')) imgSrc = 'https:' + imgSrc;

                        // 상품 URL
                        let productUrl = '';
                        if (link) {
                            productUrl = link.getAttribute('href') || '';
                            if (productUrl.startsWith('/')) {
                                productUrl = 'https://www.ssg.com' + productUrl;
                            }
                        }

                        // 단위가격
                        const unitEl = item.querySelector('.unit, .unit_price');
                        const unitPrice = unitEl ? unitEl.textContent.trim() : '';

                        if (name && itemId) {
                            results.push({
                                itemId,
                                name,
                                brand,
                                price,
                                originalPrice,
                                imgSrc,
                                productUrl,
                                unitPrice
                            });
                        }
                    } catch (e) {}
                });

                return results;
            }''')

            if not product_data:
                print("[경고] 트레이더스 상품을 찾지 못함")
                return products

            print(f"[정보] 트레이더스에서 {len(product_data)}개 상품 발견")

            seen_ids = set()
            for item in product_data:
                try:
                    item_id = item.get('itemId', '')
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    name = item.get('name', '')
                    if not name:
                        continue

                    product = TradersProduct(
                        item_id=item_id,
                        name=name,
                        brand=item.get('brand', ''),
                        price=item.get('price', 0),
                        original_price=item.get('originalPrice', 0),
                        image_url=item.get('imgSrc', ''),
                        product_url=item.get('productUrl', ''),
                        unit_price=item.get('unitPrice', ''),
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception:
                    continue

        except Exception as e:
            print(f"[에러] 트레이더스 결과 파싱 실패: {e}")

        return products

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


TRADERS_SEARCH_KEYWORDS = [
    "과자", "스낵", "음료", "우유", "커피",
    "고기", "돼지고기", "소고기", "닭고기",
    "과일", "채소", "냉동식품", "라면",
    "세제", "화장지", "청소용품", "주방용품",
]


async def main():
    """테스트"""
    print("=== 트레이더스 스크래퍼 테스트 ===\n")
    scraper = TradersScraper(headless=True)
    try:
        products = await scraper.search_products("과자", limit=5)
        for p in products:
            print(f"  - {p.name}: {p.price:,}원")
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
