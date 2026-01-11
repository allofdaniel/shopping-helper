# -*- coding: utf-8 -*-
"""
에러 핸들링 모듈 테스트
"""
import pytest
import sys
import os

# 상위 디렉토리 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from errors import (
    CrawlerError, NetworkError, ParseError, DatabaseError,
    RateLimitError, AuthError, TimeoutError, BrowserError,
    ErrorContext, ErrorAggregator, ErrorSeverity, ErrorCategory,
    classify_error, get_error_aggregator, handle_errors
)


class TestErrorContext:
    """ErrorContext 테스트"""

    def test_create_context(self):
        """컨텍스트 생성"""
        ctx = ErrorContext(
            store="daiso",
            operation="search",
            query="컵"
        )
        assert ctx.store == "daiso"
        assert ctx.operation == "search"
        assert ctx.query == "컵"

    def test_context_to_dict(self):
        """컨텍스트 딕셔너리 변환"""
        ctx = ErrorContext(store="costco", operation="crawl")
        data = ctx.to_dict()

        assert isinstance(data, dict)
        assert data["store"] == "costco"
        assert "timestamp" in data


class TestCrawlerErrors:
    """에러 클래스 테스트"""

    def test_network_error(self):
        """네트워크 에러"""
        err = NetworkError("Connection refused")
        assert err.category == ErrorCategory.NETWORK
        assert err.severity == ErrorSeverity.HIGH
        assert err.retryable is True

    def test_parse_error(self):
        """파싱 에러"""
        err = ParseError("JSON decode error")
        assert err.category == ErrorCategory.PARSE
        assert err.retryable is False

    def test_database_error(self):
        """데이터베이스 에러"""
        err = DatabaseError("Constraint violation")
        assert err.category == ErrorCategory.DATABASE
        assert err.retryable is True

    def test_rate_limit_error(self):
        """속도 제한 에러"""
        err = RateLimitError(retry_after=120)
        assert err.category == ErrorCategory.RATE_LIMIT
        assert err.retry_after == 120

    def test_auth_error(self):
        """인증 에러"""
        err = AuthError("Unauthorized")
        assert err.category == ErrorCategory.AUTH
        assert err.severity == ErrorSeverity.CRITICAL
        assert err.retryable is False

    def test_timeout_error(self):
        """타임아웃 에러"""
        err = TimeoutError("Request timeout")
        assert err.category == ErrorCategory.TIMEOUT
        assert err.retryable is True

    def test_browser_error(self):
        """브라우저 에러"""
        err = BrowserError("Page crashed")
        assert err.category == ErrorCategory.BROWSER
        assert err.retryable is True

    def test_error_to_dict(self):
        """에러 딕셔너리 변환"""
        ctx = ErrorContext(store="test")
        err = NetworkError("Test error", context=ctx)
        data = err.to_dict()

        assert data["error_type"] == "NetworkError"
        assert data["message"] == "Test error"
        assert data["context"]["store"] == "test"

    def test_error_str_format(self):
        """에러 문자열 포맷"""
        ctx = ErrorContext(store="daiso", operation="search")
        err = NetworkError("Connection failed", context=ctx)

        assert "[daiso]" in str(err)
        assert "(search)" in str(err)


class TestErrorClassification:
    """에러 분류 테스트"""

    def test_classify_network_error(self):
        """네트워크 에러 분류"""
        tests = [
            Exception("Connection refused"),
            Exception("Network unreachable"),
            Exception("DNS resolution failed"),
            Exception("SSL certificate error"),
        ]

        for e in tests:
            classified = classify_error(e)
            assert isinstance(classified, NetworkError), f"{e} should be NetworkError"

    def test_classify_timeout_error(self):
        """타임아웃 에러 분류"""
        tests = [
            Exception("Timeout waiting for selector"),
            Exception("Request timed out"),
            Exception("Operation time out"),
        ]

        for e in tests:
            classified = classify_error(e)
            assert isinstance(classified, TimeoutError), f"{e} should be TimeoutError"

    def test_classify_rate_limit_error(self):
        """속도 제한 에러 분류"""
        tests = [
            Exception("Rate limit exceeded"),
            Exception("Too many requests"),
            Exception("429 error"),
        ]

        for e in tests:
            classified = classify_error(e)
            assert isinstance(classified, RateLimitError), f"{e} should be RateLimitError"

    def test_classify_auth_error(self):
        """인증 에러 분류"""
        tests = [
            Exception("401 Unauthorized"),
            Exception("403 Forbidden"),
            Exception("Authentication failed"),
        ]

        for e in tests:
            classified = classify_error(e)
            assert isinstance(classified, AuthError), f"{e} should be AuthError"

    def test_classify_parse_error(self):
        """파싱 에러 분류"""
        tests = [
            Exception("JSON parse error"),
            Exception("XML decode failed"),
            Exception("Invalid encoding"),
        ]

        for e in tests:
            classified = classify_error(e)
            assert isinstance(classified, ParseError), f"{e} should be ParseError"

    def test_classify_browser_error(self):
        """브라우저 에러 분류"""
        tests = [
            Exception("Page crashed"),
            Exception("Playwright error"),
            Exception("Element not found"),
        ]

        for e in tests:
            classified = classify_error(e)
            assert isinstance(classified, BrowserError), f"{e} should be BrowserError"

    def test_classify_unknown_error(self):
        """알 수 없는 에러 분류"""
        e = Exception("Something went wrong")
        classified = classify_error(e)

        assert isinstance(classified, CrawlerError)
        assert classified.category == ErrorCategory.UNKNOWN

    def test_classify_with_context(self):
        """컨텍스트와 함께 분류"""
        ctx = ErrorContext(store="daiso", operation="search")
        e = Exception("Connection refused")

        classified = classify_error(e, ctx)
        assert classified.context.store == "daiso"


