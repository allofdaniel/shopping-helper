# -*- coding: utf-8 -*-
"""
크롤러 로깅 시스템
- 파일 및 콘솔 로깅
- 일별 로그 파일 관리
- 크롤링 통계 추적
"""
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json

# 로그 디렉토리 설정
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class CrawlerLogger:
    """크롤러 전용 로거"""

    _instance = None
    _loggers = {}

    def __new__(cls, name: str = "crawler"):
        """싱글톤 패턴 (이름별 인스턴스)"""
        if name not in cls._loggers:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._loggers[name] = instance
        return cls._loggers[name]

    def __init__(self, name: str = "crawler"):
        if self._initialized:
            return

        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # 기존 핸들러 제거

        # 콘솔 핸들러 (INFO 이상)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # 파일 핸들러 (DEBUG 포함 전체)
        log_filename = LOG_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)

        # 에러 전용 파일 핸들러
        error_filename = LOG_DIR / f"{name}_errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_filename, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        self.logger.addHandler(error_handler)

        self._initialized = True

        # 통계 파일
        self.stats_file = LOG_DIR / f"stats_{datetime.now().strftime('%Y%m%d')}.json"
        self._init_stats()

    def _init_stats(self):
        """통계 초기화"""
        if not self.stats_file.exists():
            self._save_stats({
                "date": datetime.now().strftime('%Y-%m-%d'),
                "stores": {},
                "total_products": 0,
                "total_errors": 0,
                "runs": [],
            })

    def _load_stats(self) -> Dict:
        """통계 로드"""
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "date": datetime.now().strftime('%Y-%m-%d'),
                "stores": {},
                "total_products": 0,
                "total_errors": 0,
                "runs": [],
            }

    def _save_stats(self, stats: Dict):
        """통계 저장"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        self.logger.error(message, exc_info=exc_info)

    def success(self, message: str):
        """성공 로그 (INFO 레벨)"""
        self.logger.info(f"[OK] {message}")

    def start_crawl(self, store: str, crawler_type: str = "catalog"):
        """크롤링 시작 로그"""
        self.info(f"{'='*60}")
        self.info(f"[{store.upper()}] {crawler_type} 크롤링 시작")
        self.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info(f"{'='*60}")

        return datetime.now()

    def end_crawl(self, store: str, start_time: datetime, stats: Dict):
        """크롤링 종료 로그 및 통계 저장"""
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        self.info(f"{'='*60}")
        self.info(f"[{store.upper()}] 크롤링 완료")
        self.info(f"소요 시간: {elapsed:.1f}초")
        self.info(f"수집: {stats.get('products_crawled', 0)}개")
        self.info(f"저장: {stats.get('products_saved', 0)}개")
        if stats.get('errors'):
            self.warning(f"에러: {len(stats['errors'])}건")
        self.info(f"{'='*60}")

        # 통계 업데이트
        daily_stats = self._load_stats()

        if store not in daily_stats["stores"]:
            daily_stats["stores"][store] = {
                "runs": 0,
                "products_crawled": 0,
                "products_saved": 0,
                "errors": 0,
            }

        store_stats = daily_stats["stores"][store]
        store_stats["runs"] += 1
        store_stats["products_crawled"] += stats.get("products_crawled", 0)
        store_stats["products_saved"] += stats.get("products_saved", 0)
        store_stats["errors"] += len(stats.get("errors", []))
        store_stats["last_run"] = end_time.strftime('%Y-%m-%d %H:%M:%S')

        daily_stats["total_products"] += stats.get("products_saved", 0)
        daily_stats["total_errors"] += len(stats.get("errors", []))

        daily_stats["runs"].append({
            "store": store,
            "start": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "end": end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "elapsed_seconds": elapsed,
            "products_crawled": stats.get("products_crawled", 0),
            "products_saved": stats.get("products_saved", 0),
            "errors": len(stats.get("errors", [])),
        })

        self._save_stats(daily_stats)

        return elapsed

    def log_product(self, store: str, product_name: str, price: int, extra: str = ""):
        """상품 로그 (DEBUG)"""
        extra_str = f" {extra}" if extra else ""
        self.debug(f"[{store}] {product_name}: {price:,}원{extra_str}")

    def log_error(self, store: str, operation: str, error: Exception):
        """에러 로그"""
        self.error(f"[{store}] {operation} 실패: {error}", exc_info=True)

        # 통계 업데이트
        daily_stats = self._load_stats()
        daily_stats["total_errors"] += 1
        self._save_stats(daily_stats)

    def get_daily_summary(self) -> Dict:
        """일일 통계 요약"""
        return self._load_stats()

    def print_daily_summary(self):
        """일일 통계 출력"""
        stats = self._load_stats()

        self.info(f"\n{'='*60}")
        self.info(f"[일일 통계] {stats['date']}")
        self.info(f"{'='*60}")

        for store, store_stats in stats.get("stores", {}).items():
            self.info(f"  {store}:")
            self.info(f"    실행: {store_stats['runs']}회")
            self.info(f"    수집: {store_stats['products_crawled']}개")
            self.info(f"    저장: {store_stats['products_saved']}개")
            if store_stats.get('errors', 0) > 0:
                self.info(f"    에러: {store_stats['errors']}건")

        self.info(f"\n  총 저장 상품: {stats['total_products']}개")
        self.info(f"  총 에러: {stats['total_errors']}건")
        self.info(f"{'='*60}")


def get_logger(name: str = "crawler") -> CrawlerLogger:
    """로거 인스턴스 가져오기"""
    return CrawlerLogger(name)


# 기본 로거
logger = get_logger()


def cleanup_old_logs(days: int = 7):
    """오래된 로그 파일 정리"""
    import time

    now = time.time()
    cutoff = now - (days * 86400)

    count = 0
    for log_file in LOG_DIR.glob("*.log"):
        if log_file.stat().st_mtime < cutoff:
            log_file.unlink()
            count += 1

    for stats_file in LOG_DIR.glob("stats_*.json"):
        if stats_file.stat().st_mtime < cutoff:
            stats_file.unlink()
            count += 1

    if count > 0:
        logger.info(f"{count}개의 오래된 로그 파일 삭제됨")


if __name__ == "__main__":
    # 테스트
    log = get_logger("test")

    log.info("테스트 정보 메시지")
    log.debug("테스트 디버그 메시지")
    log.warning("테스트 경고 메시지")
    log.error("테스트 에러 메시지")
    log.success("테스트 성공 메시지")

    # 크롤링 시뮬레이션
    start = log.start_crawl("daiso", "catalog")

    import time
    time.sleep(1)

    log.end_crawl("daiso", start, {
        "products_crawled": 100,
        "products_saved": 85,
        "errors": ["test error 1"],
    })

    log.print_daily_summary()
