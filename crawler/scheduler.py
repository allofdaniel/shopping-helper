# -*- coding: utf-8 -*-
"""
자동 수집 스케줄러
YouTube 영상 수집 및 상품 추출을 자동으로 실행합니다.

사용법:
1. 직접 실행: python scheduler.py
2. Windows 작업 스케줄러 등록
3. Linux cron 등록
"""
import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 경로 설정
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from config import CRAWL_CONFIG, STORE_CATEGORIES, DATA_DIR
from pipeline import DataPipeline


# 로깅 설정
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Scheduler:
    """자동 수집 스케줄러"""

    def __init__(self):
        self.status_file = DATA_DIR / "scheduler_status.json"
        self.load_status()

    def load_status(self):
        """상태 파일 로드"""
        if self.status_file.exists():
            with open(self.status_file, 'r', encoding='utf-8') as f:
                self.status = json.load(f)
        else:
            self.status = {
                "last_run": None,
                "last_store": None,
                "runs_today": 0,
                "total_runs": 0,
                "last_results": {}
            }

    def save_status(self):
        """상태 파일 저장"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(self.status, f, ensure_ascii=False, indent=2)

    def should_run(self) -> bool:
        """실행 필요 여부 체크"""
        if not self.status["last_run"]:
            return True

        last_run = datetime.fromisoformat(self.status["last_run"])
        interval_hours = CRAWL_CONFIG.get("check_interval_hours", 1)
        next_run = last_run + timedelta(hours=interval_hours)

        return datetime.now() >= next_run

    def run_collection(self, store_keys: list = None, max_videos: int = 30):
        """
        수집 실행

        Args:
            store_keys: 수집할 매장 키 리스트 (None이면 전체)
            max_videos: 매장당 최대 영상 수
        """
        if store_keys is None:
            store_keys = list(STORE_CATEGORIES.keys())

        logger.info(f"=== 수집 시작: {', '.join(store_keys)} ===")
        start_time = datetime.now()

        results = {
            "start_time": start_time.isoformat(),
            "stores": {},
            "errors": []
        }

        for store_key in store_keys:
            store_name = STORE_CATEGORIES[store_key]["name"]
            logger.info(f"\n[{store_name}] 수집 시작...")

            try:
                # 파이프라인 실행
                pipeline = DataPipeline()
                pipeline.run_full_pipeline(
                    store_key=store_key,
                    max_videos=max_videos
                )

                results["stores"][store_key] = {
                    "name": store_name,
                    "status": "completed"
                }

                logger.info(f"[{store_name}] 완료")

            except Exception as e:
                error_msg = f"{store_name}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"[{store_name}] 오류: {e}")

            # 매장 간 딜레이
            time.sleep(5)

        # 결과 저장
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        results["end_time"] = end_time.isoformat()
        results["duration_seconds"] = duration

        # 상태 업데이트
        self.status["last_run"] = end_time.isoformat()
        self.status["runs_today"] += 1
        self.status["total_runs"] += 1
        self.status["last_results"] = results
        self.save_status()

        logger.info(f"\n=== 수집 완료 ===")
        logger.info(f"소요 시간: {duration:.1f}초")
        logger.info(f"처리된 매장: {len(results['stores'])}개")

        if results["errors"]:
            logger.warning(f"오류 {len(results['errors'])}건: {results['errors']}")

        return results

    def run_once(self, store_keys: list = None):
        """한 번 실행"""
        if not self.should_run():
            last_run = datetime.fromisoformat(self.status["last_run"])
            interval = CRAWL_CONFIG.get("check_interval_hours", 1)
            next_run = last_run + timedelta(hours=interval)
            logger.info(f"아직 실행 시간 아님. 다음 실행: {next_run.strftime('%H:%M')}")
            return None

        return self.run_collection(store_keys)

    def run_daemon(self, store_keys: list = None, check_interval_minutes: int = 30):
        """
        데몬 모드로 실행 (계속 실행)

        Args:
            store_keys: 수집할 매장
            check_interval_minutes: 체크 주기 (분)
        """
        logger.info(f"스케줄러 데몬 시작 (체크 주기: {check_interval_minutes}분)")

        try:
            while True:
                if self.should_run():
                    self.run_collection(store_keys)

                # 다음 체크까지 대기
                logger.info(f"다음 체크까지 {check_interval_minutes}분 대기...")
                time.sleep(check_interval_minutes * 60)

        except KeyboardInterrupt:
            logger.info("스케줄러 종료됨")


def run_once(store_key: str = None):
    """단일 실행 (외부 호출용)"""
    scheduler = Scheduler()
    store_keys = [store_key] if store_key else None
    return scheduler.run_collection(store_keys)


def main():
    """CLI 실행"""
    import argparse

    parser = argparse.ArgumentParser(description='꿀템장바구니 자동 수집 스케줄러')
    parser.add_argument('--store', type=str, help='특정 매장만 수집 (daiso, costco, ikea, oliveyoung, convenience)')
    parser.add_argument('--daemon', action='store_true', help='데몬 모드로 계속 실행')
    parser.add_argument('--force', action='store_true', help='시간 체크 무시하고 강제 실행')
    parser.add_argument('--max-videos', type=int, default=30, help='매장당 최대 영상 수')

    args = parser.parse_args()

    scheduler = Scheduler()

    store_keys = [args.store] if args.store else None

    if args.daemon:
        scheduler.run_daemon(store_keys)
    elif args.force:
        scheduler.run_collection(store_keys, max_videos=args.max_videos)
    else:
        scheduler.run_once(store_keys)


if __name__ == "__main__":
    main()
