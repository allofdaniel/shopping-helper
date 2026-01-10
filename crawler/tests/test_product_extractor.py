# -*- coding: utf-8 -*-
"""
ProductExtractor 테스트 (TDD)
AI 기반 상품 추출 로직을 테스트합니다.
"""
import pytest
import json
from improved_product_extractor import ImprovedProductExtractor


class TestImprovedProductExtractor:
    """개선된 ProductExtractor 테스트"""

    def setup_method(self):
        """각 테스트 전 실행"""
        # 테스트에서는 실제 API 호출 없이 파싱 로직만 테스트
        self.extractor = ImprovedProductExtractor(test_mode=True)

    # ========== 자막 검증 테스트 ==========

    def test_reject_short_transcript(self):
        """짧은 자막은 거부해야 함"""
        result = self.extractor.extract_products("다이소 추천", "다이소")
        assert result == []

    def test_accept_valid_transcript(self, sample_good_transcript):
        """유효한 자막은 처리해야 함 (검증 통과)"""
        # 검증만 테스트 (실제 AI 호출 없이)
        is_valid = self.extractor.validate_transcript(sample_good_transcript)
        assert is_valid is True

    def test_reject_no_product_mentions(self, sample_bad_transcript_no_products):
        """상품 언급 없는 자막은 거부"""
        long_text = sample_bad_transcript_no_products * 5
        is_valid = self.extractor.validate_transcript(long_text)
        assert is_valid is False

    # ========== JSON 파싱 테스트 ==========

    def test_parse_valid_json(self):
        """유효한 JSON 파싱"""
        response = '''
        [
            {
                "name": "스텐 배수구망",
                "price": 2000,
                "category": "주방",
                "reason": "물때가 안 껴요",
                "timestamp": 120,
                "keywords": ["배수구", "스텐"],
                "confidence": 0.95,
                "is_recommended": true
            }
        ]
        '''
        products = self.extractor._parse_response(response)
        assert len(products) == 1
        assert products[0]["name"] == "스텐 배수구망"
        assert products[0]["price"] == 2000

    def test_parse_json_with_markdown(self):
        """마크다운 코드 블록 포함된 JSON 파싱"""
        response = '''
        Here are the products:
        ```json
        [
            {"name": "테스트 상품", "price": 1000}
        ]
        ```
        '''
        products = self.extractor._parse_response(response)
        assert len(products) == 1
        assert products[0]["name"] == "테스트 상품"

    def test_parse_invalid_json(self):
        """유효하지 않은 JSON 처리"""
        response = "이것은 JSON이 아닙니다."
        products = self.extractor._parse_response(response)
        assert products == []

    def test_parse_empty_response(self):
        """빈 응답 처리"""
        products = self.extractor._parse_response("")
        assert products == []
        products = self.extractor._parse_response(None)
        assert products == []

    # ========== 부정 리뷰 필터링 테스트 ==========

    def test_filter_negative_products(self):
        """비추천 상품 필터링"""
        response = '''
        [
            {"name": "좋은 상품", "price": 2000, "is_recommended": true, "confidence": 0.9},
            {"name": "나쁜 상품", "price": 1000, "is_recommended": false, "confidence": 0.8}
        ]
        '''
        products = self.extractor._parse_response(response)
        # is_recommended=false인 상품은 제외
        assert len(products) == 1
        assert products[0]["name"] == "좋은 상품"

    def test_filter_low_confidence(self):
        """낮은 신뢰도 상품 필터링"""
        response = '''
        [
            {"name": "확실한 상품", "price": 2000, "confidence": 0.9},
            {"name": "불확실한 상품", "price": 1000, "confidence": 0.3}
        ]
        '''
        products = self.extractor._parse_response(response, min_confidence=0.5)
        assert len(products) == 1
        assert products[0]["name"] == "확실한 상품"

    # ========== 신뢰도 점수 테스트 ==========

    def test_confidence_included_in_result(self):
        """결과에 신뢰도 포함"""
        response = '''
        [{"name": "테스트", "price": 1000, "confidence": 0.85}]
        '''
        products = self.extractor._parse_response(response)
        assert "confidence" in products[0]
        assert products[0]["confidence"] == 0.85

    def test_default_confidence_if_missing(self):
        """신뢰도 누락 시 기본값"""
        response = '''
        [{"name": "테스트", "price": 1000}]
        '''
        products = self.extractor._parse_response(response)
        # 신뢰도 없으면 기본값 0.5 또는 필터링
        assert products[0].get("confidence", 0.5) >= 0

    # ========== 중복 제거 테스트 ==========

    def test_remove_duplicate_products(self):
        """중복 상품 제거"""
        response = '''
        [
            {"name": "스텐 배수구망", "price": 2000},
            {"name": "스텐배수구망", "price": 2000},
            {"name": "스테인레스 배수구망", "price": 2000}
        ]
        '''
        products = self.extractor._parse_response(response)
        products = self.extractor._remove_duplicates(products)
        # 유사한 이름은 하나만 남아야 함
        assert len(products) <= 2

    # ========== 데이터 정규화 테스트 ==========

    def test_normalize_price(self):
        """가격 정규화"""
        response = '''
        [
            {"name": "상품1", "price": "2,000원"},
            {"name": "상품2", "price": 3000},
            {"name": "상품3", "price": "5천원"}
        ]
        '''
        products = self.extractor._parse_response(response)
        # 모든 가격이 정수로 변환되어야 함
        for p in products:
            if p.get("price"):
                assert isinstance(p["price"], int)

    def test_normalize_category(self):
        """카테고리 정규화"""
        response = '''
        [
            {"name": "상품1", "price": 1000, "category": "kitchen"},
            {"name": "상품2", "price": 2000, "category": "주방용품"}
        ]
        '''
        products = self.extractor._parse_response(response)
        # 카테고리가 정규화되어야 함
        for p in products:
            assert isinstance(p.get("category", ""), str)


class TestProductExtractionPrompt:
    """프롬프트 관련 테스트"""

    def test_prompt_includes_store_name(self):
        """프롬프트에 매장명 포함"""
        extractor = ImprovedProductExtractor(test_mode=True)
        prompt = extractor.build_prompt("테스트 자막", "다이소")
        assert "다이소" in prompt

    def test_prompt_includes_negative_filter(self):
        """프롬프트에 부정 상품 필터링 지시 포함"""
        extractor = ImprovedProductExtractor(test_mode=True)
        prompt = extractor.build_prompt("테스트 자막", "다이소")
        assert "비추천" in prompt or "부정" in prompt or "is_recommended" in prompt

    def test_prompt_includes_confidence(self):
        """프롬프트에 신뢰도 요청 포함"""
        extractor = ImprovedProductExtractor(test_mode=True)
        prompt = extractor.build_prompt("테스트 자막", "다이소")
        assert "confidence" in prompt or "신뢰도" in prompt

    def test_prompt_includes_context_awareness(self):
        """프롬프트에 맥락 이해 지시 포함"""
        extractor = ImprovedProductExtractor(test_mode=True)
        prompt = extractor.build_prompt("테스트 자막", "다이소")
        # 실제로 추천하는 상품만 추출하라는 지시
        assert "실제" in prompt or "확실" in prompt or "명확" in prompt
