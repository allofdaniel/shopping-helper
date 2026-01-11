# -*- coding: utf-8 -*-
"""
Rate Limiter - API 호출 속도 제한
"""
import time
import asyncio
from typing import Optional, Dict
from functools import wraps
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RateLimitConfig:
    """Rate limit 설정"""
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    burst_size: int = 5  # 순간적으로 허용되는 요청 수


class RateLimiter:
    """
    Token Bucket 알고리즘 기반 Rate Limiter

    사용법:
        limiter = RateLimiter(requests_per_second=2)

        # 동기 사용
        limiter.wait()
        make_api_call()

        # 비동기 사용
        await limiter.wait_async()
        await make_api_call()

        # 데코레이터 사용
        @limiter.limit
        def api_call():
            pass
    """

    def __init__(
        self,
        requests_per_second: float = 1.0,
        burst_size: int = 5,
        name: str = "default"
    ):
        self.rate = requests_per_second
        self.burst_size = burst_size
        self.name = name

        self.tokens = float(burst_size)
        self.last_update = time.monotonic()
        self._lock = Lock()

        # 통계
        self.total_requests = 0
        self.total_waits = 0

    def _update_tokens(self) -> None:
        """토큰 갱신"""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)
        self.last_update = now

    def wait(self) -> float:
        """
        토큰 소비 대기 (동기)

        Returns:
            대기 시간 (초)
        """
        with self._lock:
            self._update_tokens()

            if self.tokens >= 1:
                self.tokens -= 1
                self.total_requests += 1
                return 0.0

            # 토큰 부족 - 대기 필요
            wait_time = (1 - self.tokens) / self.rate
            self.total_waits += 1

        time.sleep(wait_time)

        with self._lock:
            self.tokens = 0
            self.last_update = time.monotonic()
            self.total_requests += 1

        return wait_time

    async def wait_async(self) -> float:
        """
        토큰 소비 대기 (비동기)

        Returns:
            대기 시간 (초)
        """
        with self._lock:
            self._update_tokens()

            if self.tokens >= 1:
                self.tokens -= 1
                self.total_requests += 1
                return 0.0

            wait_time = (1 - self.tokens) / self.rate
            self.total_waits += 1

        await asyncio.sleep(wait_time)

        with self._lock:
            self.tokens = 0
            self.last_update = time.monotonic()
            self.total_requests += 1

        return wait_time

    def limit(self, func):
        """동기 함수용 데코레이터"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.wait()
            return func(*args, **kwargs)
        return wrapper

    def limit_async(self, func):
        """비동기 함수용 데코레이터"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await self.wait_async()
            return await func(*args, **kwargs)
        return wrapper

    def stats(self) -> Dict:
        """통계 반환"""
        return {
            "name": self.name,
            "total_requests": self.total_requests,
            "total_waits": self.total_waits,
            "current_tokens": self.tokens,
            "rate": self.rate,
            "burst_size": self.burst_size,
        }


# 전역 rate limiters (API별)
_limiters: Dict[str, RateLimiter] = {}


def get_limiter(name: str, requests_per_second: float = 1.0, burst_size: int = 5) -> RateLimiter:
    """
    이름으로 rate limiter 가져오기 (없으면 생성)

    Args:
        name: limiter 이름 (예: "youtube", "gemini", "costco")
        requests_per_second: 초당 요청 수
        burst_size: 버스트 크기

    Returns:
        RateLimiter 인스턴스
    """
    if name not in _limiters:
        _limiters[name] = RateLimiter(
            requests_per_second=requests_per_second,
            burst_size=burst_size,
            name=name
        )
    return _limiters[name]


# 사전 정의된 API limiters
YOUTUBE_LIMITER = get_limiter("youtube", requests_per_second=5, burst_size=10)
GEMINI_LIMITER = get_limiter("gemini", requests_per_second=1, burst_size=5)
SCRAPER_LIMITER = get_limiter("scraper", requests_per_second=0.5, burst_size=3)


def rate_limit(limiter_name: str, requests_per_second: float = 1.0):
    """
    Rate limiting 데코레이터 팩토리

    사용법:
        @rate_limit("youtube", requests_per_second=5)
        def youtube_api_call():
            pass

        @rate_limit("gemini")
        async def gemini_call():
            pass
    """
    def decorator(func):
        limiter = get_limiter(limiter_name, requests_per_second)

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                await limiter.wait_async()
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                limiter.wait()
                return func(*args, **kwargs)
            return sync_wrapper

    return decorator
