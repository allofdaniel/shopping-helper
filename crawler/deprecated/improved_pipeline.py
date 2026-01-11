# -*- coding: utf-8 -*-
"""
개선된 데이터 파이프라인
- 자막 품질 검증 통합
- AI 추출 개선 (신뢰도, 부정 리뷰 필터)
- 매칭 로직 개선 (임계값 40점)
- 중복 방지
- 품질 메트릭 로깅
"""
import time
from datetime import datetime
from typing import Optional, List, Dict

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

from youtube_crawler import YouTubeCrawler, TRANSCRIPT_AVAILABLE
from transcript_validator import TranscriptValidator
from improved_product_extractor import ImprovedProductExtractor
from improved_product_matcher import ImprovedProductMatcher
from improved_database import ImprovedDatabase
from config import STORE_CATEGORIES, CRAWL_CONFIG

# 다이소 공식몰 연동 (옵션)
try:
    from daiso_enricher import DaisoEnricher
    DAISO_ENRICHER_AVAILABLE = True
except ImportError:
    DAISO_ENRICHER_AVAILABLE = False


class ImprovedDataPipeline:
    """개선된 데이터 파이프라인"""

    def __init__(self, use_improved_db: bool = True, use_daiso_enricher: bool = True):
        """
        Args:
            use_improved_db: True면 improved_database 사용
            use_daiso_enricher: True면 다이소 공식몰 연동 사용
        """
        self.youtube = None
        self.validator = TranscriptValidator()
        self.extractor = None
        self.matcher = None
        self.enricher = None
        self.db = ImprovedDatabase() if use_improved_db else None
        self.use_daiso_enricher = use_daiso_enricher and DAISO_ENRICHER_AVAILABLE

        self._init_apis()

    def _init_apis(self):
        """API 클라이언트 초기화"""
        try:
            self.youtube = YouTubeCrawler()
            print("[OK] YouTube API 연결됨")
        except ValueError as e:
            print(f"[!] YouTube API 미설정: {e}")

        try:
            self.extractor = ImprovedProductExtractor(provider="auto")
            print(f"[OK] AI 분석기 준비됨 ({self.extractor.provider})")
        except Exception as e:
            print(f"[!] AI API 미설정: {e}")

        try:
            self.matcher = ImprovedProductMatcher()
            # 카탈로그 로드
            if self.db:
                catalog = self.db.get_daiso_catalog_all()
                if catalog:
                    self.matcher.set_catalog(catalog)
                    print(f"[OK] 상품 매칭기 준비됨 (카탈로그: {len(catalog)}개)")
                else:
                    print("[!] 상품 카탈로그가 비어있습니다")
            else:
                print("[OK] 상품 매칭기 준비됨")
        except Exception as e:
            print(f"[!] 매칭기 초기화 실패: {e}")

    def run_full_pipeline(self, store_key: str = "daiso", max_videos: int = 10) -> Dict:
        """
        전체 파이프라인 실행

        Args:
            store_key: 매장 키 (daiso, costco, ikea 등)
            max_videos: 처리할 최대 영상 수

        Returns:
            실행 결과 통계
        """
        if not self.youtube:
            print("[!] YouTube API 키가 필요합니다.")
            return {"error": "YouTube API 키 없음"}

        if not self.extractor:
            print("[!] AI API 키가 필요합니다.")
            return {"error": "AI API 키 없음"}

        store = STORE_CATEGORIES.get(store_key)
        if not store:
            print(f"[!] 알 수 없는 매장: {store_key}")
            return {"error": f"알 수 없는 매장: {store_key}"}

        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"[개선된 파이프라인] {store['name']} 크롤링 시작")
        print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        stats = {
            "videos_collected": 0,
            "videos_with_transcript": 0,
            "products_extracted": 0,
            "products_matched": 0,
            "products_saved": 0,
            "duplicates_skipped": 0,
            "low_quality_skipped": 0,
            "errors": [],
        }

        # Step 1: YouTube 영상 수집
        print("\n[Step 1/6] YouTube 영상 수집...")
        try:
            videos = self.youtube.full_crawl(store_key)
            stats["videos_collected"] = len(videos)
            print(f"  -> {len(videos)}개 영상 수집됨")

            # DB에 영상 저장
            new_videos = 0
            for video in videos:
                if self.db.insert_video(video):
                    new_videos += 1
            print(f"  -> {new_videos}개 신규 영상 저장")
        except Exception as e:
            print(f"  [에러] 영상 수집 실패: {e}")
            stats["errors"].append(f"영상 수집: {e}")

        # Step 2: 자막 추출 및 검증
        print("\n[Step 2/6] 자막 추출 및 품질 검증...")
        pending_videos = self.db.get_pending_videos(limit=max_videos)
        print(f"  -> {len(pending_videos)}개 영상 처리 대기")

        valid_videos = []
        for video in tqdm(pending_videos, desc="  자막 추출"):
            video_id = video["video_id"]
            transcript = None
            quality_score = 0

            # 1. 자막 추출 시도
            if TRANSCRIPT_AVAILABLE:
                transcript = self.youtube.get_video_transcript(video_id)

            # 2. 자막 없으면 제목+설명 사용
            if not transcript:
                title = video.get("title", "")
                description = video.get("description", "")
                if title or description:
                    transcript = f"{title}\n\n{description}"

            # 3. 자막 품질 검증
            if transcript:
                validation = self.validator.validate(transcript, store["name"])

                if validation.is_valid:
                    quality_score = validation.quality_score
                    self.db.update_video_transcript(video_id, transcript, quality_score)
                    valid_videos.append({
                        **video,
                        "transcript": transcript,
                        "quality_score": quality_score,
                    })
                    stats["videos_with_transcript"] += 1
                else:
                    # 품질 미달
                    self.db.update_video_status(video_id, "low_quality")
                    stats["low_quality_skipped"] += 1
            else:
                self.db.update_video_status(video_id, "no_transcript")

            time.sleep(0.3)

        print(f"  -> 유효한 자막: {len(valid_videos)}개")
        print(f"  -> 품질 미달: {stats['low_quality_skipped']}개")

        # Step 3: AI 상품 추출
        print("\n[Step 3/6] AI 상품 추출...")
        all_products = []

        for video in tqdm(valid_videos, desc="  AI 분석"):
            video_id = video["video_id"]
            transcript = video.get("transcript", "")

            if not transcript:
                continue

            try:
                products = self.extractor.extract_products(transcript, store["name"])

                for product in products:
                    product["video_id"] = video_id
                    product["store_key"] = store_key
                    product["store_name"] = store["name"]
                    product["source_view_count"] = video.get("view_count", 0)
                    product["channel_title"] = video.get("channel_title", "")
                    all_products.append(product)

                self.db.update_video_status(video_id, "analyzed")

            except Exception as e:
                print(f"  [에러] AI 추출 실패 ({video_id}): {e}")
                stats["errors"].append(f"AI 추출 ({video_id}): {e}")

            time.sleep(1)  # API 속도 제한

        stats["products_extracted"] = len(all_products)
        print(f"  -> {len(all_products)}개 상품 추출됨")

        # Step 4: 매장 상품 매칭 (카탈로그 기반)
        print("\n[Step 4/6] 매장 상품 매칭 (카탈로그)...")
        enriched_products = []

        if self.matcher and self.matcher.catalog:
            for product in tqdm(all_products, desc="  매칭"):
                match = self.matcher.match(
                    product_name=product.get("name", ""),
                    price=product.get("price"),
                    category=product.get("category"),
                    keywords=product.get("keywords", []),
                )

                if match:
                    product["official"] = match.to_dict()
                    product["needs_manual_review"] = match.needs_manual_review
                    stats["products_matched"] += 1
                else:
                    product["official"] = {}
                    product["needs_manual_review"] = True  # 매칭 안 되면 수동 검토

                enriched_products.append(product)

            print(f"  -> {stats['products_matched']}/{len(enriched_products)}개 매칭 성공")
        else:
            enriched_products = all_products
            print(f"  -> 매장 매칭 스킵 (카탈로그 없음)")

        # Step 5: 다이소 공식몰 보강 (매칭 안 된 상품만)
        if self.use_daiso_enricher and store_key == "daiso":
            print("\n[Step 5/6] 다이소 공식몰 보강...")
            unmatched = [p for p in enriched_products if not p.get("official", {}).get("matched")]
            print(f"  -> {len(unmatched)}개 상품 공식몰 검색 대기")

            if unmatched:
                try:
                    import asyncio
                    enricher = DaisoEnricher(headless=True)

                    async def enrich_unmatched():
                        try:
                            results = await enricher.enrich_products(unmatched, delay=1.5)
                            return results
                        finally:
                            await enricher.close()

                    enriched_unmatched = asyncio.run(enrich_unmatched())

                    # 원본 목록 업데이트
                    unmatched_idx = 0
                    newly_matched = 0
                    for i, product in enumerate(enriched_products):
                        if not product.get("official", {}).get("matched"):
                            if unmatched_idx < len(enriched_unmatched):
                                enriched_products[i] = enriched_unmatched[unmatched_idx]
                                if enriched_products[i].get("is_matched"):
                                    newly_matched += 1
                                    stats["products_matched"] += 1
                                unmatched_idx += 1

                    print(f"  -> 공식몰에서 {newly_matched}개 추가 매칭")

                except Exception as e:
                    print(f"  [에러] 공식몰 보강 실패: {e}")
                    stats["errors"].append(f"공식몰 보강: {e}")
        else:
            print("\n[Step 5/6] 다이소 공식몰 보강... (스킵)")

        # Step 6: DB 저장 (중복 방지)
        print("\n[Step 6/6] DB 저장...")
        for product in enriched_products:
            result = self.db.insert_product(product)
            if result:
                stats["products_saved"] += 1
            else:
                stats["duplicates_skipped"] += 1

        print(f"  -> {stats['products_saved']}개 저장됨")
        print(f"  -> {stats['duplicates_skipped']}개 중복 스킵")

        # 결과 요약
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        stats["elapsed_seconds"] = elapsed

        # 품질 메트릭 로깅
        for video in valid_videos:
            video_products = [p for p in enriched_products if p.get("video_id") == video["video_id"]]
            matched = sum(1 for p in video_products if p.get("official", {}).get("matched"))
            avg_conf = sum(p.get("confidence", 0) for p in video_products) / max(len(video_products), 1)
            avg_match = sum(p.get("official", {}).get("confidence", 0) for p in video_products) / max(len(video_products), 1)

            self.db.log_quality_metrics(
                video_id=video["video_id"],
                transcript_length=len(video.get("transcript", "")),
                transcript_quality_score=video.get("quality_score", 0),
                products_extracted=len(video_products),
                products_matched=matched,
                avg_extraction_confidence=avg_conf,
                avg_match_confidence=avg_match,
                processing_time_sec=elapsed / max(len(valid_videos), 1),
            )

        print(f"\n{'='*60}")
        print("[개선된 파이프라인] 완료!")
        print(f"{'='*60}")
        print(f"소요 시간: {elapsed:.1f}초")
        print(f"수집 영상: {stats['videos_collected']}")
        print(f"유효 자막: {stats['videos_with_transcript']}")
        print(f"추출 상품: {stats['products_extracted']}")
        print(f"매칭 성공: {stats['products_matched']}")
        print(f"저장 완료: {stats['products_saved']}")
        print(f"중복 스킵: {stats['duplicates_skipped']}")

        if stats["errors"]:
            print(f"\n에러 발생: {len(stats['errors'])}건")
            for err in stats["errors"][:3]:
                print(f"  - {err}")

        # 전체 통계
        db_stats = self.db.get_stats()
        print(f"\n[DB 현황]")
        print(f"총 영상: {db_stats['total_videos']}")
        print(f"총 상품: {db_stats['total_products']}")
        print(f"승인 대기: {db_stats['pending_products']}")
        print(f"수동 검토 필요: {db_stats['needs_review']}")

        return stats

    def process_single_video(self, video_id: str, store_key: str = "daiso") -> Dict:
        """단일 영상 처리 (테스트용)"""
        store = STORE_CATEGORIES.get(store_key, {})

        print(f"\n[단일 영상 처리] {video_id}")

        # 1. 영상 정보 가져오기
        video = self.db.get_video_by_id(video_id)
        if not video:
            # YouTube에서 가져오기
            videos = self.youtube.search_videos(f"site:youtube.com/watch?v={video_id}", 1)
            if videos:
                video = videos[0]
                self.db.insert_video(video)
            else:
                return {"error": "영상을 찾을 수 없습니다"}

        # 2. 자막 추출
        transcript = None
        if TRANSCRIPT_AVAILABLE:
            transcript = self.youtube.get_video_transcript(video_id)
        if not transcript:
            transcript = f"{video.get('title', '')}\n\n{video.get('description', '')}"

        # 3. 자막 검증
        validation = self.validator.validate(transcript, store.get("name", "다이소"))
        print(f"자막 품질: {validation.quality_score} (유효: {validation.is_valid})")

        if not validation.is_valid:
            return {
                "error": "자막 품질 미달",
                "reason": validation.rejection_reason,
            }

        # 4. 상품 추출
        products = self.extractor.extract_products(transcript, store.get("name", "다이소"))
        print(f"추출된 상품: {len(products)}개")

        for p in products:
            print(f"  - {p['name']}: {p.get('price')}원 (신뢰도: {p.get('confidence')})")

        return {
            "video_id": video_id,
            "transcript_quality": validation.quality_score,
            "products": products,
        }


def main():
    """메인 실행"""
    import sys

    pipeline = ImprovedDataPipeline()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # 테스트 모드
            pipeline.run_full_pipeline("daiso", max_videos=3)
        elif sys.argv[1] == "--video":
            # 단일 영상 테스트
            video_id = sys.argv[2] if len(sys.argv) > 2 else "dQw4w9WgXcQ"
            pipeline.process_single_video(video_id)
    else:
        # 기본 실행
        pipeline.run_full_pipeline("daiso", max_videos=10)


if __name__ == "__main__":
    main()
