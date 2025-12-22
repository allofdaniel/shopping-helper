# -*- coding: utf-8 -*-
"""
트레이더스 크롤러
이마트 트레이더스 상품 검색 및 매칭
"""
import requests
from dataclasses import dataclass
from typing import Optional, List
import time
import re


@dataclass
class TradersProduct:
    """트레이더스 상품 정보"""
    product_code: str
    name: str
    price: int
    original_price: Optional[int]
    discount_rate: Optional[int]
    image_url: str
    product_url: str
    brand: Optional[str]
    category: Optional[str]
    unit_info: Optional[str]  # 용량/개수 정보


class TradersCrawler:
    """이마트 트레이더스 크롤러"""

    BASE_URL = "https://traders.ssg.com"
    SEARCH_API = "https://search.ssg.com/search.ssg"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://traders.ssg.com/",
        })

    def search(self, query: str, limit: int = 20) -> List[TradersProduct]:
        """상품 검색"""
        try:
            params = {
                "target": "all",
                "query": query,
                "count": limit,
                "page": 1,
                "sort": "best",  # 인기순
                "siteNo": "6005",  # 트레이더스 사이트 코드
            }

            response = self.session.get(
                self.SEARCH_API,
                params=params,
                timeout=15
            )

            if response.status_code != 200:
                print(f"[!] 트레이더스 검색 실패: HTTP {response.status_code}")
                return []

            # JSON 응답이 아닌 경우 HTML 파싱 필요
            products = self._parse_search_response(response.text, query)
            return products[:limit]

        except Exception as e:
            print(f"[!] 트레이더스 검색 오류: {e}")
            return []

    def _parse_search_response(self, html: str, query: str) -> List[TradersProduct]:
        """검색 결과 파싱 (SSG 검색 API 형식)"""
        products = []

        # SSG 검색은 JSON + HTML 혼합 응답을 보냄
        # 간단한 상품 정보 추출
        try:
            # 상품 코드 패턴
            product_pattern = r'data-item-id="(\d+)"'
            product_ids = re.findall(product_pattern, html)

            # 상품명 패턴
            name_pattern = r'class="tx_ko"[^>]*>([^<]+)</span>'
            names = re.findall(name_pattern, html)

            # 가격 패턴
            price_pattern = r'class="ssg_price"[^>]*>([0-9,]+)</em>'
            prices = re.findall(price_pattern, html)

            # 이미지 패턴
            img_pattern = r'data-src="(https://[^"]+\.jpg)"'
            images = re.findall(img_pattern, html)

            for i, product_id in enumerate(product_ids[:20]):
                name = names[i] if i < len(names) else f"상품 {product_id}"
                price_str = prices[i] if i < len(prices) else "0"
                price = int(price_str.replace(",", ""))
                image = images[i] if i < len(images) else ""

                products.append(TradersProduct(
                    product_code=product_id,
                    name=name.strip(),
                    price=price,
                    original_price=None,
                    discount_rate=None,
                    image_url=image,
                    product_url=f"https://traders.ssg.com/item/itemView.ssg?itemId={product_id}",
                    brand=None,
                    category=None,
                    unit_info=None,
                ))

        except Exception as e:
            print(f"[!] 트레이더스 파싱 오류: {e}")

        return products

    def search_and_match(self, product_name: str, threshold: float = 0.5) -> Optional[TradersProduct]:
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

            if normalized_score > best_score:
                best_score = normalized_score
                best_match = product

        if best_score >= threshold:
            return best_match

        # 점수가 낮아도 첫 번째 결과 반환 (검색 결과가 있으면)
        return results[0] if results else None

    def get_product_detail(self, product_code: str) -> Optional[dict]:
        """상품 상세 정보 조회"""
        try:
            url = f"https://traders.ssg.com/item/itemView.ssg?itemId={product_code}"
            response = self.session.get(url, timeout=15)

            if response.status_code != 200:
                return None

            # 상세 페이지에서 추가 정보 추출
            html = response.text

            # 브랜드 추출
            brand_match = re.search(r'<a[^>]*class="brand"[^>]*>([^<]+)</a>', html)
            brand = brand_match.group(1).strip() if brand_match else None

            # 카테고리 추출
            cat_match = re.search(r'<li class="on"[^>]*>.*?<a[^>]*>([^<]+)</a>', html, re.DOTALL)
            category = cat_match.group(1).strip() if cat_match else None

            return {
                "brand": brand,
                "category": category,
                "product_code": product_code,
            }

        except Exception as e:
            print(f"[!] 트레이더스 상세 조회 오류: {e}")
            return None


def test_traders():
    """트레이더스 크롤러 테스트"""
    crawler = TradersCrawler()

    test_keywords = ["김치", "커피", "세탁세제"]

    for keyword in test_keywords:
        print(f"\n검색어: {keyword}")
        print("-" * 40)

        result = crawler.search_and_match(keyword)
        if result:
            print(f"상품명: {result.name}")
            print(f"가격: {result.price:,}원")
            print(f"URL: {result.product_url}")
        else:
            print("검색 결과 없음")

        time.sleep(1)


if __name__ == "__main__":
    test_traders()
