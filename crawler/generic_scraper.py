# -*- coding: utf-8 -*-
"""
통합 스크래퍼 (GenericScraper)
- 설정 기반으로 다양한 스토어 지원
- base_scraper.py의 BaseScraper 상속
- 코드 중복 최소화
"""
import re
import asyncio
import urllib.parse
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from base_scraper import BaseScraper, ScraperConfig
from scraper_configs import StoreConfig, StoreSelectors, get_store_config, STORE_CONFIGS


@dataclass
class Product:
    """통합 상품 모델"""
    product_id: str
    name: str
    store: str  # 스토어 코드
    price: int = 0
    original_price: int = 0
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    brand: str = ""
    rating: float = 0.0
    review_count: int = 0

    # 확장 필드 (스토어별 특수 정보)
    type_name: str = ""  # 이케아 상품 타입
    unit_price: str = ""  # 코스트코 단가
    color: str = ""
    size: str = ""
    event_type: str = ""  # 1+1, 2+1 등
    is_best: bool = False
    is_sale: bool = False
    is_new: bool = False
    is_pb: bool = False  # PB 상품

    # 메타데이터
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        result = {
            "product_id": self.product_id,
            "name": self.name,
            "store": self.store,
            "price": self.price,
            "original_price": self.original_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "brand": self.brand,
            "rating": self.rating,
            "review_count": self.review_count,
        }

        # 값이 있는 확장 필드만 포함
        if self.type_name:
            result["type_name"] = self.type_name
        if self.unit_price:
            result["unit_price"] = self.unit_price
        if self.event_type:
            result["event_type"] = self.event_type
        if self.is_best:
            result["is_best"] = self.is_best
        if self.is_sale:
            result["is_sale"] = self.is_sale
        if self.is_new:
            result["is_new"] = self.is_new
        if self.extra:
            result["extra"] = self.extra

        return result


