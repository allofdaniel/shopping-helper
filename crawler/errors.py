# -*- coding: utf-8 -*-
"""
꿀템장바구니 - 표준화된 에러 핸들링 모듈

에러 계층구조:
- CrawlerError (기본)
  - NetworkError (네트워크 관련)
  - ParseError (파싱 관련)
  - DatabaseError (DB 관련)
  - RateLimitError (속도 제한)
  - AuthError (인증 관련)
  - TimeoutError (타임아웃)
"""
import traceback
from enum import Enum
from typing import Optional, Dict, Any, Callable, TypeVar
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime


class ErrorSeverity(Enum):
    """에러 심각도"""
    LOW = "low"           # 무시 가능
    MEDIUM = "medium"     # 로깅 필요
    HIGH = "high"         # 재시도 필요
    CRITICAL = "critical" # 즉시 중단


class ErrorCategory(Enum):
    """에러 카테고리"""
    NETWORK = "network"
    PARSE = "parse"
    DATABASE = "database"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    TIMEOUT = "timeout"
    BROWSER = "browser"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """에러 컨텍스트 정보"""
    store: str = ""
    operation: str = ""
    url: str = ""
    query: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "store": self.store,
            "operation": self.operation,
            "url": self.url,
            "query": self.query,
            "timestamp": self.timestamp.isoformat(),
            "extra": self.extra,
        }


class CrawlerError(Exception):
    """크롤러 기본 에러"""

    category = ErrorCategory.UNKNOWN
    severity = ErrorSeverity.MEDIUM
    retryable = False

    def __init__(
        self,
        message: str,
        context: ErrorContext = None,
        original_error: Exception = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext()
        self.original_error = original_error
        self.stack_trace = traceback.format_exc() if original_error else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "retryable": self.retryable,
            "context": self.context.to_dict(),
            "original_error": str(self.original_error) if self.original_error else None,
        }

    def __str__(self) -> str:
        parts = [self.message]
        if self.context.store:
            parts.insert(0, f"[{self.context.store}]")
        if self.context.operation:
            parts.insert(1, f"({self.context.operation})")
        return " ".join(parts)


class NetworkError(CrawlerError):
    """네트워크 관련 에러"""
    category = ErrorCategory.NETWORK
    severity = ErrorSeverity.HIGH
    retryable = True


class ParseError(CrawlerError):
    """파싱 관련 에러"""
    category = ErrorCategory.PARSE
    severity = ErrorSeverity.MEDIUM
    retryable = False


class DatabaseError(CrawlerError):
    """데이터베이스 관련 에러"""
    category = ErrorCategory.DATABASE
    severity = ErrorSeverity.HIGH
    retryable = True


class RateLimitError(CrawlerError):
    """속도 제한 에러"""
    category = ErrorCategory.RATE_LIMIT
    severity = ErrorSeverity.HIGH
    retryable = True

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AuthError(CrawlerError):
    """인증 관련 에러"""
    category = ErrorCategory.AUTH
    severity = ErrorSeverity.CRITICAL
    retryable = False


class TimeoutError(CrawlerError):
    """타임아웃 에러"""
    category = ErrorCategory.TIMEOUT
    severity = ErrorSeverity.HIGH
    retryable = True


class BrowserError(CrawlerError):
    """브라우저 관련 에러"""
    category = ErrorCategory.BROWSER
    severity = ErrorSeverity.HIGH
    retryable = True


# 에러 분류 함수
def classify_error(error: Exception, context: ErrorContext = None) -> CrawlerError:
    """
    일반 에러를 CrawlerError로 분류

    Args:
        error: 원본 에러
        context: 에러 컨텍스트

    Returns:
        분류된 CrawlerError
    """
    error_str = str(error).lower()

    # 네트워크 에러
    if any(keyword in error_str for keyword in [
        "connection", "network", "dns", "ssl", "tls",
        "refused", "reset", "unreachable", "socket"
    ]):
        return NetworkError(str(error), context, error)

    # 타임아웃
    if any(keyword in error_str for keyword in [
        "timeout", "timed out", "time out"
    ]):
        return TimeoutError(str(error), context, error)

    # 속도 제한
    if any(keyword in error_str for keyword in [
        "rate limit", "too many requests", "429", "throttl"
    ]):
        return RateLimitError(str(error), context=context, original_error=error)

    # 인증
    if any(keyword in error_str for keyword in [
        "auth", "unauthorized", "forbidden", "403", "401", "login"
    ]):
        return AuthError(str(error), context, error)

    # 파싱
    if any(keyword in error_str for keyword in [
        "parse", "json", "xml", "decode", "encoding", "invalid"
    ]):
        return ParseError(str(error), context, error)

    # 브라우저
    if any(keyword in error_str for keyword in [
        "browser", "playwright", "chromium", "page", "selector", "element"
    ]):
        return BrowserError(str(error), context, error)

    # 데이터베이스
    if any(keyword in error_str for keyword in [
        "database", "sqlite", "sql", "query", "constraint"
    ]):
        return DatabaseError(str(error), context, error)

    # 기본
    return CrawlerError(str(error), context, error)


