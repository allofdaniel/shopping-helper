# -*- coding: utf-8 -*-
"""
다이소몰 스크래퍼 (2024-2025 업데이트)
- 상품명으로 품번 검색
- 품번으로 상품 정보 조회
- 공식몰 URL 및 상세정보 추출

사이트 구조:
- 검색 URL: https://prdm.daisomall.co.kr/ms/msb/SCR_MSB_0011?selectPdList=검색어
- 상품 링크 형태: link "가격 원 상품명 품번: 품번"
"""
import re
import time
import json
import asyncio
import urllib.parse
from typing import Optional, List, Dict
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[!] Playwright 설치 필요: pip install playwright && playwright install chromium")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class DaisoProduct:
    """다이소 상품 정보"""
    product_no: str  # 품번
    name: str
    price: int
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    is_available: bool = True  # 온라인 판매 여부

    def to_dict(self) -> dict:
        return {
            "product_no": self.product_no,
            "name": self.name,
            "price": self.price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "is_available": self.is_available,
        }


class DaisoMallScraper:
    """다이소몰 스크래퍼 (Playwright 기반)"""

    BASE_URL = "https://prdm.daisomall.co.kr"
    SEARCH_URL = "https://prdm.daisomall.co.kr/ms/msb/SCR_MSB_0011"

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

    async def search_products(self, query: str, limit: int = 20) -> List[DaisoProduct]:
        """
        상품명 또는 품번으로 검색

        Args:
            query: 검색어 (상품명 또는 품번)
            limit: 최대 결과 수

        Returns:
            검색된 상품 목록
        """
        if not self.page:
            await self._init_browser()

        try:
            # URL 인코딩된 검색어로 직접 이동 (tab=tab2 추가 - 매장 상품 찾기 탭)
            encoded_query = urllib.parse.quote(query)
            search_url = f"{self.SEARCH_URL}?tab=tab2&selectPdList={encoded_query}"

            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # 검색 결과 로딩 대기 (JavaScript 렌더링 시간 필요)
            await asyncio.sleep(3)

            # 혹시 검색 결과가 없으면 검색창 직접 입력 시도
            links = await self.page.query_selector_all('a[href*="pdNo="]')
            if not links:
                # 검색창 찾아서 입력
                try:
                    search_input = await self.page.wait_for_selector(
                        'input[placeholder*="상품명"], input[placeholder*="품번"]',
                        timeout=5000
                    )
                    if search_input:
                        await search_input.fill(query)
                        await search_input.press('Enter')
                        await asyncio.sleep(3)
                except Exception:
                    pass  # 검색 팝업이 없는 경우 무시

            # 결과 파싱
            products = await self._parse_search_results(limit)
            return products

        except Exception as e:
            print(f"[에러] 검색 실패 ({query}): {e}")
            return []

    async def _parse_search_results(self, limit: int) -> List[DaisoProduct]:
        """검색 결과 파싱 (2025 업데이트) - JavaScript evaluate 방식"""
        products = []

        try:
            # JavaScript로 직접 모든 링크 정보 추출 (query_selector가 동작하지 않는 경우 대비)
            product_data = await self.page.evaluate('''() => {
                const results = [];
                const links = document.querySelectorAll('a[href*="pdNo="]');

                links.forEach(link => {
                    const href = link.getAttribute('href') || '';
                    const text = link.innerText || '';
                    const img = link.querySelector('img');
                    const imgSrc = img ? img.getAttribute('src') : '';

                    // pdNo 추출
                    const pdNoMatch = href.match(/pdNo=(\\d+)/);
                    if (pdNoMatch) {
                        results.push({
                            pdNo: pdNoMatch[1],
                            href: href,
                            text: text.trim(),
                            imgSrc: imgSrc || ''
                        });
                    }
                });

                return results;
            }''')

            if not product_data:
                print("[경고] JavaScript evaluate로도 상품을 찾지 못함")
                return products

            print(f"[정보] JavaScript evaluate로 {len(product_data)}개 링크 발견")

            seen_product_nos = set()
            for item in product_data:
                try:
                    product_no = item.get('pdNo', '')
                    text = item.get('text', '')
                    image_url = item.get('imgSrc', '')

                    if not product_no:
                        continue

                    # 중복 체크
                    if product_no in seen_product_nos:
                        continue

                    if not text or len(text.strip()) < 5:
                        continue

                    # 텍스트 파싱
                    # 형태: "2,000 원 실리콘용기(약250 ml) 품번: 1045439"
                    # 또는: "2,000\n원\n실리콘용기(약250 ml)\n품번: 1045439"
                    text = text.strip()

                    # 가격 추출 (맨 앞에 있는 숫자)
                    price = 0
                    price_match = re.search(r'^(\d{1,3}(?:,\d{3})*)', text.replace('\n', ' '))
                    if price_match:
                        price = int(price_match.group(1).replace(',', ''))

                    # 상품명 추출 (품번: 이전, 가격 이후)
                    name = ""
                    # "원" 이후, "품번:" 이전 부분 추출
                    name_match = re.search(r'원\s*(.+?)\s*품번:', text.replace('\n', ' '), re.DOTALL)
                    if name_match:
                        name = name_match.group(1).strip()

                    # name이 비어있으면 다른 방법 시도
                    if not name:
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        for line in lines:
                            # 숫자로 시작하지 않고, '원', '품번' 아닌 라인
                            if not re.match(r'^\d', line) and line != '원' and '품번' not in line:
                                name = line
                                break

                    if not name or not product_no:
                        continue

                    seen_product_nos.add(product_no)

                    product_url = f"https://prdm.daisomall.co.kr/pd/pdl/SCR_PDL_0001?pdNo={product_no}"

                    product = DaisoProduct(
                        product_no=product_no,
                        name=name,
                        price=price,
                        image_url=image_url,
                        product_url=product_url,
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[에러] 결과 파싱 실패: {e}")

        return products

    async def get_product_by_code(self, product_no: str) -> Optional[DaisoProduct]:
        """
        품번으로 상품 조회

        Args:
            product_no: 다이소 품번

        Returns:
            상품 정보 또는 None
        """
        products = await self.search_products(product_no, limit=1)

        if products:
            # 정확한 품번 매칭 확인
            for p in products:
                if p.product_no == product_no:
                    return p

        return None

    async def search_and_match(self, product_name: str, expected_price: int = None) -> Optional[DaisoProduct]:
        """
        상품명으로 검색하고 가장 적합한 결과 반환

        Args:
            product_name: 검색할 상품명
            expected_price: 예상 가격 (있으면 가격 매칭에 사용)

        Returns:
            가장 적합한 상품 또는 None
        """
        products = await self.search_products(product_name, limit=10)

        if not products:
            return None

        # 점수 기반 매칭
        best_match = None
        best_score = 0

        for product in products:
            score = self._calculate_match_score(product_name, product.name, expected_price, product.price)
            if score > best_score:
                best_score = score
                best_match = product

        # 최소 점수 임계값
        if best_score >= 30:
            return best_match

        return None

    def _calculate_match_score(self, query_name: str, result_name: str,
                                query_price: int = None, result_price: int = None) -> int:
        """매칭 점수 계산"""
        score = 0

        # 이름 정규화
        q_name = re.sub(r'[^\w\s]', '', query_name.lower())
        r_name = re.sub(r'[^\w\s]', '', result_name.lower())

        # 완전 일치
        if q_name == r_name:
            score += 100
        # 포함 관계
        elif q_name in r_name or r_name in q_name:
            score += 60
        else:
            # 단어 매칭
            q_words = set(q_name.split())
            r_words = set(r_name.split())
            common = q_words & r_words
            if common:
                score += len(common) * 15

        # 가격 매칭
        if query_price and result_price:
            if query_price == result_price:
                score += 30
            elif abs(query_price - result_price) <= 1000:
                score += 15

        return score

    async def batch_search(self, product_names: List[str], delay: float = 1.0) -> Dict[str, Optional[DaisoProduct]]:
        """
        여러 상품 일괄 검색

        Args:
            product_names: 검색할 상품명 목록
            delay: 검색 간 대기 시간 (초)

        Returns:
            {상품명: DaisoProduct 또는 None} 딕셔너리
        """
        results = {}

        if not self.page:
            await self._init_browser()

        for name in product_names:
            print(f"  검색 중: {name}")
            result = await self.search_and_match(name)
            results[name] = result

            if result:
                print(f"    -> 매칭: {result.name} (품번: {result.product_no})")
            else:
                print(f"    -> 매칭 실패")

            await asyncio.sleep(delay)

        return results

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


class DaisoMallScraperSync:
    """동기 버전 스크래퍼 (간단한 사용을 위해)"""

    def __init__(self, headless: bool = True):
        self.async_scraper = DaisoMallScraper(headless=headless)

    def search_products(self, query: str, limit: int = 20) -> List[DaisoProduct]:
        """상품 검색"""
        return asyncio.run(self._async_search(query, limit))

    async def _async_search(self, query: str, limit: int) -> List[DaisoProduct]:
        try:
            results = await self.async_scraper.search_products(query, limit)
            return results
        finally:
            await self.async_scraper.close()

    def get_product_by_code(self, product_no: str) -> Optional[DaisoProduct]:
        """품번으로 검색"""
        return asyncio.run(self._async_get_by_code(product_no))

    async def _async_get_by_code(self, product_no: str) -> Optional[DaisoProduct]:
        try:
            result = await self.async_scraper.get_product_by_code(product_no)
            return result
        finally:
            await self.async_scraper.close()

    def search_and_match(self, product_name: str, expected_price: int = None) -> Optional[DaisoProduct]:
        """상품명으로 검색 및 매칭"""
        return asyncio.run(self._async_match(product_name, expected_price))

    async def _async_match(self, product_name: str, expected_price: int = None) -> Optional[DaisoProduct]:
        try:
            result = await self.async_scraper.search_and_match(product_name, expected_price)
            return result
        finally:
            await self.async_scraper.close()


class DaisoMallAPIClient:
    """
    HTTP 기반 다이소몰 API 클라이언트
    Playwright 없이 동작 (httpx 사용)
    """

    BASE_URL = "https://prdm.daisomall.co.kr"
    SEARCH_API = "https://prdm.daisomall.co.kr/pd/api/products/search"

    def __init__(self):
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx가 설치되어 있지 않습니다: pip install httpx")

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://prdm.daisomall.co.kr/",
        }

    def search_products(self, query: str, limit: int = 20) -> List[DaisoProduct]:
        """
        상품 검색 (API 버전)

        주의: 실제 API 엔드포인트가 변경될 수 있음
        Playwright 버전 사용 권장
        """
        products = []

        try:
            # 다이소몰 검색 페이지를 파싱하는 대체 방법
            search_url = f"https://prdm.daisomall.co.kr/ms/msb/SCR_MSB_0011?selectPdList={query}"

            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(search_url, headers=self.headers)

                if response.status_code == 200:
                    # HTML에서 상품 정보 추출 시도
                    text = response.text

                    # 간단한 정규식 파싱 (정확도 낮음)
                    pattern = r'pdNo=(\d+).*?(\d{1,3}(?:,\d{3})*)\s*원.*?>([\w가-힣\s\(\)]+)</.*?품번:\s*\1'
                    matches = re.findall(pattern, text, re.DOTALL)

                    for match in matches[:limit]:
                        product_no = match[0]
                        price = int(match[1].replace(',', ''))
                        name = match[2].strip()

                        if name and product_no:
                            product = DaisoProduct(
                                product_no=product_no,
                                name=name,
                                price=price,
                                product_url=f"https://prdm.daisomall.co.kr/pd/pdl/SCR_PDL_0001?pdNo={product_no}",
                            )
                            products.append(product)

        except Exception as e:
            print(f"[에러] API 검색 실패: {e}")

        return products

    def get_product_by_code(self, product_no: str) -> Optional[DaisoProduct]:
        """품번으로 상품 조회"""
        products = self.search_products(product_no, limit=5)

        for p in products:
            if p.product_no == product_no:
                return p

        return None


