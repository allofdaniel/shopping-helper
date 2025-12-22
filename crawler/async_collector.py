# -*- coding: utf-8 -*-
"""
비동기 고성능 수집기
병렬 처리로 수집 속도를 최적화합니다.
"""
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Callable

from database import Database
from youtube_crawler import YouTubeCrawler, TRANSCRIPT_AVAILABLE
from product_extractor import ProductExtractor
from product_matcher import ProductMatcher
from sns_crawler import SNSCollector, SocialPost
from config import STORE_CATEGORIES


class AsyncCollector:
    """
    비동기 수집기

    최적화 전략:
    1. YouTube API 호출: 병렬 처리 (ThreadPoolExecutor)
    2. 자막 추출: 비동기 배치
    3. AI 추출: Rate limiting과 함께 병렬
    4. DB 저장: 배치 삽입
    """

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.db = Database()
        self.youtube = None
        self.extractor = None
        self.matcher = None

        # 통계
        self.stats = {
            "videos_collected": 0,
            "transcripts_extracted": 0,
            "products_extracted": 0,
            "products_matched": 0,
            "errors": 0,
            "start_time": None,
        }

    def _init_components(self):
        """컴포넌트 지연 초기화"""
        if self.youtube is None:
            try:
                self.youtube = YouTubeCrawler()
            except Exception as e:
                print(f"YouTube 초기화 실패: {e}")

        if self.extractor is None:
            try:
                self.extractor = ProductExtractor(provider="auto")
            except Exception as e:
                print(f"AI 추출기 초기화 실패: {e}")

        if self.matcher is None:
            try:
                self.matcher = ProductMatcher()
            except Exception as e:
                print(f"매칭기 초기화 실패: {e}")

    async def collect_all_sources(self, store_key: str = "daiso",
                                   max_videos: int = 20,
                                   include_sns: bool = False) -> dict:
        """
        모든 소스에서 병렬 수집

        Args:
            store_key: 매장 키
            max_videos: 최대 영상 수
            include_sns: SNS 수집 포함 여부

        Returns:
            수집 결과 통계
        """
        self.stats["start_time"] = datetime.now()
        self._init_components()

        print(f"\n{'='*60}")
        print(f"비동기 수집 시작: {STORE_CATEGORIES.get(store_key, {}).get('name', store_key)}")
        print(f"{'='*60}")

        # 1. YouTube 영상 수집 (병렬)
        print("\n[1/4] YouTube 영상 수집...")
        videos = await self._collect_youtube_parallel(store_key, max_videos)

        # 2. 자막 추출 (병렬)
        print("\n[2/4] 자막 추출...")
        transcripts = await self._extract_transcripts_parallel(videos)

        # 3. AI 상품 추출 (Rate limited 병렬)
        print("\n[3/4] AI 상품 추출...")
        products = await self._extract_products_parallel(transcripts, store_key)

        # 4. 매칭 및 저장 (병렬)
        print("\n[4/4] 매칭 및 저장...")
        matched = await self._match_and_save_parallel(products)

        # 5. SNS 수집 (선택)
        if include_sns:
            print("\n[추가] SNS 수집...")
            await self._collect_sns(store_key)

        # 결과 출력
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
        self.stats["elapsed_seconds"] = elapsed

        print(f"\n{'='*60}")
        print("수집 완료!")
        print(f"{'='*60}")
        print(f"소요 시간: {elapsed:.1f}초")
        print(f"수집 영상: {self.stats['videos_collected']}개")
        print(f"추출 자막: {self.stats['transcripts_extracted']}개")
        print(f"추출 상품: {self.stats['products_extracted']}개")
        print(f"매칭 성공: {self.stats['products_matched']}개")
        print(f"오류: {self.stats['errors']}개")

        return self.stats

    async def _collect_youtube_parallel(self, store_key: str, max_videos: int) -> list:
        """YouTube 영상 병렬 수집"""
        if not self.youtube:
            return []

        loop = asyncio.get_event_loop()

        # ThreadPoolExecutor로 동기 API 비동기 실행
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 채널 + 키워드 수집을 병렬로
            channel_future = loop.run_in_executor(
                executor,
                self.youtube.crawl_target_channels,
                store_key
            )
            keyword_future = loop.run_in_executor(
                executor,
                self.youtube.crawl_search_keywords,
                store_key
            )

            channel_videos, keyword_videos = await asyncio.gather(
                channel_future, keyword_future, return_exceptions=True
            )

        # 결과 병합
        all_videos = []
        seen_ids = set()

        for videos in [channel_videos, keyword_videos]:
            if isinstance(videos, Exception):
                self.stats["errors"] += 1
                continue
            for v in videos:
                if v["video_id"] not in seen_ids:
                    all_videos.append(v)
                    seen_ids.add(v["video_id"])
                    # DB 저장
                    self.db.insert_video(v)

        self.stats["videos_collected"] = len(all_videos)
        print(f"  -> {len(all_videos)}개 영상 수집됨")

        return all_videos[:max_videos]

    async def _extract_transcripts_parallel(self, videos: list) -> list:
        """자막 병렬 추출"""
        if not TRANSCRIPT_AVAILABLE or not self.youtube:
            print("  -> 자막 추출 스킵 (라이브러리 미설치)")
            return videos

        loop = asyncio.get_event_loop()
        results = []

        # 배치로 처리 (5개씩)
        batch_size = 5
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i+batch_size]

            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = []
                for video in batch:
                    future = loop.run_in_executor(
                        executor,
                        self.youtube.get_video_transcript,
                        video["video_id"]
                    )
                    futures.append((video, future))

                for video, future in futures:
                    try:
                        transcript = await future
                        if transcript:
                            video["transcript"] = transcript
                            self.db.update_video_transcript(video["video_id"], transcript)
                            self.stats["transcripts_extracted"] += 1
                        results.append(video)
                    except Exception as e:
                        self.stats["errors"] += 1
                        results.append(video)

            # Rate limiting
            await asyncio.sleep(1)

        print(f"  -> {self.stats['transcripts_extracted']}개 자막 추출됨")
        return results

    async def _extract_products_parallel(self, videos: list, store_key: str) -> list:
        """AI 상품 추출 (Rate limited)"""
        if not self.extractor:
            return []

        store_name = STORE_CATEGORIES.get(store_key, {}).get("name", store_key)
        all_products = []

        # 자막 있는 영상만 처리
        videos_with_transcript = [v for v in videos if v.get("transcript")]

        loop = asyncio.get_event_loop()

        # 순차 처리 (AI API rate limit 때문)
        for video in videos_with_transcript:
            try:
                # ThreadPool에서 실행
                with ThreadPoolExecutor(max_workers=1) as executor:
                    products = await loop.run_in_executor(
                        executor,
                        self.extractor.extract_products,
                        video["transcript"],
                        store_name
                    )

                for product in products:
                    product["video_id"] = video["video_id"]
                    product["store_key"] = store_key
                    product["store_name"] = store_name
                    product["source_view_count"] = video.get("view_count", 0)
                    product["channel_title"] = video.get("channel_title", "")
                    all_products.append(product)

                self.stats["products_extracted"] += len(products)

            except Exception as e:
                self.stats["errors"] += 1

            # AI API Rate limiting (1초 대기)
            await asyncio.sleep(1)

        print(f"  -> {self.stats['products_extracted']}개 상품 추출됨")
        return all_products

    async def _match_and_save_parallel(self, products: list) -> list:
        """매칭 및 저장 (병렬)"""
        if not self.matcher:
            # 매칭 없이 저장만
            for product in products:
                self.db.insert_product(product)
            return products

        loop = asyncio.get_event_loop()
        matched_products = []

        # 배치로 처리
        batch_size = 10
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]

            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = []
                for product in batch:
                    future = loop.run_in_executor(
                        executor,
                        self.matcher.match_product,
                        product.get("name", ""),
                        product.get("price"),
                        product.get("category"),
                        product.get("keywords", [])
                    )
                    futures.append((product, future))

                for product, future in futures:
                    try:
                        match = await future
                        if match:
                            product["official"] = match
                            self.stats["products_matched"] += 1
                        else:
                            product["official"] = {}

                        self.db.insert_product(product)
                        matched_products.append(product)

                    except Exception as e:
                        self.stats["errors"] += 1

        print(f"  -> {self.stats['products_matched']}/{len(products)}개 매칭됨")
        return matched_products

    async def _collect_sns(self, store_key: str):
        """SNS 수집"""
        # SNS 수집은 별도 API 키 필요
        print("  -> SNS 수집은 API 키 설정 필요")

    def close(self):
        """리소스 해제"""
        self.db.close()
        if self.matcher:
            self.matcher.close()


def run_async_collection(store_key: str = "daiso", max_videos: int = 20):
    """비동기 수집 실행 (편의 함수)"""
    collector = AsyncCollector()
    try:
        result = asyncio.run(
            collector.collect_all_sources(store_key, max_videos)
        )
        return result
    finally:
        collector.close()


if __name__ == "__main__":
    import sys

    store_key = sys.argv[1] if len(sys.argv) > 1 else "daiso"
    max_videos = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    run_async_collection(store_key, max_videos)
