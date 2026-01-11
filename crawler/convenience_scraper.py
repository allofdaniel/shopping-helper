# -*- coding: utf-8 -*-
"""
편의점 스크래퍼 (CU, GS25, 세븐일레븐, 이마트24)
- 신상품, 행사상품 수집
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
class ConvenienceProduct:
    """편의점 상품 정보"""
    product_id: str
    name: str
    price: int = 0
    original_price: int = 0
    image_url: str = ""
    product_url: str = ""
    store: str = ""  # cu, gs25, seveneleven, emart24
    category: str = ""
    event_type: str = ""  # 1+1, 2+1, 할인 등
    is_new: bool = False
    is_pb: bool = False  # PB 상품 여부

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "price": self.price,
            "original_price": self.original_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "store": self.store,
            "category": self.category,
            "event_type": self.event_type,
            "is_new": self.is_new,
            "is_pb": self.is_pb,
        }


class CUScraper:
    """CU 편의점 스크래퍼"""

    BASE_URL = "https://cu.bgfretail.com"
    EVENT_URL = "https://cu.bgfretail.com/event/plus.do"
    NEW_URL = "https://cu.bgfretail.com/product/productNewList.do"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.page = await self.context.new_page()

    async def _close_browser(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except Exception:
            pass

    async def get_event_products(self, event_type: str = "1+1", limit: int = 30) -> List[ConvenienceProduct]:
        """행사 상품 수집 (1+1, 2+1)"""
        if not self.page:
            await self._init_browser()

        try:
            print(f"[CU] 행사 상품 수집: {event_type}")
            await self.page.goto(self.EVENT_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # 탭 선택 (1+1, 2+1)
            if event_type == "2+1":
                tab = await self.page.query_selector('a[data-tab="2"]')
                if tab:
                    await tab.click()
                    await asyncio.sleep(2)

            products = await self._parse_products("cu", event_type, limit)
            return products

        except Exception as e:
            print(f"[에러] CU 행사 상품 수집 실패: {e}")
            return []

    async def get_new_products(self, limit: int = 30) -> List[ConvenienceProduct]:
        """신상품 수집"""
        if not self.page:
            await self._init_browser()

        try:
            print("[CU] 신상품 수집")
            await self.page.goto(self.NEW_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            products = await self._parse_products("cu", "신상품", limit, is_new=True)
            return products

        except Exception as e:
            print(f"[에러] CU 신상품 수집 실패: {e}")
            return []

    async def _parse_products(self, store: str, event_type: str, limit: int, is_new: bool = False) -> List[ConvenienceProduct]:
        products = []

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];
                const items = document.querySelectorAll('.prod_list li, .product_list li, ul.list li');

                items.forEach((item, idx) => {
                    try {
                        const nameEl = item.querySelector('.name, .prod_name, .tit');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        const priceEl = item.querySelector('.price, .cost, .won');
                        let price = 0;
                        if (priceEl) {
                            price = parseInt(priceEl.textContent.replace(/[^0-9]/g, '')) || 0;
                        }

                        const img = item.querySelector('img');
                        let imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '';

                        if (name) {
                            results.push({
                                productId: 'CU_' + idx,
                                name,
                                price,
                                imgSrc
                            });
                        }
                    } catch (e) {}
                });

                return results;
            }''')

            for item in product_data[:limit]:
                product = ConvenienceProduct(
                    product_id=item.get('productId', ''),
                    name=item.get('name', ''),
                    price=item.get('price', 0),
                    image_url=item.get('imgSrc', ''),
                    store=store,
                    event_type=event_type,
                    is_new=is_new,
                )
                products.append(product)

        except Exception as e:
            print(f"[에러] 파싱 실패: {e}")

        print(f"[정보] {store.upper()}에서 {len(products)}개 상품 발견")
        return products

    async def close(self):
        await self._close_browser()


class GS25Scraper:
    """GS25 편의점 스크래퍼"""

    BASE_URL = "https://gs25.gsretail.com"
    EVENT_URL = "https://gs25.gsretail.com/gscvs/ko/products/event-goods"
    NEW_URL = "https://gs25.gsretail.com/gscvs/ko/products/youus-freshfood"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.page = await self.context.new_page()

    async def _close_browser(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except Exception:
            pass

    async def get_event_products(self, limit: int = 30) -> List[ConvenienceProduct]:
        """행사 상품 수집"""
        if not self.page:
            await self._init_browser()

        try:
            print("[GS25] 행사 상품 수집")
            await self.page.goto(self.EVENT_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            products = await self._parse_products("gs25", limit)
            return products

        except Exception as e:
            print(f"[에러] GS25 행사 상품 수집 실패: {e}")
            return []

    async def _parse_products(self, store: str, limit: int) -> List[ConvenienceProduct]:
        products = []

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];
                const items = document.querySelectorAll('.prod_box, .product_list li, .prd_item');

                items.forEach((item, idx) => {
                    try {
                        const nameEl = item.querySelector('.tit, .prd_name, .name');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        const priceEl = item.querySelector('.price, .cost');
                        let price = 0;
                        if (priceEl) {
                            price = parseInt(priceEl.textContent.replace(/[^0-9]/g, '')) || 0;
                        }

                        const img = item.querySelector('img');
                        let imgSrc = img ? (img.getAttribute('src') || '') : '';

                        // 행사 타입
                        const eventEl = item.querySelector('.flag, .badge, .event_type');
                        const eventType = eventEl ? eventEl.textContent.trim() : '';

                        if (name) {
                            results.push({
                                productId: 'GS_' + idx,
                                name,
                                price,
                                imgSrc,
                                eventType
                            });
                        }
                    } catch (e) {}
                });

                return results;
            }''')

            for item in product_data[:limit]:
                product = ConvenienceProduct(
                    product_id=item.get('productId', ''),
                    name=item.get('name', ''),
                    price=item.get('price', 0),
                    image_url=item.get('imgSrc', ''),
                    store=store,
                    event_type=item.get('eventType', ''),
                )
                products.append(product)

        except Exception as e:
            print(f"[에러] 파싱 실패: {e}")

        print(f"[정보] {store.upper()}에서 {len(products)}개 상품 발견")
        return products

    async def close(self):
        await self._close_browser()


class SevenElevenScraper:
    """세븐일레븐 스크래퍼"""

    BASE_URL = "https://www.7-eleven.co.kr"
    EVENT_URL = "https://www.7-eleven.co.kr/product/presentList.asp"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.page = await self.context.new_page()

    async def _close_browser(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except Exception:
            pass

    async def get_event_products(self, event_type: str = "1+1", limit: int = 30) -> List[ConvenienceProduct]:
        """행사 상품 수집"""
        if not self.page:
            await self._init_browser()

        try:
            print(f"[세븐일레븐] 행사 상품 수집: {event_type}")
            await self.page.goto(self.EVENT_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            products = await self._parse_products("seveneleven", event_type, limit)
            return products

        except Exception as e:
            print(f"[에러] 세븐일레븐 행사 상품 수집 실패: {e}")
            return []

    async def _parse_products(self, store: str, event_type: str, limit: int) -> List[ConvenienceProduct]:
        products = []

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];
                const items = document.querySelectorAll('.pic_product, .product_list li, ul.list_711 li');

                items.forEach((item, idx) => {
                    try {
                        const nameEl = item.querySelector('.name, .tit_product, .txt_product');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        const priceEl = item.querySelector('.price, .price_product');
                        let price = 0;
                        if (priceEl) {
                            price = parseInt(priceEl.textContent.replace(/[^0-9]/g, '')) || 0;
                        }

                        const img = item.querySelector('img');
                        let imgSrc = img ? (img.getAttribute('src') || '') : '';
                        if (imgSrc.startsWith('/')) imgSrc = 'https://www.7-eleven.co.kr' + imgSrc;

                        if (name) {
                            results.push({
                                productId: '711_' + idx,
                                name,
                                price,
                                imgSrc
                            });
                        }
                    } catch (e) {}
                });

                return results;
            }''')

            for item in product_data[:limit]:
                product = ConvenienceProduct(
                    product_id=item.get('productId', ''),
                    name=item.get('name', ''),
                    price=item.get('price', 0),
                    image_url=item.get('imgSrc', ''),
                    store=store,
                    event_type=event_type,
                )
                products.append(product)

        except Exception as e:
            print(f"[에러] 파싱 실패: {e}")

        print(f"[정보] 세븐일레븐에서 {len(products)}개 상품 발견")
        return products

    async def close(self):
        await self._close_browser()


class Emart24Scraper:
    """이마트24 스크래퍼"""

    BASE_URL = "https://emart24.co.kr"
    EVENT_URL = "https://emart24.co.kr/goods/event"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.page = await self.context.new_page()

    async def _close_browser(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except Exception:
            pass

    async def get_event_products(self, event_type: str = "1+1", limit: int = 30) -> List[ConvenienceProduct]:
        """행사 상품 수집"""
        if not self.page:
            await self._init_browser()

        try:
            print(f"[이마트24] 행사 상품 수집: {event_type}")

            # 행사 타입별 URL
            type_map = {"1+1": "ONE_TO_ONE", "2+1": "TWO_TO_ONE"}
            event_code = type_map.get(event_type, "ONE_TO_ONE")
            url = f"{self.EVENT_URL}?eventTypeCode={event_code}"

            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            products = await self._parse_products("emart24", event_type, limit)
            return products

        except Exception as e:
            print(f"[에러] 이마트24 행사 상품 수집 실패: {e}")
            return []

    async def _parse_products(self, store: str, event_type: str, limit: int) -> List[ConvenienceProduct]:
        products = []

        try:
            product_data = await self.page.evaluate('''() => {
                const results = [];
                const items = document.querySelectorAll('.itemWrap, .goods_list li, .product_item');

                items.forEach((item, idx) => {
                    try {
                        const nameEl = item.querySelector('.itemTitle, .goods_name, .name');
                        const name = nameEl ? nameEl.textContent.trim() : '';

                        const priceEl = item.querySelector('.itemPrice, .goods_price, .price');
                        let price = 0;
                        if (priceEl) {
                            price = parseInt(priceEl.textContent.replace(/[^0-9]/g, '')) || 0;
                        }

                        const img = item.querySelector('img');
                        let imgSrc = img ? (img.getAttribute('src') || '') : '';

                        if (name) {
                            results.push({
                                productId: 'EM24_' + idx,
                                name,
                                price,
                                imgSrc
                            });
                        }
                    } catch (e) {}
                });

                return results;
            }''')

            for item in product_data[:limit]:
                product = ConvenienceProduct(
                    product_id=item.get('productId', ''),
                    name=item.get('name', ''),
                    price=item.get('price', 0),
                    image_url=item.get('imgSrc', ''),
                    store=store,
                    event_type=event_type,
                )
                products.append(product)

        except Exception as e:
            print(f"[에러] 파싱 실패: {e}")

        print(f"[정보] 이마트24에서 {len(products)}개 상품 발견")
        return products

    async def close(self):
        await self._close_browser()


# 통합 클래스
class ConvenienceStoreScraper:
    """편의점 통합 스크래퍼"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.scrapers = {
            "cu": CUScraper,
            "gs25": GS25Scraper,
            "seveneleven": SevenElevenScraper,
            "emart24": Emart24Scraper,
        }

    async def get_all_event_products(self, limit_per_store: int = 20) -> Dict[str, List[ConvenienceProduct]]:
        """모든 편의점 행사 상품 수집"""
        results = {}

        for store_key, ScraperClass in self.scrapers.items():
            scraper = ScraperClass(headless=self.headless)
            try:
                products = await scraper.get_event_products(limit=limit_per_store)
                results[store_key] = products
            except Exception as e:
                print(f"[에러] {store_key} 수집 실패: {e}")
                results[store_key] = []
            finally:
                await scraper.close()

            await asyncio.sleep(2)  # 부하 방지

        return results


async def main():
    """테스트"""
    print("=== 편의점 스크래퍼 테스트 ===\n")

    # CU 테스트
    cu = CUScraper(headless=True)
    try:
        products = await cu.get_event_products("1+1", limit=5)
        print("\n[CU 1+1 상품]")
        for p in products:
            print(f"  - {p.name}: {p.price:,}원")
    finally:
        await cu.close()


if __name__ == "__main__":
    asyncio.run(main())