# 데코레이터
T = TypeVar('T')


def handle_errors(
    store: str = "",
    operation: str = "",
    default_return: Any = None,
    reraise: bool = False,
    logger: Any = None,
):
    """
    에러 핸들링 데코레이터

    Args:
        store: 매장 이름
        operation: 작업 이름
        default_return: 에러 시 반환값
        reraise: 에러 재발생 여부
        logger: 로거 인스턴스

    Example:
        @handle_errors(store="daiso", operation="search", default_return=[])
        async def search_products(query):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            context = ErrorContext(store=store, operation=operation)
            try:
                return await func(*args, **kwargs)
            except CrawlerError:
                raise
            except Exception as e:
                classified = classify_error(e, context)
                if logger:
                    logger.error(str(classified), exc_info=True)
                if reraise:
                    raise classified from e
                return default_return

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            context = ErrorContext(store=store, operation=operation)
            try:
                return func(*args, **kwargs)
            except CrawlerError:
                raise
            except Exception as e:
                classified = classify_error(e, context)
                if logger:
                    logger.error(str(classified), exc_info=True)
                if reraise:
                    raise classified from e
                return default_return

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class ErrorAggregator:
    """에러 집계기"""

    def __init__(self):
        self.errors: list[CrawlerError] = []

    def add(self, error: CrawlerError):
        """에러 추가"""
        self.errors.append(error)

    def add_exception(self, error: Exception, context: ErrorContext = None):
        """일반 예외 추가"""
        classified = classify_error(error, context)
        self.errors.append(classified)

    def get_by_category(self, category: ErrorCategory) -> list[CrawlerError]:
        """카테고리별 에러 조회"""
        return [e for e in self.errors if e.category == category]

    def get_by_severity(self, severity: ErrorSeverity) -> list[CrawlerError]:
        """심각도별 에러 조회"""
        return [e for e in self.errors if e.severity == severity]

    def get_retryable(self) -> list[CrawlerError]:
        """재시도 가능한 에러 조회"""
        return [e for e in self.errors if e.retryable]

    def has_critical(self) -> bool:
        """치명적 에러 존재 여부"""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)

    def summary(self) -> Dict[str, Any]:
        """에러 요약"""
        by_category = {}
        by_severity = {}

        for error in self.errors:
            cat = error.category.value
            sev = error.severity.value

            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total": len(self.errors),
            "by_category": by_category,
            "by_severity": by_severity,
            "has_critical": self.has_critical(),
            "retryable_count": len(self.get_retryable()),
        }

    def clear(self):
        """에러 목록 초기화"""
        self.errors.clear()


# 싱글톤 에러 집계기
_global_aggregator = ErrorAggregator()


def get_error_aggregator() -> ErrorAggregator:
    """전역 에러 집계기 반환"""
    return _global_aggregator


if __name__ == "__main__":
    # 테스트
    ctx = ErrorContext(store="daiso", operation="search", query="컵")

    # 에러 분류 테스트
    test_errors = [
        Exception("Connection refused"),
        Exception("Timeout waiting for selector"),
        Exception("Rate limit exceeded"),
        Exception("JSON decode error"),
        Exception("SQLite constraint violation"),
        Exception("Something went wrong"),
    ]

    for err in test_errors:
        classified = classify_error(err, ctx)
        print(f"{err} -> {classified.__class__.__name__} ({classified.category.value})")

    # 집계기 테스트
    agg = ErrorAggregator()
    for err in test_errors:
        agg.add_exception(err, ctx)

    print("\n=== Summary ===")
    print(agg.summary())
