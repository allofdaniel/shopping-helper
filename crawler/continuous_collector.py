# -*- coding: utf-8 -*-
"""
실시간 YouTube 수집기 - Docker 컨테이너용
주기적으로 YouTube 영상을 수집하고 상품을 추출합니다.
"""
import os
import sys
import time
import logging
import sqlite3
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 경로 설정
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from youtube_scraper import YouTubeScraper, run_full_collection

# GitHub 동기화 (선택적)
try:
    from sync_to_github import main as sync_to_github
except ImportError:
    sync_to_github = None

# SmartExtractor는 선택적 (Gemini API 필요)
try:
    from improved_product_extractor import ImprovedProductExtractor as SmartExtractor
except ImportError:
    SmartExtractor = None

DB_PATH = BASE_DIR / 'data' / 'products.db'

# 수집 설정
COLLECTION_CONFIG = {
    'daiso': {
        'keywords': ['다이소 추천템', '다이소 신상', '다이소 꿀템', '다이소 하울', '다이소 정리'],
        'videos_per_keyword': 10,
        'interval_hours': 6,
    },
    'costco': {
        'keywords': ['코스트코 추천', '코스트코 장보기', '코스트코 하울', '코스트코 신상'],
        'videos_per_keyword': 10,
        'interval_hours': 6,
    },
    'ikea': {
        'keywords': ['이케아 추천', '이케아 꿀템', '이케아 수납', '이케아 인테리어'],
        'videos_per_keyword': 10,
        'interval_hours': 12,
    },
    'oliveyoung': {
        'keywords': ['올리브영 추천', '올리브영 하울', '올리브영 세일', '올리브영 스킨케어', '올리브영 베스트'],
        'videos_per_keyword': 15,
        'interval_hours': 4,
    },
    'traders': {
        'keywords': ['트레이더스 추천', '트레이더스 장보기', '이마트 트레이더스', '트레이더스 하울'],
        'videos_per_keyword': 15,
        'interval_hours': 6,
    },
    'convenience': {
        'keywords': ['편의점 신상', 'CU 추천', 'GS25 추천', '세븐일레븐 추천', '편의점 디저트', '편의점 먹방'],
        'videos_per_keyword': 15,
        'interval_hours': 4,
    },
}


