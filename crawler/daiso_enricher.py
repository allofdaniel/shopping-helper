# -*- coding: utf-8 -*-
"""
다이소 상품 정보 보강 모듈
- 다이소몰에서 품번 및 상세정보 조회
- 상품 데이터 자동 보강
"""
import asyncio
import time
from typing import Optional, List, Dict
from dataclasses import dataclass

from daiso_mall_scraper import DaisoMallScraper, DaisoProduct


@dataclass
class EnrichedProduct:
    """보강된 상품 정보"""
    # 원본 정보
    name: str
    price: int
    category: str = ""
    reason: str = ""
    recommendation_quote: str = ""
    video_id: str = ""
    video_start_sec: int = None
    video_end_sec: int = None

    # 다이소몰 정보
    official_code: str = ""
    official_name: str = ""
    official_price: int = None
    official_url: str = ""
    official_image_url: str = ""
    is_matched: bool = False
    match_confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "price": self.price,
            "category": self.category,
            "reason": self.reason,
            "recommendation_quote": self.recommendation_quote,
            "video_id": self.video_id,
            "video_start_sec": self.video_start_sec,
            "video_end_sec": self.video_end_sec,
            "official": {
                "product_no": self.official_code,
                "name": self.official_name,
                "price": self.official_price,
                "product_url": self.official_url,
                "image_url": self.official_image_url,
                "matched": self.is_matched,
                "confidence": self.match_confidence,
            } if self.is_matched else {},
        }


class DaisoEnricher:
    """다이소 상품 정보 보강기"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.scraper = None
        self._cache = {}  # 검색 결과 캐시

    async def _init_scraper(self):
        """스크래퍼 초기화"""
        if not self.scraper:
            self.scraper = DaisoMallScraper(headless=self.headless)
            await self.scraper._init_browser()

    async def _close_scraper(self):
        """스크래퍼 종료"""
        if self.scraper:
            await self.scraper.close()
            self.scraper = None

    async def enrich_product(self, product: dict) -> dict:
        """
        단일 상품 정보 보강

        Args:
            product: 상품 정보 딕셔너리
                - name: 상품명 (필수)
                - price: 가격
                - 기타 필드들

        Returns:
            보강된 상품 정보
        """
        await self._init_scraper()

        name = product.get("name", "")
        price = product.get("price")

        if not name:
            return product

        # 캐시 확인
        cache_key = f"{name}_{price}"
        if cache_key in self._cache:
            matched = self._cache[cache_key]
        else:
            # 다이소몰 검색
            matched = await self.scraper.search_and_match(name, price)
            self._cache[cache_key] = matched

        # 결과 병합
        enriched = product.copy()

        if matched:
            enriched["official"] = {
                "product_no": matched.product_no,
                "name": matched.name,
                "price": matched.price,
                "product_url": matched.product_url,
                "image_url": matched.image_url,
                "matched": True,
                "confidence": self._calculate_confidence(name, matched.name, price, matched.price),
            }
            enriched["official_code"] = matched.product_no
            enriched["is_matched"] = True
        else:
            enriched["official"] = {}
            enriched["is_matched"] = False
            enriched["needs_manual_review"] = True

        return enriched

    async def enrich_products(self, products: List[dict], delay: float = 1.0) -> List[dict]:
        """
        여러 상품 일괄 보강

        Args:
            products: 상품 목록
            delay: 검색 간 대기 시간

        Returns:
            보강된 상품 목록
        """
        await self._init_scraper()

        enriched_products = []

        for i, product in enumerate(products):
            print(f"  [{i+1}/{len(products)}] 보강 중: {product.get('name', '')[:20]}...")

            try:
                enriched = await self.enrich_product(product)
                enriched_products.append(enriched)

                if enriched.get("is_matched"):
                    print(f"    -> 매칭: {enriched['official'].get('product_no')}")
                else:
                    print(f"    -> 매칭 실패")

            except Exception as e:
                print(f"    -> 에러: {e}")
                enriched_products.append(product)

            await asyncio.sleep(delay)

        return enriched_products

    def _calculate_confidence(self, query_name: str, matched_name: str,
                               query_price: int = None, matched_price: int = None) -> float:
        """매칭 신뢰도 계산"""
        confidence = 0.0

        # 이름 유사도 (간단 버전)
        q_lower = query_name.lower().replace(" ", "")
        m_lower = matched_name.lower().replace(" ", "")

        if q_lower == m_lower:
            confidence += 0.5
        elif q_lower in m_lower or m_lower in q_lower:
            confidence += 0.3
        else:
            # 공통 단어 비율
            q_words = set(query_name.lower().split())
            m_words = set(matched_name.lower().split())
            if q_words and m_words:
                common = len(q_words & m_words)
                confidence += 0.2 * (common / max(len(q_words), len(m_words)))

        # 가격 일치
        if query_price and matched_price:
            if query_price == matched_price:
                confidence += 0.5
            elif abs(query_price - matched_price) <= 1000:
                confidence += 0.3

        return min(confidence, 1.0)

    async def lookup_by_code(self, product_no: str) -> Optional[dict]:
        """
        품번으로 상품 정보 조회

        Args:
            product_no: 다이소 품번

        Returns:
            상품 정보 또는 None
        """
        await self._init_scraper()

        product = await self.scraper.get_product_by_code(product_no)

        if product:
            return {
                "product_no": product.product_no,
                "name": product.name,
                "price": product.price,
                "product_url": product.product_url,
                "image_url": product.image_url,
                "is_available": product.is_available,
            }

        return None

    async def close(self):
        """리소스 정리"""
        await self._close_scraper()


class DaisoEnricherSync:
    """동기 버전 (간편 사용)"""

    def __init__(self, headless: bool = True):
        self.enricher = DaisoEnricher(headless=headless)

    def enrich_product(self, product: dict) -> dict:
        return asyncio.run(self._async_enrich(product))

    async def _async_enrich(self, product: dict) -> dict:
        try:
            result = await self.enricher.enrich_product(product)
            return result
        finally:
            await self.enricher.close()

    def enrich_products(self, products: List[dict], delay: float = 1.0) -> List[dict]:
        return asyncio.run(self._async_enrich_all(products, delay))

    async def _async_enrich_all(self, products: List[dict], delay: float) -> List[dict]:
        try:
            results = await self.enricher.enrich_products(products, delay)
            return results
        finally:
            await self.enricher.close()


async def main():
    """테스트 실행"""
    print("=== 다이소 상품 보강 테스트 ===\n")

    enricher = DaisoEnricher(headless=True)

    try:
        # 테스트 상품들
        test_products = [
            {"name": "실리콘수세미", "price": 1000, "category": "주방"},
            {"name": "에어프라이어 종이호일", "price": 2000, "category": "주방"},
            {"name": "스텐 배수구망", "price": 2000, "category": "주방"},
        ]

        print("상품 보강 시작...\n")
        enriched = await enricher.enrich_products(test_products, delay=1.5)

        print("\n=== 결과 ===")
        for p in enriched:
            print(f"\n상품: {p['name']}")
            if p.get("is_matched"):
                official = p.get("official", {})
                print(f"  -> 품번: {official.get('product_no')}")
                print(f"  -> 공식명: {official.get('name')}")
                print(f"  -> 가격: {official.get('price')}원")
                print(f"  -> URL: {official.get('product_url')}")
            else:
                print(f"  -> 매칭 실패 (수동 검토 필요)")

    finally:
        await enricher.close()


if __name__ == "__main__":
    asyncio.run(main())
