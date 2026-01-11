# -*- coding: utf-8 -*-
"""
기본 스크래퍼 클래스
- Playwright 기반 공통 기능
- 봇 탐지 우회
- 재시도 로직
- 표준화된 에러 핸들링
"""
import asyncio
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = Any
    Browser = Any
    BrowserContext = Any

try:
    from crawler_logger import get_logger
except ImportError:
    # 폴백 로거
    class FallbackLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def debug(self, msg): print(f"[DEBUG] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
        def error(self, msg, exc_info=False): print(f"[ERROR] {msg}")
        def success(self, msg): print(f"[OK] {msg}")
        def start_crawl(self, store, crawler_type): return datetime.now()
        def end_crawl(self, store, start, stats): pass
        def log_error(self, store, op, e): print(f"[ERROR] {store} {op}: {e}")

    def get_logger(name): return FallbackLogger()

try:
    from errors import (
        CrawlerError, NetworkError, BrowserError, TimeoutError,
        ErrorContext, ErrorAggregator, classify_error, get_error_aggregator
    )
except ImportError:
    # 에러 모듈 없을 경우 기본 동작
    CrawlerError = Exception
    NetworkError = Exception
    BrowserError = Exception
    TimeoutError = Exception
    ErrorContext = None
    ErrorAggregator = None
    classify_error = lambda e, c=None: e
    get_error_aggregator = lambda: None


T = TypeVar('T')


@dataclass
class ScraperConfig:
    """스크래퍼 설정"""
    headless: bool = True
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    locale: str = "ko-KR"
    max_retries: int = 3
    retry_delay: float = 2.0
    page_load_delay: float = 3.0
    anti_bot_delay_min: float = 1.0
    anti_bot_delay_max: float = 3.0


class BaseScraper(ABC, Generic[T]):
    """
    기본 스크래퍼 추상 클래스

    상속받아 사용:
    - store_name: 매장 이름
    - search_products(): 검색 구현
    - _parse_products(): 파싱 구현
    """

    store_name: str = "unknown"

    def __init__(self, config: ScraperConfig = None):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다. pip install playwright && playwright install chromium")

        self.config = config or ScraperConfig()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.logger = get_logger(self.store_name)
        self._is_initialized = False

        # 에러 집계기
        self.error_aggregator = get_error_aggregator() or ErrorAggregator() if ErrorAggregator else None

    async def _init_browser(self):
        """브라우저 초기화 (봇 탐지 우회 포함)"""
        if self._is_initialized and self.page:
            return

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            },
            user_agent=self.config.user_agent,
            locale=self.config.locale,
            timezone_id="Asia/Seoul",
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

        # 봇 탐지 우회 스크립트
        await self.context.add_init_script("""
            // webdriver 속성 숨기기
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // plugins 배열 채우기
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // languages 설정
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });

            // chrome 객체 추가
            window.chrome = { runtime: {} };

            // permissions 수정
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        self.page = await self.context.new_page()
        self._is_initialized = True

        self.logger.debug(f"브라우저 초기화 완료 (headless={self.config.headless})")

    async def _close_browser(self):
        """브라우저 종료"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            self.logger.debug(f"브라우저 종료 중 에러 (무시됨): {e}")
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self._is_initialized = False

    async def _random_delay(self, min_delay: float = None, max_delay: float = None):
        """랜덤 딜레이 (봇 탐지 우회)"""
        min_d = min_delay or self.config.anti_bot_delay_min
        max_d = max_delay or self.config.anti_bot_delay_max
        delay = random.uniform(min_d, max_d)
        await asyncio.sleep(delay)

    async def _goto_with_retry(self, url: str, wait_until: str = "domcontentloaded") -> bool:
        """
        페이지 이동 (재시도 포함)

        Returns:
            성공 여부
        """
        for attempt in range(self.config.max_retries):
            try:
                await self.page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=self.config.timeout
                )
                await asyncio.sleep(self.config.page_load_delay)
                return True

            except Exception as e:
                self.logger.warning(f"페이지 로드 실패 (시도 {attempt + 1}/{self.config.max_retries}): {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

                    # 브라우저 재시작 시도
                    if attempt >= 1:
                        self.logger.debug("브라우저 재시작 시도...")
                        await self._close_browser()
                        await self._init_browser()
                else:
                    self.logger.error(f"페이지 로드 최종 실패: {url}")
                    return False

        return False

    async def _handle_popup(self, selector: str, action: str = "click"):
        """팝업/쿠키 동의 처리"""
        try:
            element = await self.page.query_selector(selector)
            if element:
                if action == "click":
                    await element.click()
                await asyncio.sleep(1)
                self.logger.debug(f"팝업 처리 완료: {selector}")
                return True
        except Exception as e:
            self.logger.debug(f"팝업 처리 실패 (무시됨): {e}")
        return False

    async def _scroll_page(self, times: int = 3, delay: float = 1.0):
        """페이지 스크롤 (무한 스크롤 처리)"""
        for i in range(times):
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(delay)
            self.logger.debug(f"스크롤 {i + 1}/{times}")

    async def _wait_for_selector_safe(self, selector: str, timeout: int = None) -> bool:
        """안전한 셀렉터 대기"""
        try:
            await self.page.wait_for_selector(
                selector,
                timeout=timeout or self.config.timeout
            )
            return True
        except Exception:
            return False

    async def _evaluate_safe(self, script: str, default: Any = None) -> Any:
        """안전한 JavaScript 실행"""
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            self.logger.debug(f"JavaScript 실행 실패: {e}")
            return default

    @abstractmethod
    async def search_products(self, query: str, limit: int = 20) -> List[T]:
        """
        상품 검색 (하위 클래스에서 구현)

        Args:
            query: 검색어
            limit: 최대 결과 수

        Returns:
            상품 목록
        """
        pass

    async def search_products_with_retry(self, query: str, limit: int = 20) -> List[T]:
        """상품 검색 (재시도 포함, 표준화된 에러 핸들링)"""
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                return await self.search_products(query, limit)
            except Exception as e:
                self.logger.warning(f"검색 실패 '{query}' (시도 {attempt + 1}/{self.config.max_retries}): {e}")

                # 에러 분류 및 집계
                if ErrorContext:
                    ctx = ErrorContext(store=self.store_name, operation="search", query=query)
                    classified = classify_error(e, ctx)
                    last_error = classified

                    # 집계기에 추가
                    if self.error_aggregator:
                        self.error_aggregator.add(classified)

                    # 재시도 불가능한 에러면 즉시 종료
                    if not classified.retryable:
                        self.logger.error(f"재시도 불가능한 에러: {classified}")
                        return []

                if attempt < self.config.max_retries - 1:
                    # 지수 백오프
                    delay = self.config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    self.logger.log_error(self.store_name, f"검색 '{query}'", e)
                    return []

        return []

    def get_error_summary(self) -> Dict[str, Any]:
        """에러 요약 조회"""
        if self.error_aggregator:
            return self.error_aggregator.summary()
        return {"total": 0}

    async def close(self):
        """리소스 정리"""
        await self._close_browser()
        self.logger.debug("스크래퍼 종료")

    async def __aenter__(self):
        """async with 지원"""
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async with 지원"""
        await self.close()


class BaseEventScraper(BaseScraper[T]):
    """
    이벤트 상품 스크래퍼 (편의점용)

    search_products 대신 get_event_products 사용
    """

    @abstractmethod
    async def get_event_products(self, event_type: str = "1+1", limit: int = 30) -> List[T]:
        """
        이벤트 상품 조회

        Args:
            event_type: 이벤트 타입 (1+1, 2+1 등)
            limit: 최대 결과 수

        Returns:
            상품 목록
        """
        pass

    async def search_products(self, query: str, limit: int = 20) -> List[T]:
        """이벤트 스크래퍼는 검색 대신 이벤트 조회"""
        return await self.get_event_products(query, limit)


if __name__ == "__main__":
    # 테스트용 간단한 구현
    class TestScraper(BaseScraper[dict]):
        store_name = "test"

        async def search_products(self, query: str, limit: int = 20) -> List[dict]:
            await self._init_browser()
            await self._goto_with_retry("https://www.google.com")
            title = await self.page.title()
            return [{"title": title, "query": query}]

    async def test():
        async with TestScraper() as scraper:
            results = await scraper.search_products("test")
            print(results)

    asyncio.run(test())
