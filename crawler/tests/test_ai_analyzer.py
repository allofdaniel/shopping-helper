# -*- coding: utf-8 -*-
"""
AI Analyzer 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAIAnalyzerInit:
    """AIAnalyzer 초기화 테스트"""

    def test_init_without_api_key_raises_error(self):
        """API 키 없이 초기화하면 에러"""
        with patch.dict('os.environ', {}, clear=True):
            with patch('ai_analyzer.GEMINI_API_KEY', None):
                from ai_analyzer import AIAnalyzer
                with pytest.raises(ValueError, match="API 키"):
                    AIAnalyzer(api_key=None)

    def test_init_with_api_key(self):
        """API 키로 초기화"""
        with patch('ai_analyzer.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = Mock()
            from ai_analyzer import AIAnalyzer
            analyzer = AIAnalyzer(api_key="test-key")
            assert analyzer.api_key == "test-key"


class TestProductValidation:
    """상품 데이터 검증 테스트"""

    @pytest.fixture
    def analyzer(self):
        """테스트용 analyzer"""
        with patch('ai_analyzer.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = Mock()
            from ai_analyzer import AIAnalyzer
            return AIAnalyzer(api_key="test-key")

    def test_validate_empty_products(self, analyzer):
        """빈 리스트 검증"""
        result = analyzer._validate_products([])
        assert result == []

    def test_validate_products_with_invalid_items(self, analyzer):
        """잘못된 항목 필터링"""
        products = [
            {"name": "좋은상품", "price": 1000},  # 유효
            {"name": "", "price": 500},  # 이름 빈 문자열
            {"price": 1000},  # 이름 없음
            "not a dict",  # 딕셔너리 아님
            {"name": "x", "price": 100},  # 이름 너무 짧음
        ]
        result = analyzer._validate_products(products)
        assert len(result) == 1
        assert result[0]["name"] == "좋은상품"

    def test_validate_products_normalizes_data(self, analyzer):
        """데이터 정규화"""
        products = [
            {
                "name": "  테스트 상품  ",
                "price": "1,000원",
                "category": "생활용품",
                "reason": "좋은 이유",
                "timestamp": "2:30",
                "keywords": ["키워드1", "키워드2"]
            }
        ]
        result = analyzer._validate_products(products)
        assert result[0]["name"] == "테스트 상품"
        assert result[0]["price"] == 1000
        assert result[0]["timestamp"] == 150  # 2분 30초


class TestPriceParser:
    """가격 파싱 테스트"""

    @pytest.fixture
    def analyzer(self):
        with patch('ai_analyzer.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = Mock()
            from ai_analyzer import AIAnalyzer
            return AIAnalyzer(api_key="test-key")

    def test_parse_integer_price(self, analyzer):
        """정수 가격"""
        assert analyzer._parse_price(1000) == 1000

    def test_parse_float_price(self, analyzer):
        """실수 가격"""
        assert analyzer._parse_price(1000.5) == 1000

    def test_parse_string_price_with_comma(self, analyzer):
        """쉼표 포함 문자열"""
        assert analyzer._parse_price("1,000원") == 1000

    def test_parse_string_price_with_cheon(self, analyzer):
        """'천' 단위"""
        assert analyzer._parse_price("3천원") == 3000

    def test_parse_string_price_with_man(self, analyzer):
        """'만' 단위"""
        assert analyzer._parse_price("1만원") == 10000

    def test_parse_none_price(self, analyzer):
        """None 가격"""
        assert analyzer._parse_price(None) is None

    def test_parse_invalid_string(self, analyzer):
        """잘못된 문자열"""
        assert analyzer._parse_price("무료") is None


class TestTimestampParser:
    """타임스탬프 파싱 테스트"""

    @pytest.fixture
    def analyzer(self):
        with patch('ai_analyzer.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = Mock()
            from ai_analyzer import AIAnalyzer
            return AIAnalyzer(api_key="test-key")

    def test_parse_integer_timestamp(self, analyzer):
        """정수 타임스탬프"""
        assert analyzer._parse_timestamp(150) == 150

    def test_parse_mmss_format(self, analyzer):
        """MM:SS 형식"""
        assert analyzer._parse_timestamp("2:30") == 150

    def test_parse_hhmmss_format(self, analyzer):
        """HH:MM:SS 형식"""
        assert analyzer._parse_timestamp("1:02:30") == 3750

    def test_parse_none_timestamp(self, analyzer):
        """None 타임스탬프"""
        assert analyzer._parse_timestamp(None) is None


class TestExtractProducts:
    """상품 추출 테스트"""

    @pytest.fixture
    def analyzer(self):
        with patch('ai_analyzer.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            from ai_analyzer import AIAnalyzer
            analyzer = AIAnalyzer(api_key="test-key")
            analyzer.model = mock_model
            return analyzer

    def test_extract_with_empty_transcript(self, analyzer):
        """빈 자막"""
        result = analyzer.extract_products("", "다이소")
        assert result == []

    def test_extract_with_short_transcript(self, analyzer):
        """너무 짧은 자막"""
        result = analyzer.extract_products("짧은 텍스트", "다이소")
        assert result == []

    def test_extract_with_valid_response(self, analyzer):
        """유효한 AI 응답"""
        mock_response = Mock()
        mock_response.text = '''
        [
            {"name": "스텐 배수구망", "price": 2000, "category": "주방용품", "reason": "좋아요"}
        ]
        '''
        analyzer.model.generate_content.return_value = mock_response

        # 자막은 50자 이상이어야 함
        long_transcript = "다이소에서 스텐 배수구망 2천원에 샀는데 진짜 좋아요 강추! 이 제품 정말 추천드립니다. 가성비가 너무 좋고 품질도 괜찮아요."
        result = analyzer.extract_products(long_transcript, "다이소")
        assert len(result) == 1
        assert result[0]["name"] == "스텐 배수구망"

    def test_extract_handles_json_error(self, analyzer):
        """JSON 파싱 오류 처리"""
        mock_response = Mock()
        mock_response.text = "이것은 유효한 JSON이 아닙니다"
        analyzer.model.generate_content.return_value = mock_response

        result = analyzer.extract_products("다이소 추천 상품입니다" * 10, "다이소")
        assert result == []

    def test_extract_handles_api_error(self, analyzer):
        """API 오류 처리"""
        analyzer.model.generate_content.side_effect = Exception("API Error")

        result = analyzer.extract_products("다이소 추천 상품입니다" * 10, "다이소")
        assert result == []
