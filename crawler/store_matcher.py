"""
꿀템장바구니 - 매장 상품 매칭
다이소몰, 이케아 등 온라인몰에서 상품 정보(품번, 공식 이미지)를 매칭합니다.
"""
import re
import time
from typing import Optional, List, TypedDict
import requests
from urllib.parse import quote
import json


class ProductMatch(TypedDict, total=False):
    """상품 매칭 결과 타입"""
    product_code: str
    name: str
    price: int
    image_url: str
    product_url: str
    category: str


class StoreMatcherBase:
    """매장 매칭 베이스 클래스"""

    def __init__(self) -> None:
        self.session: requests.Session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def search(self, product_name: str) -> List[ProductMatch]:
        """상품 검색 (서브클래스에서 구현)"""
        raise NotImplementedError

    def _delay(self, seconds: float = 1.0) -> None:
        """요청 간격 준수 (차단 방지)"""
        time.sleep(seconds)


class DaisoMatcher(StoreMatcherBase):
    """다이소몰 상품 매칭"""

    def __init__(self) -> None:
        super().__init__()
        self.base_url: str = "https://www.daisomall.co.kr"
        self.search_url: str = "https://www.daisomall.co.kr/api/product/search"

    def search(self, product_name: str, max_results: int = 5) -> List[ProductMatch]:
        """
        다이소몰에서 상품 검색

        Returns:
            [
                {
                    "product_code": "품번",
                    "name": "공식 상품명",
                    "price": 가격,
                    "image_url": "공식 이미지 URL",
                    "product_url": "상품 상세 페이지 URL",
                    "category": "카테고리"
                },
                ...
            ]
        """
        try:
            # 방법 1: 공개 검색 페이지 크롤링
            search_page_url = f"{self.base_url}/search?keyword={quote(product_name)}"

            response = self.session.get(search_page_url, timeout=10)
            if response.status_code != 200:
                return []

            # HTML에서 상품 정보 추출 (간이 파싱)
            # 실제 구현 시 BeautifulSoup 사용 권장
            products = self._parse_search_results(response.text, product_name)

            self._delay(1.0)  # 요청 간격
            return products[:max_results]

        except Exception as e:
            print(f"  [!] 다이소몰 검색 오류: {e}")
            return []

    def _parse_search_results(self, html: str, query: str) -> list:
        """
        검색 결과 HTML 파싱
        NOTE: 다이소몰 구조 변경 시 업데이트 필요
        """
        products = []

        # 간이 정규식 파싱 (실제로는 BeautifulSoup 권장)
        # 상품 코드 패턴: data-product-code="12345678"
        code_pattern = r'data-product-code="(\d+)"'
        # 상품명 패턴
        name_pattern = r'class="product-name[^"]*"[^>]*>([^<]+)<'
        # 가격 패턴
        price_pattern = r'class="price[^"]*"[^>]*>(\d[\d,]*)'
        # 이미지 패턴
        img_pattern = r'<img[^>]+src="([^"]+)"[^>]*class="[^"]*product'

        codes = re.findall(code_pattern, html)
        names = re.findall(name_pattern, html)
        prices = re.findall(price_pattern, html)
        images = re.findall(img_pattern, html)

        # 매칭된 항목 조합
        for i in range(min(len(codes), len(names))):
            product = {
                "product_code": codes[i] if i < len(codes) else None,
                "name": names[i].strip() if i < len(names) else None,
                "price": int(prices[i].replace(",", "")) if i < len(prices) else None,
                "image_url": images[i] if i < len(images) else None,
                "product_url": f"{self.base_url}/product/{codes[i]}" if i < len(codes) else None,
                "category": None,
                "match_score": self._calculate_match_score(query, names[i] if i < len(names) else ""),
            }
            products.append(product)

        # 매칭 점수 순 정렬
        products.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return products

    def _calculate_match_score(self, query: str, name: str) -> float:
        """검색어와 상품명 매칭 점수 계산"""
        if not query or not name:
            return 0

        query = query.lower().strip()
        name = name.lower().strip()

        # 완전 일치
        if query == name:
            return 1.0

        # 포함 관계
        if query in name:
            return 0.8

        # 단어 단위 매칭
        query_words = set(query.split())
        name_words = set(name.split())
        common = query_words & name_words

        if not query_words:
            return 0

        return len(common) / len(query_words) * 0.6


