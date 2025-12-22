# -*- coding: utf-8 -*-
"""
편의점 크롤러
CU, GS25, 세븐일레븐, 이마트24 상품 정보 수집
"""
import requests
from dataclasses import dataclass
from typing import Optional, List
import time
import re
import json


@dataclass
class ConvenienceProduct:
    """편의점 상품 정보"""
    product_code: str
    name: str
    price: int
    image_url: str
    product_url: str
    store: str  # cu, gs25, seven, emart24
    category: Optional[str]
    is_pb: bool  # PB상품 여부
    is_new: bool  # 신상품 여부
    is_event: bool  # 행사상품 여부
    event_type: Optional[str]  # 1+1, 2+1, 할인 등


class CUCrawler:
    """CU 편의점 크롤러"""

    BASE_URL = "https://cu.bgfretail.com"
    PRODUCT_API = "https://cu.bgfretail.com/product/productAjax.do"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://cu.bgfretail.com/product/pb.do",
        })

    def search(self, query: str = None, category: str = None, limit: int = 20) -> List[ConvenienceProduct]:
        """상품 검색"""
        try:
            params = {
                "pageIndex": 1,
                "searchKeyword": query or "",
                "listType": "1",
                "searchMainCategory": category or "",
                "searchSubCategory": "",
            }

            response = self.session.post(
                self.PRODUCT_API,
                data=params,
                timeout=15
            )

            if response.status_code != 200:
                return []

            return self._parse_response(response.json(), "cu")[:limit]

        except Exception as e:
            print(f"[!] CU 검색 오류: {e}")
            return []

    def _parse_response(self, data: dict, store: str) -> List[ConvenienceProduct]:
        """응답 파싱"""
        products = []

        try:
            items = data.get("productList", [])

            for item in items:
                products.append(ConvenienceProduct(
                    product_code=str(item.get("goodsCode", "")),
                    name=item.get("goodsNm", ""),
                    price=int(item.get("price", 0)),
                    image_url=item.get("imgUrl", ""),
                    product_url=f"{self.BASE_URL}/product/view.do?goodsCode={item.get('goodsCode', '')}",
                    store=store,
                    category=item.get("categoryNm"),
                    is_pb=item.get("pbYn", "N") == "Y",
                    is_new=item.get("newYn", "N") == "Y",
                    is_event=item.get("eventYn", "N") == "Y",
                    event_type=item.get("eventType"),
                ))

        except Exception as e:
            print(f"[!] CU 파싱 오류: {e}")

        return products

    def get_events(self, event_type: str = "1+1") -> List[ConvenienceProduct]:
        """행사 상품 조회 (1+1, 2+1)"""
        return self.search(category="event_" + event_type.replace("+", ""))


class GS25Crawler:
    """GS25 편의점 크롤러"""

    BASE_URL = "http://gs25.gsretail.com"
    SEARCH_URL = "http://gs25.gsretail.com/gscvs/ko/products/youus-freshfood"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        })

    def search(self, query: str = None, limit: int = 20) -> List[ConvenienceProduct]:
        """상품 검색"""
        try:
            params = {
                "CSRFToken": "",
                "searchKeyword": query or "",
                "pageNum": 1,
                "pageSize": limit,
            }

            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                timeout=15
            )

            if response.status_code != 200:
                return []

            return self._parse_html(response.text, "gs25")[:limit]

        except Exception as e:
            print(f"[!] GS25 검색 오류: {e}")
            return []

    def _parse_html(self, html: str, store: str) -> List[ConvenienceProduct]:
        """HTML 파싱"""
        products = []

        try:
            # 상품 블록 추출
            product_pattern = r'<div class="prod_box">(.*?)</div>\s*</li>'
            blocks = re.findall(product_pattern, html, re.DOTALL)

            for block in blocks[:20]:
                # 상품명
                name_match = re.search(r'<p class="tit"[^>]*>([^<]+)</p>', block)
                name = name_match.group(1).strip() if name_match else ""

                # 가격
                price_match = re.search(r'<span class="cost"[^>]*>([0-9,]+)원</span>', block)
                price_str = price_match.group(1) if price_match else "0"
                price = int(price_str.replace(",", ""))

                # 이미지
                img_match = re.search(r'<img[^>]*src="([^"]+)"', block)
                image_url = img_match.group(1) if img_match else ""

                # 행사 타입
                event_match = re.search(r'class="flag\s*([^"]*)"', block)
                event_type = event_match.group(1).strip() if event_match else None
                is_event = event_type is not None and event_type != ""

                if name and price > 0:
                    products.append(ConvenienceProduct(
                        product_code=f"gs_{hash(name) % 100000}",
                        name=name,
                        price=price,
                        image_url=image_url,
                        product_url=self.BASE_URL,
                        store=store,
                        category=None,
                        is_pb=False,
                        is_new=False,
                        is_event=is_event,
                        event_type=event_type,
                    ))

        except Exception as e:
            print(f"[!] GS25 파싱 오류: {e}")

        return products


