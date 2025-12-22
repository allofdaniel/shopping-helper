# -*- coding: utf-8 -*-
"""
이케아 코리아 크롤러
IKEA API를 통해 상품 정보를 수집합니다.
"""
import requests
import time
from typing import Optional
from dataclasses import dataclass


@dataclass
class IkeaProduct:
    """이케아 상품 정보"""
    product_code: str
    name: str
    type_name: str
    price: int
    image_url: str
    product_url: str
    category: str
    rating: float
    rating_count: int
    measurements: str
    color: str

    def to_dict(self) -> dict:
        return {
            "product_no": self.product_code,
            "name": self.name,
            "type_name": self.type_name,
            "price": self.price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "measurements": self.measurements,
            "color": self.color,
        }


class IkeaCrawler:
    """이케아 코리아 크롤러"""

    SEARCH_API = "https://sik.search.blue.cdtapps.com/kr/ko/search-result-page"
    BASE_URL = "https://www.ikea.com/kr/ko"

    # 인기 카테고리
    CATEGORIES = {
        "furniture": "가구",
        "beds": "침대",
        "sofas": "소파",
        "storage": "수납/정리",
        "tables": "테이블",
        "chairs": "의자",
        "lighting": "조명",
        "textiles": "텍스타일",
        "decoration": "장식",
        "kitchen": "주방",
        "bathroom": "욕실",
        "outdoor": "야외가구",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "ko-KR,ko;q=0.9",
        })

    def search_products(self, query: str, max_results: int = 50) -> list:
        """상품 검색"""
        products = []

        try:
            params = {
                "q": query,
                "size": min(max_results, 100),
                "subcategories-style": "tree-navigation",
                "sort": "RELEVANCE",
            }

            response = self.session.get(self.SEARCH_API, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            items = data.get("searchResultPage", {}).get("products", {}).get("main", {}).get("items", [])

            for item in items[:max_results]:
                product = self._parse_product(item.get("product", {}))
                if product:
                    products.append(product)

        except Exception as e:
            print(f"이케아 검색 오류 ({query}): {e}")

        return products

    def _parse_product(self, item: dict) -> Optional[IkeaProduct]:
        """상품 데이터 파싱"""
        try:
            # 기본 정보
            name = item.get("name", "")
            type_name = item.get("typeName", "")
            product_code = item.get("itemNoGlobal", "") or item.get("id", "")

            if not name or not product_code:
                return None

            # 가격
            price_info = item.get("salesPrice", {})
            price = int(price_info.get("numeral", 0))

            # 이미지
            main_image = item.get("mainImageUrl", "")

            # URL
            pip_url = item.get("pipUrl", "")
            product_url = pip_url if pip_url.startswith("http") else f"{self.BASE_URL}{pip_url}"

            # 카테고리
            category_path = item.get("categoryPath", [])
            category = category_path[0].get("name", "") if category_path else ""

            # 평점
            rating_info = item.get("ratingValue", 0)
            rating_count = item.get("ratingCount", 0)

            # 측정
            measurements = item.get("itemMeasureReferenceText", "")

            # 색상
            colors = item.get("colors", [])
            color = colors[0].get("name", "") if colors else ""

            return IkeaProduct(
                product_code=product_code,
                name=name,
                type_name=type_name,
                price=price,
                image_url=main_image,
                product_url=product_url,
                category=category,
                rating=float(rating_info) if rating_info else 0.0,
                rating_count=int(rating_count) if rating_count else 0,
                measurements=measurements,
                color=color,
            )

        except Exception as e:
            print(f"이케아 상품 파싱 오류: {e}")
            return None

    def search_and_match(self, query: str, threshold: float = 0.3) -> Optional[IkeaProduct]:
        """검색 및 최적 매칭"""
        products = self.search_products(query, max_results=10)

        if not products:
            return None

        query_lower = query.lower()
        best_match = None
        best_score = 0

        for product in products:
            name_lower = product.name.lower()
            type_lower = product.type_name.lower()
            full_name = f"{name_lower} {type_lower}"

            # 단어 매칭 점수
            query_words = set(query_lower.split())
            name_words = set(full_name.split())

            if query_words and name_words:
                intersection = query_words & name_words
                union = query_words | name_words
                score = len(intersection) / len(union)
            else:
                score = 0

            # 부분 문자열 보너스
            if query_lower in full_name:
                score += 0.3

            if score > best_score and score >= threshold:
                best_score = score
                best_match = product

        return best_match

    def get_popular_products(self, category: str = None, max_results: int = 50) -> list:
        """인기 상품 조회"""
        query = category if category else "베스트"
        return self.search_products(query, max_results)


def main():
    """테스트"""
    crawler = IkeaCrawler()

    print("=== 이케아 검색 테스트 ===\n")

    keywords = ["책상", "의자", "수납장", "조명"]

    for keyword in keywords:
        print(f"검색: {keyword}")
        products = crawler.search_products(keyword, max_results=3)

        for p in products:
            print(f"  - {p.name} ({p.type_name})")
            print(f"    가격: {p.price:,}원")
            if p.measurements:
                print(f"    크기: {p.measurements}")
            print()

    # 매칭 테스트
    print("\n=== 상품 매칭 테스트 ===\n")
    test_queries = ["말름 서랍장", "칼락스 선반", "포엥 의자"]

    for query in test_queries:
        match = crawler.search_and_match(query)
        if match:
            print(f"'{query}' -> {match.name} {match.type_name} ({match.price:,}원)")
        else:
            print(f"'{query}' -> 매칭 실패")


if __name__ == "__main__":
    main()
