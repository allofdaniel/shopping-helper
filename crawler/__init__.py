# -*- coding: utf-8 -*-
"""
꿀템장바구니 크롤러 패키지
YouTube 영상에서 오프라인 매장 추천 상품을 수집합니다.
"""

from .config import (
    YOUTUBE_API_KEY,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    DB_PATH,
    DATA_DIR,
    STORE_CATEGORIES,
    validate_config,
    check_required_config,
)

from .errors import (
    CrawlerError,
    NetworkError,
    ParseError,
    DatabaseError,
    RateLimitError,
    AuthError,
    TimeoutError,
    BrowserError,
    classify_error,
    ErrorAggregator,
    handle_errors,
)

from .rate_limiter import (
    RateLimiter,
    get_limiter,
    rate_limit,
    YOUTUBE_LIMITER,
    GEMINI_LIMITER,
    SCRAPER_LIMITER,
)

__version__ = "1.0.0"
__author__ = "꿀템장바구니"

__all__ = [
    # Config
    "YOUTUBE_API_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "DB_PATH",
    "DATA_DIR",
    "STORE_CATEGORIES",
    "validate_config",
    "check_required_config",
    # Errors
    "CrawlerError",
    "NetworkError",
    "ParseError",
    "DatabaseError",
    "RateLimitError",
    "AuthError",
    "TimeoutError",
    "BrowserError",
    "classify_error",
    "ErrorAggregator",
    "handle_errors",
    # Rate Limiter
    "RateLimiter",
    "get_limiter",
    "rate_limit",
    "YOUTUBE_LIMITER",
    "GEMINI_LIMITER",
    "SCRAPER_LIMITER",
]