class Emart24Crawler:
    """이마트24 크롤러"""

    BASE_URL = "https://www.emart24.co.kr"
    PRODUCT_API = "https://www.emart24.co.kr/api/products"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })

    def search(self, query: str = None, limit: int = 20) -> List[ConvenienceProduct]:
        """상품 검색"""
        try:
            params = {
                "keyword": query or "",
                "page": 1,
                "size": limit,
            }

            response = self.session.get(
                self.PRODUCT_API,
                params=params,
                timeout=15
            )

            if response.status_code != 200:
                return []

            return self._parse_response(response.json(), "emart24")[:limit]

        except Exception as e:
            print(f"[!] 이마트24 검색 오류: {e}")
            return []

    def _parse_response(self, data: dict, store: str) -> List[ConvenienceProduct]:
        """응답 파싱"""
        products = []

        try:
            items = data.get("data", {}).get("list", [])

            for item in items:
                products.append(ConvenienceProduct(
                    product_code=str(item.get("productCode", "")),
                    name=item.get("productName", ""),
                    price=int(item.get("price", 0)),
                    image_url=item.get("imageUrl", ""),
                    product_url=f"{self.BASE_URL}/product/{item.get('productCode', '')}",
                    store=store,
                    category=item.get("category"),
                    is_pb=item.get("isPb", False),
                    is_new=item.get("isNew", False),
                    is_event=item.get("isEvent", False),
                    event_type=item.get("eventType"),
                ))

        except Exception as e:
            print(f"[!] 이마트24 파싱 오류: {e}")

        return products


class ConvenienceCrawler:
    """통합 편의점 크롤러"""

    def __init__(self):
        self.crawlers = {
            "cu": CUCrawler(),
            "gs25": GS25Crawler(),
            "emart24": Emart24Crawler(),
        }

    def search_all(self, query: str, limit_per_store: int = 10) -> List[ConvenienceProduct]:
        """모든 편의점에서 검색"""
        all_products = []

        for store, crawler in self.crawlers.items():
            try:
                products = crawler.search(query, limit=limit_per_store)
                all_products.extend(products)
                time.sleep(0.5)
            except Exception as e:
                print(f"[!] {store} 검색 실패: {e}")

        return all_products

    def search(self, query: str, store: str = None, limit: int = 20) -> List[ConvenienceProduct]:
        """특정 편의점 또는 전체 검색"""
        if store and store in self.crawlers:
            return self.crawlers[store].search(query, limit=limit)
        return self.search_all(query, limit_per_store=limit // 3)

    def search_and_match(self, product_name: str, store: str = None) -> Optional[ConvenienceProduct]:
        """상품 검색 후 매칭"""
        results = self.search(product_name, store=store, limit=10)

        if not results:
            return None

        # 가장 유사한 상품 찾기
        search_terms = product_name.lower().split()
        best_match = None
        best_score = 0

        for product in results:
            product_lower = product.name.lower()
            score = sum(1 for term in search_terms if term in product_lower)
            normalized_score = score / len(search_terms) if search_terms else 0

            if normalized_score > best_score:
                best_score = normalized_score
                best_match = product

        return best_match if best_score >= 0.3 else (results[0] if results else None)

    def get_events(self, store: str = None, event_type: str = "1+1") -> List[ConvenienceProduct]:
        """행사 상품 조회"""
        if store == "cu" and "cu" in self.crawlers:
            return self.crawlers["cu"].get_events(event_type)
        return []


def test_convenience():
    """편의점 크롤러 테스트"""
    crawler = ConvenienceCrawler()

    print("=== 편의점 크롤러 테스트 ===\n")

    test_keywords = ["삼각김밥", "컵라면", "아이스크림"]

    for keyword in test_keywords:
        print(f"검색어: {keyword}")
        print("-" * 40)

        result = crawler.search_and_match(keyword)
        if result:
            print(f"매장: {result.store.upper()}")
            print(f"상품명: {result.name}")
            print(f"가격: {result.price:,}원")
            if result.is_event:
                print(f"행사: {result.event_type or 'O'}")
        else:
            print("검색 결과 없음")
        print()

        time.sleep(1)


if __name__ == "__main__":
    test_convenience()
