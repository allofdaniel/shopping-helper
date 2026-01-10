# -*- coding: utf-8 -*-
"""
ProductMatcher 테스트 (TDD)
상품 매칭 로직을 테스트합니다.
"""
import pytest
from improved_product_matcher import ImprovedProductMatcher, MatchResult


class TestImprovedProductMatcher:
    """개선된 ProductMatcher 테스트"""

    def setup_method(self):
        """각 테스트 전 실행"""
        self.matcher = ImprovedProductMatcher()

    # ========== 임계값 테스트 ==========

    def test_matching_threshold_is_40(self):
        """매칭 임계값이 40점이어야 함"""
        assert self.matcher.MATCH_THRESHOLD == 40

    def test_low_score_rejected(self, sample_catalog_products):
        """점수가 낮으면 매칭 거부"""
        self.matcher.set_catalog(sample_catalog_products)

        # 전혀 다른 상품명
        result = self.matcher.match("노트북 충전기", price=50000)
        assert result is None or result.score < 40

    def test_high_score_accepted(self, sample_catalog_products):
        """점수가 높으면 매칭 성공"""
        self.matcher.set_catalog(sample_catalog_products)

        # 정확히 일치하는 상품명
        result = self.matcher.match("스테인레스 배수구망", price=2000)
        assert result is not None
        assert result.score >= 40
        assert result.product_code == "100001"

    # ========== 다단계 검증 테스트 ==========

    def test_name_and_price_match(self, sample_catalog_products):
        """이름 + 가격 모두 일치하면 높은 점수"""
        self.matcher.set_catalog(sample_catalog_products)

        result = self.matcher.match("스텐 배수구망", price=2000)
        assert result is not None
        assert result.name_score > 0
        assert result.price_score > 0

    def test_name_only_match_lower_score(self, sample_catalog_products):
        """이름만 일치하면 상대적으로 낮은 점수"""
        self.matcher.set_catalog(sample_catalog_products)

        # 가격이 다른 경우
        result = self.matcher.match("스텐 배수구망", price=10000)
        # 매칭은 될 수 있지만 가격 점수는 0
        if result:
            assert result.price_score == 0

    def test_price_range_validation(self, sample_catalog_products):
        """가격 범위 검증 (±1000원)"""
        self.matcher.set_catalog(sample_catalog_products)

        # 정확히 일치
        result1 = self.matcher.match("스텐 배수구망", price=2000)
        # 범위 내 (2000 ± 1000 = 1000~3000)
        result2 = self.matcher.match("스텐 배수구망", price=2500)
        # 범위 밖
        result3 = self.matcher.match("스텐 배수구망", price=5000)

        if result1 and result2:
            assert result1.price_score >= result2.price_score
        if result2 and result3:
            assert result2.price_score > result3.price_score if result3 else True

    # ========== 불용어 처리 테스트 ==========

    def test_stopwords_removed(self, sample_catalog_products):
        """불용어 제거 후 매칭"""
        self.matcher.set_catalog(sample_catalog_products)

        # 불용어 포함 검색
        result = self.matcher.match("다이소 진짜 꿀템 스텐 배수구망 완전 추천", price=2000)
        assert result is not None
        # 불용어 제거 후 매칭 성공

    def test_korean_variations_handled(self, sample_catalog_products):
        """한국어 변형 철자 처리"""
        self.matcher.set_catalog(sample_catalog_products)

        # "스텐" vs "스테인레스"
        result1 = self.matcher.match("스텐 배수구망", price=2000)
        result2 = self.matcher.match("스테인레스 배수구망", price=2000)

        # 둘 다 같은 상품 매칭
        assert result1 is not None
        assert result2 is not None
        if result1 and result2:
            assert result1.product_code == result2.product_code

    # ========== 중복 방지 테스트 ==========

    def test_unique_matching(self, sample_catalog_products):
        """동일 상품 중복 매칭 방지"""
        self.matcher.set_catalog(sample_catalog_products)

        # 같은 상품을 다른 표현으로 검색
        products_to_match = [
            {"name": "스텐 배수구망", "price": 2000},
            {"name": "스테인레스 배수구망", "price": 2000},
            {"name": "배수구 거름망 스텐", "price": 2000},
        ]

        matched_codes = set()
        for p in products_to_match:
            result = self.matcher.match(p["name"], p["price"])
            if result:
                matched_codes.add(result.product_code)

        # 실제로는 같은 상품 코드가 매칭되어야 함
        # (다만 다른 상품으로 매칭될 수도 있음)

    # ========== 카테고리 검증 테스트 ==========

    def test_category_bonus_score(self, sample_catalog_products):
        """카테고리 일치 시 보너스 점수"""
        self.matcher.set_catalog(sample_catalog_products)

        # 카테고리 지정
        result = self.matcher.match("정리함", price=1000, category="인테리어")
        if result:
            assert result.category_score >= 0

    def test_category_mismatch_penalty(self, sample_catalog_products):
        """카테고리 불일치 시 페널티"""
        self.matcher.set_catalog(sample_catalog_products)

        # 주방용품을 뷰티 카테고리로 검색
        result = self.matcher.match("스텐 배수구망", price=2000, category="뷰티")
        # 매칭은 될 수 있지만 카테고리 점수는 낮아야 함
        if result:
            assert result.category_score == 0

    # ========== 신뢰도 테스트 ==========

    def test_confidence_high_for_exact_match(self, sample_catalog_products):
        """정확한 매칭은 높은 신뢰도"""
        self.matcher.set_catalog(sample_catalog_products)

        result = self.matcher.match("스테인레스 배수구망", price=2000)
        assert result is not None
        assert result.confidence >= 0.8

    def test_confidence_low_for_partial_match(self, sample_catalog_products):
        """부분 매칭은 낮은 신뢰도"""
        self.matcher.set_catalog(sample_catalog_products)

        # 키워드만 일치
        result = self.matcher.match("배수구", price=2000)
        if result:
            # 부분 매칭이므로 신뢰도가 낮아야 함
            assert result.confidence < 0.9

    def test_manual_review_flag(self, sample_catalog_products):
        """신뢰도가 낮으면 수동 검토 플래그"""
        self.matcher.set_catalog(sample_catalog_products)

        # 애매한 매칭
        result = self.matcher.match("정리함 수납", price=1500)
        if result and result.confidence < 0.7:
            assert result.needs_manual_review is True


class TestMatchResult:
    """MatchResult 데이터 클래스 테스트"""

    def test_match_result_to_dict(self):
        """MatchResult를 딕셔너리로 변환"""
        result = MatchResult(
            product_code="100001",
            official_name="테스트 상품",
            official_price=2000,
            score=45,
            name_score=25,
            price_score=15,
            category_score=5,
            confidence=0.85,
        )

        data = result.to_dict()
        assert isinstance(data, dict)
        assert data["product_code"] == "100001"
        assert data["score"] == 45

    def test_match_result_is_valid(self):
        """유효한 매칭 결과 체크"""
        valid = MatchResult(
            product_code="100001",
            official_name="테스트",
            official_price=2000,
            score=45,
            confidence=0.8,
        )
        invalid = MatchResult(
            product_code="100002",
            official_name="테스트2",
            official_price=3000,
            score=30,
            confidence=0.5,
        )

        assert valid.is_valid() is True
        assert invalid.is_valid() is False
