"""
꿀템장바구니 - 통합 데이터 파이프라인
YouTube 수집 → 자막 추출 → AI 분석 → 매장 매칭 → DB 저장

개선 버전:
- 타겟 채널 기반 수집 추가
- product_extractor, product_matcher 통합
- 출처(채널명) 추적
"""
import json
import time
from datetime import datetime

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

from youtube_crawler import YouTubeCrawler, TRANSCRIPT_AVAILABLE
from product_extractor import ProductExtractor
from product_matcher import ProductMatcher
from database import Database
from config import STORE_CATEGORIES, CRAWL_CONFIG


class DataPipeline:
    def __init__(self):
        self.youtube = None
        self.extractor = None
        self.matcher = None
        self.db = Database()

        self._init_apis()

    def _init_apis(self):
        """API 클라이언트 초기화"""
        try:
            self.youtube = YouTubeCrawler()
            print("[OK] YouTube API 연결됨")
        except ValueError as e:
            print(f"[!] YouTube API 미설정: {e}")

        try:
            self.extractor = ProductExtractor(provider="auto")
            print(f"[OK] AI 분석기 준비됨 ({self.extractor.provider})")
        except Exception as e:
            print(f"[!] AI API 미설정: {e}")

        try:
            self.matcher = ProductMatcher()
            print("[OK] 상품 매칭기 준비됨")
        except Exception as e:
            print(f"[!] 매칭기 초기화 실패: {e}")

    def run_full_pipeline(self, store_key: str = "daiso", max_videos: int = 10):
        """전체 파이프라인 실행"""
        if not self.youtube:
            print("[!] YouTube API 키가 필요합니다.")
            return

        if not self.extractor:
            print("[!] AI API 키가 필요합니다.")
            return

        store = STORE_CATEGORIES.get(store_key)
        if not store:
            print(f"[!] 알 수 없는 매장: {store_key}")
            return

        start_time = datetime.now()
        print(f"\n{'='*50}")
        print(f"파이프라인 시작: {store['name']}")
        print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        # Step 1: YouTube 영상 수집 (채널 + 키워드)
        print("\n[Step 1/5] YouTube 영상 수집...")
        videos = self.youtube.full_crawl(store_key)
        print(f"  -> {len(videos)}개 영상 수집됨")

        # DB에 영상 저장
        new_videos = 0
        for video in videos:
            if self.db.insert_video(video):
                new_videos += 1
        print(f"  -> {new_videos}개 신규 영상 저장")

        # Step 2: 자막 추출 (자막 없으면 설명으로 대체)
        print("\n[Step 2/5] 자막/설명 추출...")
        pending_videos = self.db.get_pending_videos(limit=max_videos)
        print(f"  -> {len(pending_videos)}개 영상 처리 대기")

        transcript_count = 0
        description_count = 0

        for video in tqdm(pending_videos, desc="  추출"):
            video_id = video["video_id"]
            transcript = None

            # 1. 자막 시도
            if TRANSCRIPT_AVAILABLE:
                transcript = self.youtube.get_video_transcript(video_id)
                if transcript:
                    transcript_count += 1

            # 2. 자막 없으면 제목 + 설명 사용
            if not transcript:
                title = video.get("title", "")
                description = video.get("description", "")
                if title or description:
                    # 제목과 설명을 합쳐서 분석용 텍스트 생성
                    transcript = f"{title}\n\n{description}"
                    description_count += 1

            if transcript and len(transcript.strip()) > 30:
                self.db.update_video_transcript(video_id, transcript)
            else:
                self.db.update_video_status(video_id, "no_transcript")

            time.sleep(0.3)  # API 속도 제한

        print(f"  -> 자막: {transcript_count}개, 설명 사용: {description_count}개")

        # Step 3: AI 분석
        print("\n[Step 3/5] AI 상품 추출...")
        transcribed_videos = self._get_transcribed_videos()
        all_products = []

        for video in tqdm(transcribed_videos, desc="  AI 분석"):
            video_id = video["video_id"]
            transcript = video.get("transcript", "")

            if not transcript:
                continue

            products = self.extractor.extract_products(transcript, store["name"])

            for product in products:
                product["video_id"] = video_id
                product["store_key"] = store_key
                product["store_name"] = store["name"]
                product["source_view_count"] = video.get("view_count", 0)
                product["channel_title"] = video.get("channel_title", "")
                all_products.append(product)

            self.db.update_video_status(video_id, "analyzed")
            time.sleep(1)  # AI API 속도 제한

        print(f"  -> {len(all_products)}개 상품 추출됨")

        # Step 4: 매장 매칭
        print("\n[Step 4/5] 매장 상품 매칭...")
        enriched_products = []
        matched_count = 0

        if self.matcher:
            for product in tqdm(all_products, desc="  매칭"):
                match = self.matcher.match_product(
                    product_name=product.get("name", ""),
                    price=product.get("price"),
                    category=product.get("category"),
                    keywords=product.get("keywords", [])
                )
                if match:
                    product["official"] = match
                    matched_count += 1
                else:
                    product["official"] = {}
                enriched_products.append(product)
            print(f"  -> {matched_count}/{len(enriched_products)}개 매칭 성공")
        else:
            enriched_products = all_products
            print(f"  -> 매장 매칭 스킵 (미지원)")

        # Step 5: DB 저장
        print("\n[Step 5/5] DB 저장...")
        saved_count = 0
        for product in enriched_products:
            self.db.insert_product(product)
            saved_count += 1
        print(f"  -> {saved_count}개 상품 저장됨")

        # 결과 요약
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        stats = self.db.get_stats()

        print(f"\n{'='*50}")
        print("파이프라인 완료!")
        print(f"{'='*50}")
        print(f"소요 시간: {elapsed:.1f}초")
        print(f"총 영상: {stats['total_videos']}")
        print(f"총 상품: {stats['total_products']}")
        print(f"승인 대기: {stats['pending_products']}")
        print(f"\n다음 단계: 관리자 대시보드에서 상품 승인")
        print(f"  -> streamlit run admin/dashboard.py")

        return {
            "videos_collected": len(videos),
            "products_extracted": len(all_products),
            "products_matched": matched_count,
            "elapsed_seconds": elapsed
        }

    def _get_transcribed_videos(self, limit: int = 20) -> list:
        """자막 추출 완료된 영상 조회"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM videos
            WHERE status = 'transcribed'
            ORDER BY view_count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def run_quick_test(self, store_key: str = "daiso"):
        """API 없이 테스트 데이터로 파이프라인 확인"""
        print("\n[테스트 모드] 샘플 데이터로 파이프라인 확인...")

        # 샘플 영상
        sample_video = {
            "video_id": "sample_001",
            "title": "[테스트] 다이소 꿀템 TOP 10",
            "channel_id": "UC_sample",
            "channel_title": "테스트 채널",
            "published_at": datetime.now().isoformat(),
            "thumbnail_url": "https://via.placeholder.com/320x180",
            "view_count": 500000,
            "store_key": store_key,
            "store_name": STORE_CATEGORIES[store_key]["name"],
        }
        self.db.insert_video(sample_video)

        # 샘플 상품들
        sample_products = [
            {
                "name": "스텐 배수구망",
                "price": 2000,
                "category": "주방",
                "reason": "물때가 안 껴서 관리가 편해요",
                "timestamp": 120,
                "keywords": ["배수구", "스텐", "주방"],
            },
            {
                "name": "실리콘 주방장갑",
                "price": 3000,
                "category": "주방",
                "reason": "세척이 쉽고 미끄럼 방지 기능",
                "timestamp": 240,
                "keywords": ["장갑", "실리콘", "주방"],
            },
            {
                "name": "다용도 정리함",
                "price": 5000,
                "category": "인테리어",
                "reason": "옷장 정리에 딱 좋아요",
                "timestamp": 360,
                "keywords": ["정리함", "수납", "인테리어"],
            },
        ]

        for product in sample_products:
            product["video_id"] = sample_video["video_id"]
            product["store_key"] = store_key
            product["store_name"] = sample_video["store_name"]
            product["source_view_count"] = sample_video["view_count"]
            product["official"] = {"matched": False}
            self.db.insert_product(product)

        stats = self.db.get_stats()
        print(f"\n[테스트 완료] 저장된 상품: {stats['total_products']}개")
        print(f"관리자 대시보드 실행: streamlit run admin/dashboard.py")


def main():
    pipeline = DataPipeline()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 테스트 모드
        pipeline.run_quick_test("daiso")
    else:
        # 실제 실행
        pipeline.run_full_pipeline("daiso", max_videos=10)


if __name__ == "__main__":
    main()
