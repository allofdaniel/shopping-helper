# -*- coding: utf-8 -*-
"""
상품 매칭 알고리즘
YouTube에서 추출한 상품명을 다이소몰 공식 품번과 매칭합니다.
"""
import re
from typing import Optional
from database import Database
from daiso_crawler import DaisoCrawler


class ProductMatcher:
    """YouTube 상품 -> 다이소몰 품번 매칭"""

    def __init__(self):
        self.db = Database()
        self.crawler = DaisoCrawler()

    def match_product(self, product_name: str, price: int = None,
                      category: str = None, keywords: list = None) -> Optional[dict]:
        """
        상품명으로 다이소몰 상품 매칭

        Args:
            product_name: YouTube에서 추출한 상품명
            price: 영상에서 언급된 가격 (있으면 매칭 정확도 향상)
            category: 상품 카테고리
            keywords: 검색 키워드 리스트

        Returns:
            매칭된 다이소몰 상품 정보 또는 None
        """
        # 1. DB 카탈로그에서 먼저 검색
        db_match = self._search_in_catalog(product_name, price, keywords)
        if db_match:
            return db_match

        # 2. DB에 없으면 다이소몰 API 직접 검색
        api_match = self._search_via_api(product_name, price, keywords)
        if api_match:
            # 검색 결과를 DB에 저장
            self.db.insert_daiso_product(api_match)
            return api_match

        return None

    def _search_in_catalog(self, product_name: str, price: int = None,
                           keywords: list = None) -> Optional[dict]:
        """로컬 DB 카탈로그에서 검색"""
        # 상품명 정제
        clean_name = self._clean_product_name(product_name)

        # DB 검색
        results = self.db.search_daiso_catalog(clean_name, limit=20)

        if not results:
            # 키워드로 재검색
            if keywords:
                for keyword in keywords[:3]:
                    results = self.db.search_daiso_catalog(keyword, limit=10)
                    if results:
                        break

        if not results:
            return None

        # 최적 매칭 선택
        best_match = self._find_best_match(results, clean_name, price)
        if best_match:
            return {
                "matched": True,
                "product_code": best_match["product_no"],
                "official_name": best_match["name"],
                "official_price": best_match["price"],
                "image_url": best_match["image_url"],
                "product_url": best_match["product_url"],
                "category": best_match["category"],
                "rating": best_match.get("rating", 0),
                "review_count": best_match.get("review_count", 0),
                "order_count": best_match.get("order_count", 0),
                "is_best": bool(best_match.get("is_best")),
                "match_source": "catalog",
            }

        return None

    def _search_via_api(self, product_name: str, price: int = None,
                        keywords: list = None) -> Optional[dict]:
        """다이소몰 API로 직접 검색"""
        clean_name = self._clean_product_name(product_name)

        # 검색어 생성 (상품명 또는 키워드)
        search_queries = [clean_name]
        if keywords:
            search_queries.extend(keywords[:2])

        for query in search_queries:
            result = self.crawler.search_and_match(query, threshold=0.4)
            if result:
                return result.to_dict()

        return None

    def _clean_product_name(self, name: str) -> str:
        """상품명 정제"""
        # 불필요한 문자 제거
        clean = re.sub(r'[^\w\s가-힣]', ' ', name)
        # 연속 공백 제거
        clean = re.sub(r'\s+', ' ', clean).strip()
        # 일반적인 수식어 제거
        stopwords = ['다이소', '진짜', '완전', '꿀템', '추천', '좋은', '최고']
        for word in stopwords:
            clean = clean.replace(word, '')
        return clean.strip()

    def _find_best_match(self, candidates: list, query: str,
                         target_price: int = None) -> Optional[dict]:
        """후보 중 최적 매칭 선택"""
        if not candidates:
            return None

        best_score = 0
        best_match = None

        query_lower = query.lower()
        query_words = set(query_lower.split())

        for candidate in candidates:
            score = 0
            candidate_name = candidate["name"].lower()
            candidate_words = set(candidate_name.split())

            # 1. 단어 겹침 점수 (Jaccard)
            if query_words and candidate_words:
                intersection = query_words & candidate_words
                union = query_words | candidate_words
                jaccard = len(intersection) / len(union)
                score += jaccard * 50

            # 2. 부분 문자열 포함
            if query_lower in candidate_name:
                score += 30
            elif any(word in candidate_name for word in query_words if len(word) >= 2):
                score += 15

            # 3. 가격 일치 보너스
            if target_price and candidate.get("price"):
                if candidate["price"] == target_price:
                    score += 20
                elif abs(candidate["price"] - target_price) <= 1000:
                    score += 10

            # 4. 인기도 보너스 (주문 수)
            order_count = candidate.get("order_count", 0)
            if order_count > 10000:
                score += 5
            elif order_count > 1000:
                score += 3

            # 5. 베스트 상품 보너스
            if candidate.get("is_best"):
                score += 5

            if score > best_score:
                best_score = score
                best_match = candidate

        # 최소 점수 기준
        if best_score >= 20:
            return best_match

        return None

    def match_products_batch(self, products: list) -> list:
        """여러 상품 일괄 매칭"""
        results = []

        for product in products:
            match = self.match_product(
                product_name=product.get("name", ""),
                price=product.get("price"),
                category=product.get("category"),
                keywords=product.get("keywords", [])
            )

            result = product.copy()
            if match:
                result["official"] = match
                result["is_matched"] = True
            else:
                result["official"] = None
                result["is_matched"] = False

            results.append(result)

        return results

    def close(self):
        """리소스 해제"""
        self.db.close()


def test_matcher():
    """테스트"""
    matcher = ProductMatcher()

    # 테스트 상품들
    test_products = [
        {"name": "스텐 배수구망", "price": 2000, "keywords": ["배수구", "스텐"]},
        {"name": "실리콘 주걱", "price": 3000, "keywords": ["주걱", "실리콘"]},
        {"name": "서랍 정리함", "price": 1000, "keywords": ["정리함", "서랍"]},
        {"name": "밀폐용기 세트", "price": 5000, "keywords": ["밀폐용기"]},
    ]

    print("=== 상품 매칭 테스트 ===\n")

    for product in test_products:
        print(f"검색: {product['name']} ({product.get('price', '?')}원)")

        match = matcher.match_product(
            product_name=product["name"],
            price=product.get("price"),
            keywords=product.get("keywords", [])
        )

        if match:
            print(f"  -> 매칭 성공!")
            code = match.get('product_code') or match.get('product_no', '')
            name = match.get('official_name') or match.get('name', '')
            price = match.get('official_price') or match.get('price', 0)
            print(f"     품번: {code}")
            print(f"     상품명: {name}")
            print(f"     가격: {price}원")
            if match.get("order_count"):
                print(f"     주문수: {match['order_count']:,}")
        else:
            print(f"  -> 매칭 실패")

        print()

    matcher.close()


if __name__ == "__main__":
    test_matcher()
