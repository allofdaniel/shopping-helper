# -*- coding: utf-8 -*-
"""
쿠팡 크롤러
쿠팡 상품 검색 및 가격 비교
"""
import requests
from dataclasses import dataclass
from typing import Optional, List
import time
import re
import json


@dataclass
class CoupangProduct:
    """쿠팡 상품 정보"""
    product_code: str
    name: str
    price: int
    original_price: Optional[int]
    discount_rate: Optional[int]
    image_url: str
    product_url: str
    brand: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    is_rocket: bool  # 로켓배송 여부
    is_fresh: bool   # 로켓프레시 여부
    seller: Optional[str]


class CoupangCrawler:
    """쿠팡 크롤러"""

    BASE_URL = "https://www.coupang.com"
    SEARCH_URL = "https://www.coupang.com/np/search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })

    def search(self, query: str, limit: int = 20) -> List[CoupangProduct]:
        """상품 검색"""
        try:
            params = {
                "q": query,
                "channel": "user",
                "component": "194176",
                "eventCategory": "SRP",
                "sorter": "scoreDesc",  # 관련도순
                "listSize": limit,
                "page": 1,
            }

            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                timeout=15
            )

            if response.status_code != 200:
                print(f"[!] 쿠팡 검색 실패: HTTP {response.status_code}")
                return []

            products = self._parse_search_html(response.text)
            return products[:limit]

        except Exception as e:
            print(f"[!] 쿠팡 검색 오류: {e}")
            return []

    def _parse_search_html(self, html: str) -> List[CoupangProduct]:
        """검색 결과 HTML 파싱"""
        products = []

        try:
            # 상품 블록 패턴
            # 쿠팡 HTML에서 상품 정보 추출
            product_blocks = re.findall(
                r'<li[^>]*class="search-product[^"]*"[^>]*data-product-id="(\d+)"[^>]*>(.*?)</li>',
                html, re.DOTALL
            )

            for product_id, block in product_blocks[:20]:
                # 상품명
                name_match = re.search(
                    r'class="name"[^>]*>([^<]+)</div>',
                    block
                )
                name = name_match.group(1).strip() if name_match else ""

                # 가격
                price_match = re.search(
                    r'class="price-value"[^>]*>([0-9,]+)</strong>',
                    block
                )
                price_str = price_match.group(1) if price_match else "0"
                price = int(price_str.replace(",", ""))

                # 원가
                original_match = re.search(
                    r'class="base-price"[^>]*>([0-9,]+)</del>',
                    block
                )
                original_price = None
                if original_match:
                    original_price = int(original_match.group(1).replace(",", ""))

                # 할인율
                discount_match = re.search(r'class="discount-rate"[^>]*>(\d+)%</span>', block)
                discount_rate = int(discount_match.group(1)) if discount_match else None

                # 이미지
                img_match = re.search(r'<img[^>]*src="(//[^"]+)"', block)
                image_url = "https:" + img_match.group(1) if img_match else ""

                # 로켓배송
                is_rocket = "rocket" in block.lower() or "로켓배송" in block

                # 로켓프레시
                is_fresh = "fresh" in block.lower() or "로켓프레시" in block

                # 평점
                rating_match = re.search(r'class="rating"[^>]*>([0-9.]+)</em>', block)
                rating = float(rating_match.group(1)) if rating_match else None

                # 리뷰 수
                review_match = re.search(r'\(([0-9,]+)\)', block)
                review_count = None
                if review_match:
                    review_count = int(review_match.group(1).replace(",", ""))

                if name and price > 0:
                    products.append(CoupangProduct(
                        product_code=product_id,
                        name=name,
                        price=price,
                        original_price=original_price,
                        discount_rate=discount_rate,
                        image_url=image_url,
                        product_url=f"https://www.coupang.com/vp/products/{product_id}",
                        brand=None,
                        rating=rating,
                        review_count=review_count,
                        is_rocket=is_rocket,
                        is_fresh=is_fresh,
                        seller=None,
                    ))

        except Exception as e:
            print(f"[!] 쿠팡 파싱 오류: {e}")

        return products

    def search_and_match(self, product_name: str, threshold: float = 0.4) -> Optional[CoupangProduct]:
        """상품 검색 후 가장 유사한 상품 반환"""
        results = self.search(product_name, limit=10)

        if not results:
            return None

        # 가장 유사한 상품 찾기
        best_match = None
        best_score = 0

        search_terms = product_name.lower().split()

        for product in results:
            product_lower = product.name.lower()
            score = sum(1 for term in search_terms if term in product_lower)
            normalized_score = score / len(search_terms) if search_terms else 0

            # 로켓배송 상품 가산점
            if product.is_rocket:
                normalized_score += 0.1

            if normalized_score > best_score:
                best_score = normalized_score
                best_match = product

        if best_score >= threshold:
            return best_match

        return results[0] if results else None

    def compare_price(self, product_name: str, store_price: int) -> Optional[dict]:
        """다른 스토어 가격과 쿠팡 가격 비교"""
        coupang_product = self.search_and_match(product_name)

        if not coupang_product:
            return None

        diff = store_price - coupang_product.price
        diff_percent = (diff / store_price * 100) if store_price > 0 else 0

        return {
            "coupang_product": coupang_product,
            "store_price": store_price,
            "coupang_price": coupang_product.price,
            "price_diff": diff,
            "diff_percent": round(diff_percent, 1),
            "cheaper_at": "coupang" if diff > 0 else "store" if diff < 0 else "same",
        }


def test_coupang():
    """쿠팡 크롤러 테스트"""
    crawler = CoupangCrawler()

    test_keywords = ["스텐 배수구망", "커클랜드 견과류", "제주 삼다수"]

    for keyword in test_keywords:
        print(f"\n검색어: {keyword}")
        print("-" * 40)

        result = crawler.search_and_match(keyword)
        if result:
            print(f"상품명: {result.name}")
            print(f"가격: {result.price:,}원")
            print(f"로켓배송: {'O' if result.is_rocket else 'X'}")
            if result.rating:
                print(f"평점: {result.rating} ({result.review_count}개 리뷰)")
            print(f"URL: {result.product_url}")
        else:
            print("검색 결과 없음")

        time.sleep(1)


if __name__ == "__main__":
    test_coupang()
