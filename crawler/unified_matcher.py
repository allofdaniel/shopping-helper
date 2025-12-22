# -*- coding: utf-8 -*-
"""
통합 상품 매처
모든 매장(다이소, 코스트코, 트레이더스, 이케아, 올리브영, 편의점, 쿠팡)을 지원하는 통합 매칭 모듈
"""
from typing import Optional
from config import STORE_CATEGORIES


class UnifiedMatcher:
    """모든 매장 통합 매처"""

    def __init__(self):
        self.matchers = {}
        self.coupang_crawler = None  # 가격 비교용
        self._init_matchers()

    def _init_matchers(self):
        """각 매장별 매처 초기화"""
        # 다이소
        try:
            from product_matcher import ProductMatcher
            self.matchers["daiso"] = ProductMatcher()
            print("[OK] 다이소 매처 로드됨")
        except Exception as e:
            print(f"[!] 다이소 매처 로드 실패: {e}")

        # 코스트코
        try:
            from costco_crawler import CostcoCrawler
            self.matchers["costco"] = CostcoCrawler()
            print("[OK] 코스트코 매처 로드됨")
        except Exception as e:
            print(f"[!] 코스트코 매처 로드 실패: {e}")

        # 트레이더스
        try:
            from traders_crawler import TradersCrawler
            self.matchers["traders"] = TradersCrawler()
            print("[OK] 트레이더스 매처 로드됨")
        except Exception as e:
            print(f"[!] 트레이더스 매처 로드 실패: {e}")

        # 이케아
        try:
            from ikea_crawler import IkeaCrawler
            self.matchers["ikea"] = IkeaCrawler()
            print("[OK] 이케아 매처 로드됨")
        except Exception as e:
            print(f"[!] 이케아 매처 로드 실패: {e}")

        # 올리브영 (Playwright 필요)
        try:
            from oliveyoung_crawler import OliveyoungCrawler, PLAYWRIGHT_AVAILABLE
            if PLAYWRIGHT_AVAILABLE:
                self.matchers["oliveyoung"] = OliveyoungCrawler(headless=True)
                print("[OK] 올리브영 매처 로드됨 (Playwright)")
            else:
                print("[!] 올리브영 매처 스킵 (Playwright 미설치)")
        except Exception as e:
            print(f"[!] 올리브영 매처 로드 실패: {e}")

        # 편의점
        try:
            from convenience_crawler import ConvenienceCrawler
            self.matchers["convenience"] = ConvenienceCrawler()
            print("[OK] 편의점 매처 로드됨")
        except Exception as e:
            print(f"[!] 편의점 매처 로드 실패: {e}")
            self.matchers["convenience"] = None

        # 쿠팡 (가격 비교용)
        try:
            from coupang_crawler import CoupangCrawler
            self.coupang_crawler = CoupangCrawler()
            self.matchers["coupang"] = self.coupang_crawler
            print("[OK] 쿠팡 크롤러 로드됨 (가격 비교)")
        except Exception as e:
            print(f"[!] 쿠팡 크롤러 로드 실패: {e}")

    def match_product(self, product_name: str, store_key: str,
                      price: int = None, keywords: list = None) -> Optional[dict]:
        """
        상품명으로 공식 매장 상품 매칭

        Args:
            product_name: 영상에서 추출한 상품명
            store_key: 매장 키 (daiso, costco, traders, ikea, oliveyoung, convenience, coupang)
            price: 언급된 가격 (선택)
            keywords: 검색 키워드 (선택)

        Returns:
            매칭된 상품 정보 또는 None
        """
        if store_key not in STORE_CATEGORIES:
            return None

        matcher = self.matchers.get(store_key)

        if matcher is None:
            return None

        try:
            if store_key == "daiso":
                return self._match_daiso(matcher, product_name, price, keywords)
            elif store_key == "costco":
                return self._match_costco(matcher, product_name)
            elif store_key == "traders":
                return self._match_traders(matcher, product_name)
            elif store_key == "ikea":
                return self._match_ikea(matcher, product_name)
            elif store_key == "oliveyoung":
                return self._match_oliveyoung(matcher, product_name)
            elif store_key == "convenience":
                return self._match_convenience(matcher, product_name)
            elif store_key == "coupang":
                return self._match_coupang(matcher, product_name)
        except Exception as e:
            print(f"매칭 오류 ({store_key}, {product_name}): {e}")

        return None

    def _match_daiso(self, matcher, name: str, price: int, keywords: list) -> Optional[dict]:
        """다이소 매칭"""
        result = matcher.match_product(
            product_name=name,
            price=price,
            keywords=keywords or []
        )
        if result:
            return {
                "matched": True,
                "product_code": result.get("product_code") or result.get("product_no"),
                "official_name": result.get("official_name") or result.get("name"),
                "official_price": result.get("official_price") or result.get("price"),
                "image_url": result.get("image_url"),
                "product_url": result.get("product_url"),
                "match_source": "daiso_catalog",
            }
        return None

    def _match_costco(self, crawler, name: str) -> Optional[dict]:
        """코스트코 매칭"""
        result = crawler.search_and_match(name)
        if result:
            return {
                "matched": True,
                "product_code": result.product_code,
                "official_name": result.name,
                "official_price": result.price,
                "image_url": result.image_url,
                "product_url": result.product_url,
                "match_source": "costco_api",
            }
        return None

    def _match_ikea(self, crawler, name: str) -> Optional[dict]:
        """이케아 매칭"""
        result = crawler.search_and_match(name)
        if result:
            return {
                "matched": True,
                "product_code": result.product_code,
                "official_name": f"{result.name} {result.type_name}",
                "official_price": result.price,
                "image_url": result.image_url,
                "product_url": result.product_url,
                "match_source": "ikea_api",
            }
        return None

    def _match_oliveyoung(self, crawler, name: str) -> Optional[dict]:
        """올리브영 매칭"""
        result = crawler.search_and_match(name)
        if result:
            return {
                "matched": True,
                "product_code": result.product_code,
                "official_name": f"[{result.brand}] {result.name}",
                "official_price": result.price,
                "image_url": result.image_url,
                "product_url": result.product_url,
                "match_source": "oliveyoung_crawler",
            }
        return None

    def _match_traders(self, crawler, name: str) -> Optional[dict]:
        """트레이더스 매칭"""
        result = crawler.search_and_match(name)
        if result:
            return {
                "matched": True,
                "product_code": result.product_code,
                "official_name": result.name,
                "official_price": result.price,
                "image_url": result.image_url,
                "product_url": result.product_url,
                "match_source": "traders_api",
            }
        return None

    def _match_convenience(self, crawler, name: str) -> Optional[dict]:
        """편의점 매칭"""
        result = crawler.search_and_match(name)
        if result:
            return {
                "matched": True,
                "product_code": result.product_code,
                "official_name": result.name,
                "official_price": result.price,
                "image_url": result.image_url,
                "product_url": result.product_url,
                "store_brand": result.store,  # cu, gs25, emart24
                "is_event": result.is_event,
                "event_type": result.event_type,
                "match_source": f"convenience_{result.store}",
            }
        return None

    def _match_coupang(self, crawler, name: str) -> Optional[dict]:
        """쿠팡 매칭"""
        result = crawler.search_and_match(name)
        if result:
            return {
                "matched": True,
                "product_code": result.product_code,
                "official_name": result.name,
                "official_price": result.price,
                "image_url": result.image_url,
                "product_url": result.product_url,
                "is_rocket": result.is_rocket,
                "rating": result.rating,
                "review_count": result.review_count,
                "match_source": "coupang_search",
            }
        return None

    def compare_with_coupang(self, product_name: str, store_price: int) -> Optional[dict]:
        """다른 스토어 상품과 쿠팡 가격 비교"""
        if not self.coupang_crawler:
            return None

        return self.coupang_crawler.compare_price(product_name, store_price)

    def match_products_batch(self, products: list, store_key: str) -> list:
        """여러 상품 일괄 매칭"""
        results = []

        for product in products:
            match = self.match_product(
                product_name=product.get("name", ""),
                store_key=store_key,
                price=product.get("price"),
                keywords=product.get("keywords", [])
            )

            result = product.copy()
            if match:
                result["official"] = match
                result["is_matched"] = True
            else:
                result["official"] = {}
                result["is_matched"] = False

            results.append(result)

        return results

    def close(self):
        """리소스 해제"""
        for key, matcher in self.matchers.items():
            if matcher and hasattr(matcher, "close"):
                matcher.close()