def get_daiso_scraper(use_playwright: bool = True, headless: bool = True):
    """
    적절한 다이소 스크래퍼 반환

    Args:
        use_playwright: True면 Playwright 사용, False면 HTTP 사용
        headless: 브라우저 헤드리스 모드

    Returns:
        DaisoMallScraper 또는 DaisoMallAPIClient
    """
    if use_playwright and PLAYWRIGHT_AVAILABLE:
        return DaisoMallScraper(headless=headless)
    elif HTTPX_AVAILABLE:
        return DaisoMallAPIClient()
    else:
        raise RuntimeError("Playwright 또는 httpx가 필요합니다")


async def main():
    """테스트 실행"""
    print("=== 다이소몰 스크래퍼 테스트 ===\n")

    scraper = DaisoMallScraper(headless=True)

    try:
        # 테스트 1: 상품명 검색
        print("[테스트 1] 상품명 검색: '실리콘수세미'")
        products = await scraper.search_products("실리콘수세미", limit=5)
        for p in products:
            print(f"  - {p.name}: {p.price}원 (품번: {p.product_no})")

        print()

        # 테스트 2: 품번 검색
        print("[테스트 2] 품번 검색: '1045474'")
        product = await scraper.get_product_by_code("1045474")
        if product:
            print(f"  -> {product.name}: {product.price}원")
            print(f"  -> URL: {product.product_url}")
        else:
            print("  -> 상품을 찾을 수 없음")

        print()

        # 테스트 3: 매칭 검색
        print("[테스트 3] 매칭 검색: '에어프라이어 종이호일', 2000원")
        matched = await scraper.search_and_match("에어프라이어 종이호일", 2000)
        if matched:
            print(f"  -> 매칭 결과: {matched.name} (품번: {matched.product_no})")
        else:
            print("  -> 매칭 실패")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
