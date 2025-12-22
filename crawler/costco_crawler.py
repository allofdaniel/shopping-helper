# -*- coding: utf-8 -*-
"""
코스트코 코리아 크롤러
costco.co.kr API를 통해 상품 정보를 수집합니다.
"""
import requests
import time
from typing import Optional
from dataclasses import dataclass


@dataclass
class CostcoProduct:
    """코스트코 상품 정보"""
    product_code: str
    name: str
    english_name: str
    price: int
    base_price: int
    discount_price: int
    image_url: str
    product_url: str
    category: str
    rating: float
    review_count: int
    in_stock: bool
    is_online_only: bool
    is_warehouse_only: bool

    def to_dict(self) -> dict:
        return {
            "product_no": self.product_code,
            "name": self.name,
            "english_name": self.english_name,
            "price": self.price,
            "base_price": self.base_price,
            "discount_price": self.discount_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "rating": self.rating,
            "review_count": self.review_count,
            "in_stock": self.in_stock,
            "is_online_only": self.is_online_only,
            "is_warehouse_only": self.is_warehouse_only,
        }


class CostcoCrawler:
    """코스트코 코리아 크롤러"""

    BASE_URL = "https://www.costco.co.kr"
    API_URL = "https://www.costco.co.kr/rest/v2/korea/products/search"

    # 주요 카테고리
    CATEGORIES = {
        "cos_10": "식품",
        "cos_10.1": "신선식품",
        "cos_10.2": "냉장/냉동식품",
        "cos_10.3": "유제품/음료",
        "cos_10.4": "가공식품",
        "cos_11": "생활용품/세제",
        "cos_12": "가전/TV/전자",
        "cos_13": "의류/잡화",
        "cos_14": "가구/생활가전",
        "cos_15": "유아용품",
        "cos_16": "뷰티/헬스",
        "cos_17": "사무/문구",
        "cos_18": "스포츠/레저",
        "cos_whsonly": "창고전용",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://www.costco.co.kr/",
        })

    def search_products(self, query: str, max_results: int = 50) -> list:
        """상품 검색"""
        products = []
        page = 0
        page_size = 20

        while len(products) < max_results:
            try:
                params = {
                    "query": query,
                    "currentPage": page,
                    "pageSize": page_size,
                    "sort": "relevance",
                }

                response = self.session.get(self.API_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                items = data.get("products", [])
                if not items:
                    break

                for item in items:
                    product = self._parse_product(item)
                    if product:
                        products.append(product)

                    if len(products) >= max_results:
                        break

                # 다음 페이지 체크
                pagination = data.get("pagination", {})
                total_pages = pagination.get("totalPages", 1)
                if page >= total_pages - 1:
                    break

                page += 1
                time.sleep(0.3)  # Rate limiting

            except Exception as e:
                print(f"검색 오류 ({query}): {e}")
                break

        return products

    def get_category_products(self, category_code: str, max_results: int = 100) -> list:
        """카테고리별 상품 조회"""
        products = []
        page = 0
        page_size = 20

        category_url = f"{self.BASE_URL}/rest/v2/korea/products/search"

        while len(products) < max_results:
            try:
                params = {
                    "query": f":relevance:allCategories:{category_code}",
                    "currentPage": page,
                    "pageSize": page_size,
                }

                response = self.session.get(category_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                items = data.get("products", [])
                if not items:
                    break

                for item in items:
                    product = self._parse_product(item)
                    if product:
                        product.category = self.CATEGORIES.get(category_code, category_code)
                        products.append(product)

                    if len(products) >= max_results:
                        break

                pagination = data.get("pagination", {})
                total_pages = pagination.get("totalPages", 1)
                if page >= total_pages - 1:
                    break

                page += 1
                time.sleep(0.3)

            except Exception as e:
                print(f"카테고리 조회 오류 ({category_code}): {e}")
                break

        return products

    def _parse_product(self, item: dict) -> Optional[CostcoProduct]:
        """API 응답 파싱"""
        try:
            code = item.get("code", "")
            name = item.get("name", "")

            if not code or not name:
                return None

            # 가격 정보
            price_data = item.get("price", {})
            price = int(price_data.get("value", 0))

            base_price_data = item.get("basePrice", {})
            base_price = int(base_price_data.get("value", 0)) if base_price_data else price

            discount = item.get("couponDiscount", {})
            discount_price = int(discount.get("value", 0)) if discount else 0

            # 이미지
            images = item.get("images", [])
            image_url = ""
            if images:
                for img in images:
                    if img.get("format") == "product":
                        image_url = img.get("url", "")
                        if not image_url.startswith("http"):
                            image_url = self.BASE_URL + image_url
                        break

            # 재고 상태
            stock = item.get("stock", {})
            in_stock = stock.get("stockLevelStatus", "") == "inStock"

            # 온라인/창고 전용
            is_online_only = item.get("onlineOnly", False)
            is_warehouse_only = item.get("warehouseOnly", False)

            # 평점
            rating = float(item.get("averageRating", 0))
            review_count = int(item.get("numberOfReviews", 0))

            # 상품 URL
            product_url = f"{self.BASE_URL}/p/{code}"

            # 카테고리
            categories = item.get("categories", [])
            category = ""
            if categories:
                category = categories[0].get("name", "")

            return CostcoProduct(
                product_code=code,
                name=name,
                english_name=item.get("englishName", ""),
                price=price,
                base_price=base_price,
                discount_price=discount_price,
                image_url=image_url,
                product_url=product_url,
                category=category,
                rating=rating,
                review_count=review_count,
                in_stock=in_stock,
                is_online_only=is_online_only,
                is_warehouse_only=is_warehouse_only,
            )

        except Exception as e:
            print(f"상품 파싱 오류: {e}")
            return None

    def search_and_match(self, query: str, threshold: float = 0.4) -> Optional[CostcoProduct]:
        """검색 및 최적 매칭"""
        products = self.search_products(query, max_results=10)

        if not products:
            return None

        query_lower = query.lower()
        best_match = None
        best_score = 0

        for product in products:
            name_lower = product.name.lower()

            # 단어 매칭 점수
            query_words = set(query_lower.split())
            name_words = set(name_lower.split())

            if query_words and name_words:
                intersection = query_words & name_words
                union = query_words | name_words
                score = len(intersection) / len(union)
            else:
                score = 0

            # 부분 문자열 보너스
            if query_lower in name_lower:
                score += 0.3

            if score > best_score and score >= threshold:
                best_score = score
                best_match = product

        return best_match

    def build_catalog(self, max_per_category: int = 50) -> list:
        """전체 카탈로그 구축"""
        all_products = []
        seen_codes = set()

        print("코스트코 카탈로그 구축 시작...")

        for cat_code, cat_name in self.CATEGORIES.items():
            print(f"  {cat_name} 수집 중...")

            products = self.get_category_products(cat_code, max_per_category)

            for product in products:
                if product.product_code not in seen_codes:
                    all_products.append(product)
                    seen_codes.add(product.product_code)

            print(f"    -> {len(products)}개 수집")
            time.sleep(0.5)

        print(f"총 {len(all_products)}개 상품 수집 완료")
        return all_products


def main():
    """테스트"""
    crawler = CostcoCrawler()

    # 검색 테스트
    print("=== 코스트코 검색 테스트 ===\n")

    keywords = ["치즈", "세제", "견과류", "커피"]

    for keyword in keywords:
        print(f"검색: {keyword}")
        products = crawler.search_products(keyword, max_results=5)

        for p in products:
            print(f"  - {p.name}")
            print(f"    가격: {p.price:,}원")
            if p.base_price > p.price:
                print(f"    정가: {p.base_price:,}원 (할인중)")
            print()

    # 매칭 테스트
    print("\n=== 상품 매칭 테스트 ===\n")
    test_queries = ["커클랜드 견과류", "코스트코 치즈케이크", "티슈"]

    for query in test_queries:
        match = crawler.search_and_match(query)
        if match:
            print(f"'{query}' -> {match.name} ({match.price:,}원)")
        else:
            print(f"'{query}' -> 매칭 실패")


if __name__ == "__main__":
    main()