def test_unified_matcher():
    """통합 매처 테스트"""
    matcher = UnifiedMatcher()

    print("\n=== 통합 매칭 테스트 ===\n")

    test_cases = [
        ("daiso", "스텐 배수구망", 2000),
        ("costco", "커클랜드 견과류", None),
        ("traders", "신라면 멀티팩", None),
        ("ikea", "말름 서랍장", None),
        ("convenience", "삼각김밥", None),
        ("coupang", "에어팟 프로", None),
    ]

    for store_key, product_name, price in test_cases:
        store_name = STORE_CATEGORIES[store_key]["name"]
        print(f"[{store_name}] {product_name}")

        result = matcher.match_product(product_name, store_key, price=price)

        if result:
            print(f"  -> 매칭: {result['official_name']}")
            if result.get('official_price'):
                print(f"     가격: {result['official_price']:,}원")
            print(f"     소스: {result['match_source']}")
        else:
            print(f"  -> 매칭 실패")
        print()

    # 가격 비교 테스트
    print("\n=== 쿠팡 가격 비교 테스트 ===\n")
    comparison = matcher.compare_with_coupang("스텐 배수구망", 2000)
    if comparison:
        print(f"다이소 가격: {comparison['store_price']:,}원")
        print(f"쿠팡 가격: {comparison['coupang_price']:,}원")
        print(f"차이: {comparison['price_diff']:,}원 ({comparison['diff_percent']}%)")
        print(f"더 저렴한 곳: {comparison['cheaper_at']}")

    matcher.close()


if __name__ == "__main__":
    test_unified_matcher()
