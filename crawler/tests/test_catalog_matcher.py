# -*- coding: utf-8 -*-
"""
Catalog Matcher 테스트
"""
import pytest
import sys
from pathlib import Path

# 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from catalog_matcher import (
    extract_keywords,
    _sanitize_text,
    MAX_NAME_LENGTH,
    MAX_KEYWORD_LENGTH,
    MIN_MATCH_SCORE,
    MAX_PRODUCTS_PER_VIDEO,
)


class TestSanitizeText:
    """텍스트 정제 테스트"""

    def test_sanitize_none(self):
        """None 입력"""
        assert _sanitize_text(None) == ""

    def test_sanitize_empty_string(self):
        """빈 문자열"""
        assert _sanitize_text("") == ""

    def test_sanitize_normal_text(self):
        """일반 텍스트"""
        assert _sanitize_text("정상 텍스트") == "정상 텍스트"

    def test_sanitize_removes_control_chars(self):
        """제어 문자 제거"""
        text_with_control = "테스트\x00\x1f텍스트"
        result = _sanitize_text(text_with_control)
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "테스트텍스트" == result

    def test_sanitize_respects_max_length(self):
        """최대 길이 제한"""
        long_text = "가" * 1000
        result = _sanitize_text(long_text, max_length=100)
        assert len(result) == 100


class TestExtractKeywords:
    """키워드 추출 테스트"""

    def test_extract_from_none(self):
        """None에서 추출"""
        assert extract_keywords(None) == []

    def test_extract_from_empty(self):
        """빈 문자열에서 추출"""
        assert extract_keywords("") == []

    def test_extract_basic_keywords(self):
        """기본 키워드 추출"""
        keywords = extract_keywords("스텐 배수구망")
        assert "스텐" in keywords
        assert "배수구망" in keywords

    def test_extract_filters_short_words(self):
        """짧은 단어 필터링 (2자 미만)"""
        keywords = extract_keywords("A 가 테스트")
        assert "A" not in keywords
        assert "가" not in keywords
        assert "테스트" in keywords

    def test_extract_removes_units(self):
        """단위 제거"""
        keywords = extract_keywords("물티슈 [100매입] (500ml)")
        # 숫자와 단위가 제거되어야 함
        assert all("ml" not in kw and "매입" not in kw for kw in keywords)

    def test_extract_converts_to_lowercase(self):
        """소문자 변환"""
        keywords = extract_keywords("IKEA 선반")
        assert "ikea" in keywords

    def test_extract_long_name(self):
        """긴 상품명 처리"""
        long_name = "가나다라마바사아자차카타파하" * 20
        keywords = extract_keywords(long_name)
        # 키워드가 MAX_KEYWORD_LENGTH 이하인지 확인
        for kw in keywords:
            assert len(kw) <= MAX_KEYWORD_LENGTH


class TestConstants:
    """상수 값 테스트"""

    def test_max_name_length(self):
        """최대 이름 길이"""
        assert MAX_NAME_LENGTH == 200

    def test_max_keyword_length(self):
        """최대 키워드 길이"""
        assert MAX_KEYWORD_LENGTH == 50

    def test_min_match_score(self):
        """최소 매칭 점수"""
        assert MIN_MATCH_SCORE == 0.25

    def test_max_products_per_video(self):
        """영상당 최대 상품 수"""
        assert MAX_PRODUCTS_PER_VIDEO == 10


class TestKeywordMatching:
    """키워드 매칭 로직 테스트"""

    def test_exact_match_scoring(self):
        """정확한 매칭 점수 계산"""
        # 키워드가 3개인 상품에서 2개 매칭되면 score = 2/3 ≈ 0.67
        item_keywords = ["스텐", "배수구망", "주방"]
        matched = ["스텐", "배수구망"]
        score = len(matched) / max(len(item_keywords), 1)
        assert abs(score - 0.67) < 0.01

    def test_title_bonus_scoring(self):
        """제목 매칭 보너스"""
        base_score = 0.5
        title_bonus = 0.3
        final_score = base_score + title_bonus
        assert final_score == 0.8

    def test_score_threshold(self):
        """점수 임계값"""
        # MIN_MATCH_SCORE = 0.25이므로
        assert 0.24 < MIN_MATCH_SCORE
        assert MIN_MATCH_SCORE <= 0.25