class IkeaMatcher(StoreMatcherBase):
    """이케아 상품 매칭"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ikea.com/kr/ko"
        self.search_url = "https://sik.search.blue.cdtapps.com/kr/ko/search-result-page"

    def search(self, product_name: str, max_results: int = 5) -> list:
        """이케아에서 상품 검색"""
        try:
            params = {
                "q": product_name,
                "size": max_results,
            }

            response = self.session.get(self.search_url, params=params, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            products = []

            for item in data.get("searchResultPage", {}).get("products", {}).get("main", {}).get("items", []):
                product = item.get("product", {})
                products.append({
                    "product_code": product.get("id"),
                    "name": product.get("name"),
                    "price": product.get("salesPrice", {}).get("numeral"),
                    "image_url": product.get("mainImageUrl"),
                    "product_url": f"{self.base_url}/p/{product.get('pipUrl', '')}",
                    "category": product.get("typeName"),
                })

            self._delay(1.0)
            return products

        except Exception as e:
            print(f"  [!] 이케아 검색 오류: {e}")
            return []


class OliveyoungMatcher(StoreMatcherBase):
    """올리브영 상품 매칭"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.oliveyoung.co.kr"

    def search(self, product_name: str, max_results: int = 5) -> list:
        """올리브영에서 상품 검색"""
        try:
            search_url = f"{self.base_url}/store/search/getSearchMain.do"
            params = {
                "query": product_name,
                "giftYn": "N",
            }

            response = self.session.get(search_url, params=params, timeout=10)

            if response.status_code != 200:
                return []

            # HTML 파싱 (간이 버전)
            products = self._parse_oliveyoung_results(response.text)

            self._delay(1.0)
            return products[:max_results]

        except Exception as e:
            print(f"  [!] 올리브영 검색 오류: {e}")
            return []

    def _parse_oliveyoung_results(self, html: str) -> list:
        """올리브영 검색 결과 파싱"""
        products = []

        # 상품 코드 패턴
        code_pattern = r'data-ref-goodsno="(\d+)"'
        name_pattern = r'class="tx_name"[^>]*>([^<]+)<'
        price_pattern = r'class="tx_cur"[^>]*>.*?(\d[\d,]+)원'
        img_pattern = r'<img[^>]+data-original="([^"]+)"'

        codes = re.findall(code_pattern, html)
        names = re.findall(name_pattern, html)
        prices = re.findall(price_pattern, html)
        images = re.findall(img_pattern, html)

        for i in range(min(len(codes), len(names))):
            products.append({
                "product_code": codes[i] if i < len(codes) else None,
                "name": names[i].strip() if i < len(names) else None,
                "price": int(prices[i].replace(",", "")) if i < len(prices) else None,
                "image_url": images[i] if i < len(images) else None,
                "product_url": f"{self.base_url}/store/goods/getGoodsDetail.do?goodsNo={codes[i]}" if i < len(codes) else None,
                "category": None,
            })

        return products


class StoreMatcher:
    """통합 매장 매칭 클래스"""

    def __init__(self):
        self.matchers = {
            "daiso": DaisoMatcher(),
            "ikea": IkeaMatcher(),
            "oliveyoung": OliveyoungMatcher(),
        }

    def match_product(self, product_name: str, store_key: str) -> Optional[dict]:
        """
        상품명으로 매장에서 공식 상품 정보 매칭

        Returns:
            가장 일치도 높은 상품 정보 또는 None
        """
        if store_key not in self.matchers:
            print(f"  [!] 지원하지 않는 매장: {store_key}")
            return None

        matcher = self.matchers[store_key]
        results = matcher.search(product_name, max_results=1)

        if results:
            return results[0]
        return None

    def enrich_products(self, products: list, store_key: str) -> list:
        """
        AI 추출 상품 리스트에 공식 매장 정보 추가

        Args:
            products: AI로 추출한 상품 리스트
            store_key: 매장 키 (daiso, ikea 등)

        Returns:
            공식 정보가 추가된 상품 리스트
        """
        if store_key not in self.matchers:
            return products

        enriched = []
        for product in products:
            try:
                print(f"  Matching: {product['name']}", flush=True)
            except UnicodeEncodeError:
                print(f"  Matching: [product name]", flush=True)

            matched = self.match_product(product["name"], store_key)

            if matched:
                product["official"] = {
                    "product_code": matched.get("product_code"),
                    "official_name": matched.get("name"),
                    "official_price": matched.get("price"),
                    "image_url": matched.get("image_url"),
                    "product_url": matched.get("product_url"),
                    "matched": True,
                }
            else:
                product["official"] = {"matched": False}

            enriched.append(product)

        return enriched


def main():
    """테스트 실행"""
    matcher = StoreMatcher()

    test_products = [
        {"name": "스텐 배수구망", "store": "daiso"},
        {"name": "KALLAX 칼락스", "store": "ikea"},
        {"name": "라운드랩 독도 토너", "store": "oliveyoung"},
    ]

    print("=== 매장 상품 매칭 테스트 ===\n")

    for p in test_products:
        print(f"\n검색: {p['name']} ({p['store']})")
        result = matcher.match_product(p["name"], p["store"])

        if result:
            print(f"  품번: {result.get('product_code')}")
            print(f"  상품명: {result.get('name')}")
            print(f"  가격: {result.get('price')}원")
            print(f"  이미지: {result.get('image_url')}")
        else:
            print("  매칭 실패")


if __name__ == "__main__":
    main()