class GenericScraper(BaseScraper[Product]):
    """
    설정 기반 통합 스크래퍼

    사용법:
        scraper = GenericScraper("costco")
        products = await scraper.search_products("노트북", limit=20)

        # 또는
        scraper = GenericScraper.from_config(COSTCO_CONFIG)
    """

    def __init__(
        self,
        store_code: str = None,
        store_config: StoreConfig = None,
        scraper_config: ScraperConfig = None
    ):
        """
        Args:
            store_code: 스토어 코드 (costco, ikea, oliveyoung 등)
            store_config: StoreConfig 객체 직접 전달
            scraper_config: ScraperConfig (브라우저 설정)
        """
        if store_config:
            self.store_config = store_config
        elif store_code:
            self.store_config = get_store_config(store_code)
            if not self.store_config:
                raise ValueError(f"Unknown store code: {store_code}")
        else:
            raise ValueError("store_code or store_config required")

        # BaseScraper 초기화
        super().__init__(scraper_config)
        self.store_name = self.store_config.code

    @classmethod
    def from_config(cls, store_config: StoreConfig, scraper_config: ScraperConfig = None):
        """StoreConfig에서 직접 생성"""
        return cls(store_config=store_config, scraper_config=scraper_config)

    async def search_products(self, query: str, limit: int = 20) -> List[Product]:
        """
        상품 검색

        Args:
            query: 검색어
            limit: 최대 결과 수

        Returns:
            상품 목록
        """
        if not self.page:
            await self._init_browser()

        try:
            # 메인 페이지 먼저 방문 필요시 (올리브영 등)
            if self.store_config.needs_main_page_first:
                self.logger.info(f"메인 페이지 접속: {self.store_config.base_url}")
                await self._goto_with_retry(f"{self.store_config.base_url}")
                await self._random_delay(2, 4)

            # 검색 URL 생성
            encoded_query = urllib.parse.quote(query)
            param = self.store_config.search_query_param
            search_url = f"{self.store_config.search_url}?{param}={encoded_query}"

            self.logger.info(f"검색: '{query}'")
            success = await self._goto_with_retry(search_url)
            if not success:
                return []

            # 추가 대기
            await asyncio.sleep(self.store_config.page_load_delay)

            # 쿠키 팝업 처리
            if self.store_config.selectors.cookie_popup:
                await self._handle_popup(self.store_config.selectors.cookie_popup)

            # 스크롤 필요시
            if self.store_config.requires_scroll:
                await self._scroll_page(times=self.store_config.scroll_times)

            # 파싱
            products = await self._parse_products(limit)
            return products

        except Exception as e:
            self.logger.error(f"검색 실패 ({query}): {e}")
            return []

    async def get_category_products(self, category_path: str, limit: int = 50) -> List[Product]:
        """
        카테고리 상품 수집

        Args:
            category_path: 카테고리 경로 또는 코드
            limit: 최대 결과 수
        """
        if not self.page:
            await self._init_browser()

        try:
            # 카테고리 URL 생성
            if category_path.startswith("http"):
                category_url = category_path
            elif self.store_config.category_url_pattern:
                category_url = self.store_config.category_url_pattern.replace("{code}", category_path)
            else:
                category_url = f"{self.store_config.base_url}/{category_path}"

            self.logger.info(f"카테고리 접속: {category_path}")
            success = await self._goto_with_retry(category_url)
            if not success:
                return []

            await asyncio.sleep(self.store_config.page_load_delay)

            # 쿠키 팝업 처리
            if self.store_config.selectors.cookie_popup:
                await self._handle_popup(self.store_config.selectors.cookie_popup)

            products = await self._parse_products(limit)
            return products

        except Exception as e:
            self.logger.error(f"카테고리 수집 실패 ({category_path}): {e}")
            return []

    async def get_event_products(self, event_type: str = "1+1", limit: int = 30) -> List[Product]:
        """
        이벤트 상품 수집 (편의점 등)

        Args:
            event_type: 이벤트 타입 (1+1, 2+1 등)
            limit: 최대 결과 수
        """
        if not self.store_config.is_event_store:
            self.logger.warning(f"{self.store_name}은 이벤트 스토어가 아닙니다")
            return []

        if not self.page:
            await self._init_browser()

        try:
            self.logger.info(f"이벤트 상품 수집: {event_type}")

            # 이벤트 타입별 URL 처리
            event_url = self.store_config.search_url
            if event_type == "2+1" and "emart24" in self.store_name:
                event_url += "?eventTypeCode=TWO_TO_ONE"
            elif event_type == "1+1" and "emart24" in self.store_name:
                event_url += "?eventTypeCode=ONE_TO_ONE"

            success = await self._goto_with_retry(event_url)
            if not success:
                return []

            await asyncio.sleep(self.store_config.page_load_delay)

            # 탭 선택 (CU 등)
            if event_type == "2+1":
                tab_selector = 'a[data-tab="2"], .tab_2plus1, #tab2'
                await self._handle_popup(tab_selector, action="click")
                await asyncio.sleep(2)

            products = await self._parse_products(limit)

            # 이벤트 타입 설정
            for p in products:
                p.event_type = event_type

            return products

        except Exception as e:
            self.logger.error(f"이벤트 상품 수집 실패: {e}")
            return []

    async def _parse_products(self, limit: int) -> List[Product]:
        """
        페이지에서 상품 파싱

        JavaScript로 DOM에서 데이터 추출
        """
        products = []
        selectors = self.store_config.selectors

        # 상품 목록 로딩 대기
        for selector in selectors.product_list:
            if await self._wait_for_selector_safe(selector, timeout=10000):
                break

        try:
            # JavaScript로 데이터 추출
            js_script = self._build_parse_script()
            product_data = await self._evaluate_safe(js_script, default=[])

            if not product_data:
                self.logger.warning("상품을 찾지 못함")
                # 봇 차단 확인
                content = await self.page.content()
                if "blocked" in content.lower() or "captcha" in content.lower():
                    self.logger.warning("봇 차단 또는 캡챠 감지됨")
                return []

            self.logger.info(f"{len(product_data)}개 상품 발견")

            # Product 객체 생성
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

                    product = Product(
                        product_id=product_id,
                        name=name,
                        store=self.store_name,
                        price=item.get('price', 0),
                        original_price=item.get('originalPrice', 0),
                        image_url=item.get('imageUrl', ''),
                        product_url=item.get('productUrl', ''),
                        brand=item.get('brand', ''),
                        rating=item.get('rating', 0),
                        review_count=item.get('reviewCount', 0),
                        type_name=item.get('typeName', ''),
                        event_type=item.get('eventType', ''),
                        is_best=item.get('isBest', False),
                        is_sale=item.get('isSale', False),
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception:
                    continue

        except Exception as e:
            self.logger.error(f"파싱 실패: {e}")

        return products

    def _build_parse_script(self) -> str:
        """상품 파싱용 JavaScript 생성"""
        s = self.store_config.selectors
        base_url = self.store_config.base_url

        # 셀렉터를 JSON 배열로 변환
        product_list_selectors = ', '.join(f"'{sel}'" for sel in s.product_list)
        name_selectors = ', '.join(f"'{sel}'" for sel in s.name) if s.name else "''"
        price_selectors = ', '.join(f"'{sel}'" for sel in s.price) if s.price else "''"
        orig_price_selectors = ', '.join(f"'{sel}'" for sel in s.original_price) if s.original_price else "''"
        link_selectors = ', '.join(f"'{sel}'" for sel in s.link) if s.link else "'a'"
        rating_selectors = ', '.join(f"'{sel}'" for sel in s.rating) if s.rating else "''"
        brand_selectors = ', '.join(f"'{sel}'" for sel in s.brand) if s.brand else "''"

        return f'''() => {{
            const results = [];
            const baseUrl = "{base_url}";
            const idPattern = "{s.id_pattern}";
            const idAttr = "{s.id_attribute}";

            // 유틸 함수
            function findElement(item, selectors) {{
                for (const sel of selectors) {{
                    const el = item.querySelector(sel);
                    if (el) return el;
                }}
                return null;
            }}

            function extractPrice(text) {{
                return parseInt((text || '').replace(/[^0-9]/g, '')) || 0;
            }}

            function extractId(item, link) {{
                // 속성에서 ID 추출
                if (idAttr) {{
                    const attrId = item.getAttribute(idAttr);
                    if (attrId) return attrId;
                }}

                // URL 패턴에서 ID 추출
                if (idPattern && link) {{
                    const href = link.getAttribute('href') || '';
                    const regex = new RegExp(idPattern);
                    const match = href.match(regex);
                    if (match) return match[1];
                }}

                return '';
            }}

            // 상품 목록 선택
            const productSelectors = [{product_list_selectors}];
            let items = [];
            for (const selector of productSelectors) {{
                items = document.querySelectorAll(selector);
                if (items.length > 0) break;
            }}

            items.forEach((item, idx) => {{
                try {{
                    const nameSelectors = [{name_selectors}];
                    const priceSelectors = [{price_selectors}];
                    const origPriceSelectors = [{orig_price_selectors}];
                    const linkSelectors = [{link_selectors}];
                    const ratingSelectors = [{rating_selectors}];
                    const brandSelectors = [{brand_selectors}];

                    // 이름
                    const nameEl = findElement(item, nameSelectors);
                    const name = nameEl ? nameEl.textContent.trim() : '';
                    if (!name) return;

                    // 링크
                    const linkEl = findElement(item, linkSelectors);

                    // ID 추출
                    let productId = extractId(item, linkEl);
                    if (!productId) productId = idx.toString();

                    // 가격
                    const priceEl = findElement(item, priceSelectors);
                    const price = priceEl ? extractPrice(priceEl.textContent) : 0;

                    const origPriceEl = findElement(item, origPriceSelectors);
                    const originalPrice = origPriceEl ? extractPrice(origPriceEl.textContent) : 0;

                    // 이미지
                    const img = item.querySelector('img');
                    let imageUrl = img ? (img.src || img.getAttribute('data-src') || '') : '';
                    if (imageUrl.startsWith('//')) imageUrl = 'https:' + imageUrl;

                    // 상품 URL
                    let productUrl = '';
                    if (linkEl) {{
                        productUrl = linkEl.getAttribute('href') || '';
                        if (productUrl.startsWith('/')) productUrl = baseUrl + productUrl;
                    }}

                    // 평점
                    const ratingEl = findElement(item, ratingSelectors);
                    let rating = 0;
                    if (ratingEl) {{
                        const ratingMatch = (ratingEl.textContent || '').match(/(\\d+\\.?\\d*)/);
                        if (ratingMatch) rating = parseFloat(ratingMatch[1]);
                    }}

                    // 브랜드
                    const brandEl = findElement(item, brandSelectors);
                    const brand = brandEl ? brandEl.textContent.trim() : '';

                    results.push({{
                        productId,
                        name,
                        price,
                        originalPrice,
                        imageUrl,
                        productUrl,
                        rating,
                        brand,
                        isSale: originalPrice > 0 && originalPrice > price
                    }});
                }} catch (e) {{}}
            }});

            return results;
        }}'''


# ============================================================
# 편의 함수
# ============================================================

async def search_store(store_code: str, query: str, limit: int = 20) -> List[Product]:
    """
    스토어에서 상품 검색 (간편 함수)

    Example:
        products = await search_store("costco", "노트북", limit=10)
    """
    async with GenericScraper(store_code) as scraper:
        return await scraper.search_products(query, limit)


async def search_all_stores(query: str, limit_per_store: int = 10) -> Dict[str, List[Product]]:
    """
    모든 스토어에서 상품 검색

    Example:
        results = await search_all_stores("선크림")
        for store, products in results.items():
            print(f"{store}: {len(products)}개")
    """
    results = {}
    non_event_stores = [code for code, cfg in STORE_CONFIGS.items() if not cfg.is_event_store]

    for store_code in non_event_stores:
        try:
            async with GenericScraper(store_code) as scraper:
                products = await scraper.search_products(query, limit_per_store)
                results[store_code] = products
        except Exception as e:
            print(f"[에러] {store_code} 검색 실패: {e}")
            results[store_code] = []

        await asyncio.sleep(2)  # 부하 방지

    return results


async def get_all_event_products(event_type: str = "1+1", limit_per_store: int = 20) -> Dict[str, List[Product]]:
    """
    모든 편의점 이벤트 상품 수집

    Example:
        events = await get_all_event_products("1+1")
    """
    results = {}
    event_stores = [code for code, cfg in STORE_CONFIGS.items() if cfg.is_event_store]

    for store_code in event_stores:
        try:
            async with GenericScraper(store_code) as scraper:
                products = await scraper.get_event_products(event_type, limit_per_store)
                results[store_code] = products
        except Exception as e:
            print(f"[에러] {store_code} 수집 실패: {e}")
            results[store_code] = []

        await asyncio.sleep(2)

    return results


# ============================================================
# 테스트
# ============================================================

async def main():
    """테스트"""
    print("=== GenericScraper 테스트 ===\n")

    # 1. 코스트코 검색 테스트
    print("[1] 코스트코 검색")
    async with GenericScraper("costco") as scraper:
        products = await scraper.search_products("노트북", limit=3)
        for p in products:
            print(f"  - {p.name}: {p.price:,}원")

    print()

    # 2. 이케아 검색 테스트
    print("[2] 이케아 검색")
    async with GenericScraper("ikea") as scraper:
        products = await scraper.search_products("책상", limit=3)
        for p in products:
            print(f"  - {p.name}: {p.price:,}원")

    print()

    # 3. 편의점 이벤트 테스트
    print("[3] CU 1+1 이벤트")
    async with GenericScraper("cu") as scraper:
        products = await scraper.get_event_products("1+1", limit=3)
        for p in products:
            print(f"  - {p.name}: {p.price:,}원 ({p.event_type})")


if __name__ == "__main__":
    asyncio.run(main())