class TestErrorAggregator:
    """에러 집계기 테스트"""

    def setup_method(self):
        """각 테스트 전 실행"""
        self.agg = ErrorAggregator()

    def test_add_error(self):
        """에러 추가"""
        err = NetworkError("Test")
        self.agg.add(err)

        assert len(self.agg.errors) == 1

    def test_add_exception(self):
        """예외 추가 (자동 분류)"""
        self.agg.add_exception(Exception("Connection failed"))

        assert len(self.agg.errors) == 1
        assert isinstance(self.agg.errors[0], NetworkError)

    def test_get_by_category(self):
        """카테고리별 조회"""
        self.agg.add(NetworkError("Net1"))
        self.agg.add(NetworkError("Net2"))
        self.agg.add(ParseError("Parse1"))

        network_errors = self.agg.get_by_category(ErrorCategory.NETWORK)
        assert len(network_errors) == 2

    def test_get_by_severity(self):
        """심각도별 조회"""
        self.agg.add(AuthError("Critical1"))  # CRITICAL
        self.agg.add(NetworkError("High1"))   # HIGH
        self.agg.add(ParseError("Medium1"))   # MEDIUM

        critical = self.agg.get_by_severity(ErrorSeverity.CRITICAL)
        assert len(critical) == 1

    def test_get_retryable(self):
        """재시도 가능한 에러 조회"""
        self.agg.add(NetworkError("Retryable"))    # retryable=True
        self.agg.add(ParseError("NotRetryable"))   # retryable=False

        retryable = self.agg.get_retryable()
        assert len(retryable) == 1

    def test_has_critical(self):
        """치명적 에러 존재 여부"""
        self.agg.add(NetworkError("Not critical"))
        assert self.agg.has_critical() is False

        self.agg.add(AuthError("Critical"))
        assert self.agg.has_critical() is True

    def test_summary(self):
        """요약 생성"""
        self.agg.add(NetworkError("Net"))
        self.agg.add(NetworkError("Net2"))
        self.agg.add(ParseError("Parse"))
        self.agg.add(AuthError("Auth"))

        summary = self.agg.summary()

        assert summary["total"] == 4
        assert summary["by_category"]["network"] == 2
        assert summary["has_critical"] is True
        assert summary["retryable_count"] == 2

    def test_clear(self):
        """에러 목록 초기화"""
        self.agg.add(NetworkError("Test"))
        self.agg.clear()

        assert len(self.agg.errors) == 0


class TestHandleErrorsDecorator:
    """handle_errors 데코레이터 테스트"""

    def test_sync_function_success(self):
        """동기 함수 성공"""
        @handle_errors(store="test", default_return=-1)
        def add(a, b):
            return a + b

        assert add(1, 2) == 3

    def test_sync_function_error(self):
        """동기 함수 에러"""
        @handle_errors(store="test", default_return=-1)
        def fail():
            raise ValueError("Test error")

        result = fail()
        assert result == -1

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """비동기 함수 성공"""
        @handle_errors(store="test", default_return=[])
        async def fetch():
            return ["item1", "item2"]

        result = await fetch()
        assert result == ["item1", "item2"]

    @pytest.mark.asyncio
    async def test_async_function_error(self):
        """비동기 함수 에러"""
        @handle_errors(store="test", default_return=[])
        async def fail_async():
            raise ConnectionError("Network failed")

        result = await fail_async()
        assert result == []


class TestGlobalAggregator:
    """전역 에러 집계기 테스트"""

    def test_get_global_aggregator(self):
        """전역 집계기 반환"""
        agg1 = get_error_aggregator()
        agg2 = get_error_aggregator()

        assert agg1 is agg2  # 같은 인스턴스


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
