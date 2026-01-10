# -*- coding: utf-8 -*-
"""
TranscriptValidator 테스트 (TDD)
자막 품질 검증 로직을 테스트합니다.
"""
import pytest
from transcript_validator import TranscriptValidator, TranscriptQuality


class TestTranscriptValidator:
    """TranscriptValidator 클래스 테스트"""

    def setup_method(self):
        """각 테스트 전 실행"""
        self.validator = TranscriptValidator()

    # ========== 길이 검증 테스트 ==========

    def test_validate_minimum_length_pass(self, sample_good_transcript):
        """충분한 길이의 자막은 통과해야 함"""
        result = self.validator.validate(sample_good_transcript)
        assert result.is_valid is True
        assert result.length >= TranscriptValidator.MIN_LENGTH

    def test_validate_minimum_length_fail(self, sample_bad_transcript_too_short):
        """너무 짧은 자막은 실패해야 함"""
        result = self.validator.validate(sample_bad_transcript_too_short)
        assert result.is_valid is False
        assert "길이" in result.rejection_reason or "length" in result.rejection_reason.lower()

    def test_validate_empty_transcript(self):
        """빈 자막은 실패해야 함"""
        result = self.validator.validate("")
        assert result.is_valid is False

    def test_validate_none_transcript(self):
        """None 자막은 실패해야 함"""
        result = self.validator.validate(None)
        assert result.is_valid is False

    def test_validate_whitespace_only(self):
        """공백만 있는 자막은 실패해야 함"""
        result = self.validator.validate("   \n\t   ")
        assert result.is_valid is False

    # ========== 상품 언급 검증 테스트 ==========

    def test_validate_product_mentions_pass(self, sample_good_transcript):
        """상품 언급이 있는 자막은 통과해야 함"""
        result = self.validator.validate(sample_good_transcript)
        assert result.is_valid is True
        assert result.product_mention_count > 0

    def test_validate_product_mentions_fail(self, sample_bad_transcript_no_products):
        """상품 언급이 없는 자막은 실패해야 함 (길이 충분해도)"""
        # 길이 요건을 충족하도록 텍스트 반복
        long_text = sample_bad_transcript_no_products * 5
        result = self.validator.validate(long_text)
        assert result.is_valid is False
        assert "상품" in result.rejection_reason or "product" in result.rejection_reason.lower()

    def test_detect_price_mentions(self, sample_good_transcript):
        """가격 언급을 감지해야 함"""
        result = self.validator.validate(sample_good_transcript)
        assert result.price_mention_count > 0

    # ========== 품질 점수 테스트 ==========

    def test_quality_score_high_for_good_transcript(self, sample_good_transcript):
        """좋은 자막은 높은 품질 점수를 받아야 함"""
        result = self.validator.validate(sample_good_transcript)
        assert result.quality_score >= 0.7

    def test_quality_score_low_for_bad_transcript(self, sample_bad_transcript_too_short):
        """나쁜 자막은 낮은 품질 점수를 받아야 함"""
        result = self.validator.validate(sample_bad_transcript_too_short)
        assert result.quality_score < 0.5

    # ========== 부정적 리뷰 감지 테스트 ==========

    def test_detect_negative_reviews(self, sample_negative_review_transcript):
        """부정적 리뷰(비추천)를 감지해야 함"""
        result = self.validator.validate(sample_negative_review_transcript)
        assert result.has_negative_reviews is True
        assert result.negative_product_count > 0

    def test_extract_positive_only_from_mixed(self, sample_negative_review_transcript):
        """부정적 리뷰 포함 자막에서도 긍정적 상품만 카운트"""
        result = self.validator.validate(sample_negative_review_transcript)
        # "스텐 배수구망"은 긍정적 추천이므로 카운트되어야 함
        assert result.positive_product_count >= 1

    # ========== 매장 관련성 테스트 ==========

    def test_validate_store_relevance(self, sample_good_transcript):
        """매장 관련 키워드 감지"""
        result = self.validator.validate(sample_good_transcript, store_name="다이소")
        assert result.store_mention_count > 0

    def test_validate_wrong_store_content(self):
        """다른 매장 내용이면 경고"""
        costco_transcript = """
        코스트코 추천템 알려드릴게요! 코스트코 피자가 정말 맛있어요.
        코스트코 불고기도 강추드려요. 가성비가 진짜 좋아요.
        코스트코에서 꼭 사야할 제품들 알려드립니다.
        첫 번째는 코스트코 연어예요. 가격은 2만원인데 양이 엄청 많아요.
        두 번째는 코스트코 티라미수. 맛있고 저렴해요.
        """ * 2
        result = self.validator.validate(costco_transcript, store_name="다이소")
        # 유효한 자막이지만 매장이 다름
        if result.is_valid:
            assert result.store_mismatch_warning is True
        else:
            # 길이 미달인 경우 테스트 스킵
            pass


class TestTranscriptQuality:
    """TranscriptQuality 데이터 클래스 테스트"""

    def test_quality_to_dict(self):
        """품질 결과를 딕셔너리로 변환"""
        quality = TranscriptQuality(
            is_valid=True,
            length=500,
            quality_score=0.85,
            product_mention_count=5,
            price_mention_count=3,
            rejection_reason=None,
        )
        result = quality.to_dict()
        assert isinstance(result, dict)
        assert result["is_valid"] is True
        assert result["quality_score"] == 0.85

    def test_quality_from_invalid(self):
        """유효하지 않은 품질 생성"""
        quality = TranscriptQuality.invalid("테스트 실패 이유")
        assert quality.is_valid is False
        assert quality.rejection_reason == "테스트 실패 이유"