class ContinuousCollector:
    """실시간 YouTube 수집기"""

    def __init__(self):
        self.scraper = YouTubeScraper()
        self.extractor = None
        self.last_collection: Dict[str, datetime] = {}
        self.stats = {
            'total_videos': 0,
            'total_products': 0,
            'runs': 0,
            'errors': 0,
        }

    def _init_extractor(self):
        """Extractor 초기화 (API 키 필요)"""
        if self.extractor is None and SmartExtractor is not None:
            api_key = os.environ.get('GEMINI_API_KEY')
            if api_key:
                try:
                    self.extractor = SmartExtractor(api_key)
                    logger.info("SmartExtractor initialized with Gemini API")
                except Exception as e:
                    logger.warning(f"SmartExtractor init failed: {e}")
            else:
                logger.warning("GEMINI_API_KEY not set - product extraction disabled")

    def collect_store(self, store_key: str) -> Dict:
        """특정 매장의 YouTube 데이터 수집"""
        config = COLLECTION_CONFIG.get(store_key)
        if not config:
            logger.error(f"Unknown store: {store_key}")
            return {'videos': 0, 'products': 0}

        logger.info(f"=== Collecting {store_key.upper()} ===")

        videos_collected = 0
        products_extracted = 0

        for keyword in config['keywords']:
            try:
                # 비디오 검색 및 수집
                videos = self.scraper.search_and_extract(
                    keyword,
                    limit=config['videos_per_keyword'],
                    get_details=True,
                    get_transcripts=False  # IP 차단 방지
                )

                if videos:
                    # DB에 저장
                    saved = self.scraper.save_to_db(videos, store_key)
                    videos_collected += saved
                    logger.info(f"  [{keyword}] {saved} videos saved")

                # Rate limiting
                time.sleep(2)

            except Exception as e:
                logger.error(f"  [{keyword}] Error: {e}")
                self.stats['errors'] += 1

        # 상품 추출 (Gemini API 사용 가능한 경우)
        self._init_extractor()
        if self.extractor:
            try:
                products_extracted = self._extract_products(store_key)
            except Exception as e:
                logger.error(f"Product extraction error: {e}")

        self.last_collection[store_key] = datetime.now()

        result = {
            'store': store_key,
            'videos': videos_collected,
            'products': products_extracted,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"=== {store_key.upper()} Complete: {videos_collected} videos, {products_extracted} products ===")
        return result

    def _extract_products(self, store_key: str) -> int:
        """수집된 비디오에서 상품 추출"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 처리 안된 비디오 조회
        cur.execute('''
            SELECT * FROM videos
            WHERE store_key = ?
            AND status = 'pending'
            AND description IS NOT NULL
            ORDER BY view_count DESC
            LIMIT 20
        ''', (store_key,))

        videos = cur.fetchall()
        products_added = 0

        for video in videos:
            try:
                # 설명에서 상품 추출
                text = f"{video['title']} {video['description']}"
                products = self.extractor.extract_products(text, store_key)

                for product in products:
                    # 중복 체크
                    cur.execute(
                        'SELECT id FROM products WHERE video_id=? AND name=?',
                        (video['video_id'], product.get('name'))
                    )
                    if cur.fetchone():
                        continue

                    cur.execute('''
                        INSERT INTO products
                        (video_id, name, price, category, store_key, store_name,
                         source_view_count, is_approved, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
                    ''', (
                        video['video_id'],
                        product.get('name'),
                        product.get('price'),
                        product.get('category'),
                        store_key,
                        self._get_store_name(store_key),
                        video['view_count']
                    ))
                    products_added += 1

                # 비디오 상태 업데이트
                cur.execute(
                    "UPDATE videos SET status='processed' WHERE video_id=?",
                    (video['video_id'],)
                )
                conn.commit()

            except Exception as e:
                logger.warning(f"Extract error for {video['video_id']}: {e}")

        conn.close()
        return products_added

    def _get_store_name(self, key: str) -> str:
        names = {
            'daiso': '다이소',
            'costco': 'Costco',
            'oliveyoung': '올리브영',
            'traders': '트레이더스',
            'ikea': 'IKEA',
            'convenience': '편의점',
        }
        return names.get(key, key)

    def collect_all(self):
        """모든 매장 수집"""
        logger.info("=" * 60)
        logger.info("STARTING FULL COLLECTION")
        logger.info("=" * 60)

        self.stats['runs'] += 1

        results = []
        for store_key in COLLECTION_CONFIG.keys():
            result = self.collect_store(store_key)
            results.append(result)
            self.stats['total_videos'] += result['videos']
            self.stats['total_products'] += result['products']
            time.sleep(5)  # 매장 간 딜레이

        logger.info("=" * 60)
        logger.info(f"COLLECTION COMPLETE - Run #{self.stats['runs']}")
        logger.info(f"  Total videos: {self.stats['total_videos']}")
        logger.info(f"  Total products: {self.stats['total_products']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info("=" * 60)

        return results

    def collect_missing_stores(self):
        """누락된 매장만 수집 (올리브영, 트레이더스, 편의점)"""
        missing_stores = ['oliveyoung', 'traders', 'convenience']

        logger.info("=" * 60)
        logger.info("COLLECTING MISSING STORES")
        logger.info("=" * 60)

        for store_key in missing_stores:
            self.collect_store(store_key)
            time.sleep(5)

    def run_scheduler(self):
        """스케줄러 실행 (각 매장별 다른 주기)"""
        logger.info("Starting scheduler...")

        # 각 매장별 스케줄 설정
        for store_key, config in COLLECTION_CONFIG.items():
            interval = config['interval_hours']
            schedule.every(interval).hours.do(self.collect_store, store_key)
            logger.info(f"  {store_key}: every {interval} hours")

        # GitHub 동기화 스케줄 (6시간마다)
        if sync_to_github:
            schedule.every(6).hours.do(sync_to_github)
            logger.info("  GitHub sync: every 6 hours")

        # 즉시 한 번 실행
        self.collect_all()

        # 첫 동기화 실행
        if sync_to_github:
            logger.info("Running initial GitHub sync...")
            try:
                sync_to_github()
            except Exception as e:
                logger.error(f"Initial sync failed: {e}")

        # 스케줄 루프
        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description='YouTube Continuous Collector')
    parser.add_argument('--mode', choices=['once', 'missing', 'schedule'],
                        default='once', help='실행 모드')
    parser.add_argument('--store', help='특정 매장만 수집')
    args = parser.parse_args()

    collector = ContinuousCollector()

    if args.store:
        collector.collect_store(args.store)
    elif args.mode == 'once':
        collector.collect_all()
    elif args.mode == 'missing':
        collector.collect_missing_stores()
    elif args.mode == 'schedule':
        collector.run_scheduler()


if __name__ == '__main__':
    main()
