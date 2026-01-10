# -*- coding: utf-8 -*-
"""
꿀템장바구니 - 무제한 데이터 파이프라인 (yt-dlp 기반)
YouTube API 쿼터 제한 없이 대량 수집 가능

사용법:
    # 기본 실행 (다이소, 각 채널 20개 영상)
    python unlimited_pipeline.py

    # 특정 매장
    python unlimited_pipeline.py --store costco

    # 모든 매장 수집
    python unlimited_pipeline.py --all

    # 서버 데몬 모드 (주기적 실행)
    python unlimited_pipeline.py --daemon --interval 3600

    # 카탈로그만 크롤링 (다이소몰)
    python unlimited_pipeline.py --catalog-only
"""
import argparse
import asyncio
import time
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

from ytdlp_crawler import YTDLPCrawler, YTDLP_AVAILABLE
from transcript_validator import TranscriptValidator
from improved_product_extractor import ImprovedProductExtractor
from improved_product_matcher import ImprovedProductMatcher
from improved_database import ImprovedDatabase
from config import STORE_CATEGORIES, CRAWL_CONFIG

# 카탈로그 크롤러
try:
    from daiso_mall_scraper import DaisoMallScraper, PLAYWRIGHT_AVAILABLE
    CATALOG_CRAWLER_AVAILABLE = PLAYWRIGHT_AVAILABLE
except ImportError:
    CATALOG_CRAWLER_AVAILABLE = False

# 코스트코 크롤러
try:
    from costco_scraper import CostcoScraper, COSTCO_SEARCH_KEYWORDS
    COSTCO_SCRAPER_AVAILABLE = True
except ImportError:
    COSTCO_SCRAPER_AVAILABLE = False

# 올리브영 크롤러
try:
    from oliveyoung_scraper import OliveyoungScraper, OLIVEYOUNG_SEARCH_KEYWORDS
    OLIVEYOUNG_SCRAPER_AVAILABLE = True
except ImportError:
    OLIVEYOUNG_SCRAPER_AVAILABLE = False

# 쿠팡 크롤러
try:
    from coupang_scraper import CoupangScraper, COUPANG_SEARCH_KEYWORDS
    COUPANG_SCRAPER_AVAILABLE = True
except ImportError:
    COUPANG_SCRAPER_AVAILABLE = False

# 카탈로그 크롤링 설정
CATALOG_CONFIG = {
    "daiso": {
        "enabled": True,
        "crawler_class": "DaisoMallScraper",
        "categories": [
            "생활용품", "주방용품", "욕실용품", "청소용품",
            "수납정리", "인테리어", "문구팬시", "파티용품",
        ],
        "keywords": [
            "실리콘", "수세미", "배수구", "정리함", "밀폐용기",
            "행거", "후크", "수납", "바구니", "트레이",
        ],
        "update_interval_hours": 24,  # 카탈로그 업데이트 주기
    },
    "costco": {
        "enabled": True,
        "crawler_class": "CostcoScraper",
        "keywords": [
            "과자", "스낵", "견과류", "초콜릿", "커피",
            "음료", "생수", "주스", "차", "우유",
            "고기", "소고기", "돼지고기", "닭고기", "해산물",
            "과일", "채소", "샐러드", "냉동식품", "피자",
            "라면", "즉석밥", "통조림", "소스", "조미료",
            "세제", "화장지", "청소용품", "주방용품", "생활용품",
        ],
        "categories": [
            "/c/SpecialPriceOffers",  # 스페셜 할인
            "/c/BuyersPick",  # Buyer's Pick
        ],
        "update_interval_hours": 24,
    },
    "oliveyoung": {
        "enabled": True,
        "crawler_class": "OliveyoungScraper",
        "keywords": [
            "선크림", "클렌징", "토너", "에센스", "크림",
            "마스크팩", "립스틱", "파운데이션", "쿠션", "아이라이너",
            "샴푸", "트리트먼트", "바디로션", "핸드크림", "향수",
            "비타민", "영양제", "다이어트", "건강식품", "유산균",
        ],
        "categories": [],
        "update_interval_hours": 24,
    },
    "coupang": {
        "enabled": True,
        "crawler_class": "CoupangScraper",
        "keywords": [
            "생활용품", "주방용품", "욕실용품", "청소용품", "수납정리",
            "식품", "과자", "음료", "라면", "즉석식품",
            "건강식품", "비타민", "유산균", "다이어트",
            "화장품", "스킨케어", "메이크업",
        ],
        "categories": [],
        "update_interval_hours": 24,
    },
}


class UnlimitedPipeline:
    """무제한 데이터 파이프라인 (yt-dlp 기반)"""

    def __init__(self, use_daiso_enricher: bool = False):
        """
        Args:
            use_daiso_enricher: 다이소 공식몰 연동 (느림, 선택적)
        """
        if not YTDLP_AVAILABLE:
            raise ImportError("yt-dlp가 필요합니다. pip install yt-dlp")

        self.db = ImprovedDatabase()

        # yt-dlp 크롤러에 DB 연결 (중복 체크용)
        self.crawler = YTDLPCrawler(db=self.db)
        self.validator = TranscriptValidator()
        self.extractor = None
        self.matcher = None
        self.use_daiso_enricher = use_daiso_enricher

        self._init_ai()

    def _init_ai(self):
        """AI 분석기 초기화"""
        try:
            self.extractor = ImprovedProductExtractor(provider="auto")
            print(f"[OK] AI 분석기 준비됨 ({self.extractor.provider})")
        except Exception as e:
            print(f"[!] AI API 미설정: {e}")
            print("    GEMINI_API_KEY 또는 OPENAI_API_KEY 환경변수 필요")

        try:
            self.matcher = ImprovedProductMatcher()
            catalog = self.db.get_daiso_catalog_all()
            if catalog:
                self.matcher.set_catalog(catalog)
                print(f"[OK] 상품 매칭기 준비됨 (카탈로그: {len(catalog)}개)")
            else:
                print("[!] 카탈로그 없음 - 매칭 스킵됨")
                if CATALOG_CRAWLER_AVAILABLE:
                    print("    -> 'python unlimited_pipeline.py --catalog-only' 로 카탈로그 수집 필요")
        except Exception as e:
            print(f"[!] 매칭기 초기화 실패: {e}")

    async def crawl_catalog_async(self, store_key: str = "daiso") -> Dict:
        """
        매장 카탈로그 크롤링 (비동기)

        Args:
            store_key: 매장 키

        Returns:
            크롤링 결과 통계
        """
        if not CATALOG_CRAWLER_AVAILABLE:
            return {"error": "Playwright가 설치되어 있지 않습니다"}

        if store_key not in CATALOG_CONFIG:
            return {"error": f"지원하지 않는 매장: {store_key}"}

        config = CATALOG_CONFIG[store_key]
        if not config.get("enabled"):
            return {"error": f"{store_key} 카탈로그 크롤링 비활성화"}

        print(f"\n{'='*60}")
        print(f"[카탈로그 크롤링] {store_key} 시작")
        print(f"{'='*60}")

        stats = {
            "store": store_key,
            "products_crawled": 0,
            "products_saved": 0,
            "errors": [],
        }

        if store_key == "daiso":
            from daiso_mall_scraper import DaisoMallScraper

            scraper = DaisoMallScraper(headless=True)

            try:
                all_products = []

                # 키워드별 검색
                keywords = config.get("keywords", [])
                print(f"\n검색 키워드: {len(keywords)}개")

                for keyword in keywords:
                    print(f"  검색: '{keyword}'")
                    try:
                        products = await scraper.search_products(keyword, limit=30)
                        stats["products_crawled"] += len(products)

                        for p in products:
                            all_products.append(p)
                            print(f"    - {p.name}: {p.price}원 (품번: {p.product_no})")

                    except Exception as e:
                        print(f"    [에러] {e}")
                        stats["errors"].append(f"{keyword}: {e}")

                    await asyncio.sleep(2)  # 사이트 부하 방지

                # 카테고리별 검색
                categories = config.get("categories", [])
                print(f"\n카테고리 검색: {len(categories)}개")

                for category in categories:
                    print(f"  카테고리: '{category}'")
                    try:
                        products = await scraper.search_products(category, limit=50)
                        stats["products_crawled"] += len(products)

                        for p in products:
                            all_products.append(p)

                    except Exception as e:
                        print(f"    [에러] {e}")
                        stats["errors"].append(f"{category}: {e}")

                    await asyncio.sleep(2)

                # 중복 제거 및 DB 저장
                seen_product_nos = set()
                for p in all_products:
                    if p.product_no not in seen_product_nos:
                        seen_product_nos.add(p.product_no)
                        product_dict = {
                            "product_no": p.product_no,
                            "name": p.name,
                            "price": p.price,
                            "image_url": p.image_url,
                            "product_url": p.product_url,
                            "category": p.category,
                        }
                        if self.db.insert_daiso_product(product_dict):
                            stats["products_saved"] += 1

                print(f"\n크롤링 완료: {stats['products_crawled']}개 수집, "
                      f"{stats['products_saved']}개 저장 (중복 제외)")

                # 매처 카탈로그 새로고침
                catalog = self.db.get_daiso_catalog_all()
                if catalog and self.matcher:
                    self.matcher.set_catalog(catalog)
                    print(f"매칭기 카탈로그 업데이트: {len(catalog)}개")

            finally:
                await scraper.close()

        elif store_key == "costco":
            if not COSTCO_SCRAPER_AVAILABLE:
                return {"error": "코스트코 스크래퍼를 불러올 수 없습니다"}

            from costco_scraper import CostcoScraper

            scraper = CostcoScraper(headless=True)

            try:
                all_products = []

                # 키워드별 검색
                keywords = config.get("keywords", [])
                print(f"\n검색 키워드: {len(keywords)}개")

                for keyword in keywords:
                    print(f"  검색: '{keyword}'")
                    try:
                        products = await scraper.search_products(keyword, limit=20)
                        stats["products_crawled"] += len(products)

                        for p in products:
                            all_products.append(p)
                            print(f"    - {p.name}: {p.price:,}원 (코드: {p.product_code})")

                    except Exception as e:
                        print(f"    [에러] {e}")
                        stats["errors"].append(f"{keyword}: {e}")

                    await asyncio.sleep(2)  # 사이트 부하 방지

                # 카테고리별 검색
                categories = config.get("categories", [])
                print(f"\n카테고리 검색: {len(categories)}개")

                for category in categories:
                    print(f"  카테고리: '{category}'")
                    try:
                        products = await scraper.get_category_products(category, limit=50)
                        stats["products_crawled"] += len(products)

                        for p in products:
                            all_products.append(p)

                    except Exception as e:
                        print(f"    [에러] {e}")
                        stats["errors"].append(f"{category}: {e}")

                    await asyncio.sleep(2)

                # 중복 제거 및 DB 저장
                seen_codes = set()
                for p in all_products:
                    if p.product_code not in seen_codes:
                        seen_codes.add(p.product_code)
                        product_dict = {
                            "product_code": p.product_code,
                            "name": p.name,
                            "price": p.price,
                            "image_url": p.image_url,
                            "product_url": p.product_url,
                            "category": p.category,
                            "unit_price": p.unit_price,
                            "rating": p.rating,
                            "review_count": p.review_count,
                        }
                        if self.db.insert_costco_product(product_dict):
                            stats["products_saved"] += 1

                print(f"\n크롤링 완료: {stats['products_crawled']}개 수집, "
                      f"{stats['products_saved']}개 저장 (중복 제외)")

            finally:
                await scraper.close()

        elif store_key == "oliveyoung":
            if not OLIVEYOUNG_SCRAPER_AVAILABLE:
                return {"error": "올리브영 스크래퍼를 불러올 수 없습니다"}

            from oliveyoung_scraper import OliveyoungScraper

            scraper = OliveyoungScraper(headless=True)

            try:
                all_products = []

                # 키워드별 검색
                keywords = config.get("keywords", [])
                print(f"\n검색 키워드: {len(keywords)}개")

                for keyword in keywords:
                    print(f"  검색: '{keyword}'")
                    try:
                        products = await scraper.search_products(keyword, limit=20)
                        stats["products_crawled"] += len(products)

                        for p in products:
                            all_products.append(p)
                            print(f"    - [{p.brand}] {p.name}: {p.price:,}원")

                    except Exception as e:
                        print(f"    [에러] {e}")
                        stats["errors"].append(f"{keyword}: {e}")

                    await asyncio.sleep(3)  # 봇 탐지 방지를 위한 더 긴 딜레이

                # 중복 제거 및 DB 저장
                seen_codes = set()
                for p in all_products:
                    if p.product_code not in seen_codes:
                        seen_codes.add(p.product_code)
                        product_dict = {
                            "product_code": p.product_code,
                            "name": p.name,
                            "brand": p.brand,
                            "price": p.price,
                            "original_price": p.original_price,
                            "image_url": p.image_url,
                            "product_url": p.product_url,
                            "rating": p.rating,
                            "review_count": p.review_count,
                            "is_best": p.is_best,
                            "is_sale": p.is_sale,
                        }
                        if self.db.insert_oliveyoung_product(product_dict):
                            stats["products_saved"] += 1

                print(f"\n크롤링 완료: {stats['products_crawled']}개 수집, "
                      f"{stats['products_saved']}개 저장 (중복 제외)")

            finally:
                await scraper.close()

        elif store_key == "coupang":
            if not COUPANG_SCRAPER_AVAILABLE:
                return {"error": "쿠팡 스크래퍼를 불러올 수 없습니다"}

            from coupang_scraper import CoupangScraper

            scraper = CoupangScraper(headless=True)

            try:
                all_products = []

                # 키워드별 검색
                keywords = config.get("keywords", [])
                print(f"\n검색 키워드: {len(keywords)}개")

                for keyword in keywords:
                    print(f"  검색: '{keyword}'")
                    try:
                        products = await scraper.search_products(keyword, limit=20)
                        stats["products_crawled"] += len(products)

                        for p in products:
                            all_products.append(p)
                            rocket = "🚀" if p.is_rocket else ""
                            print(f"    - {p.name}: {p.price:,}원 {rocket}")

                    except Exception as e:
                        print(f"    [에러] {e}")
                        stats["errors"].append(f"{keyword}: {e}")

                    await asyncio.sleep(5)  # 쿠팡은 봇 탐지가 강해서 더 긴 딜레이

                # 중복 제거 및 DB 저장
                seen_ids = set()
                for p in all_products:
                    if p.product_id not in seen_ids:
                        seen_ids.add(p.product_id)
                        product_dict = {
                            "product_id": p.product_id,
                            "name": p.name,
                            "price": p.price,
                            "original_price": p.original_price,
                            "image_url": p.image_url,
                            "product_url": p.product_url,
                            "rating": p.rating,
                            "review_count": p.review_count,
                            "is_rocket": p.is_rocket,
                            "is_rocket_fresh": p.is_rocket_fresh,
                            "seller": p.seller,
                        }
                        if self.db.insert_coupang_product(product_dict):
                            stats["products_saved"] += 1

                print(f"\n크롤링 완료: {stats['products_crawled']}개 수집, "
                      f"{stats['products_saved']}개 저장 (중복 제외)")

            finally:
                await scraper.close()

        return stats

    def crawl_catalog(self, store_key: str = "daiso") -> Dict:
        """카탈로그 크롤링 (동기 wrapper)"""
        return asyncio.run(self.crawl_catalog_async(store_key))

    def run(self, store_key: str = "daiso", max_videos: int = 50,
            max_per_channel: int = 20, max_per_search: int = 10,
            skip_existing: bool = True) -> Dict:
        """
        파이프라인 실행

        Args:
            store_key: 매장 키
            max_videos: 처리할 최대 영상 수
            max_per_channel: 채널당 최대 영상 수
            max_per_search: 검색어당 최대 영상 수
            skip_existing: 이미 처리된 영상 스킵

        Returns:
            실행 통계
        """
        store = STORE_CATEGORIES.get(store_key)
        if not store:
            print(f"[!] 알 수 없는 매장: {store_key}")
            return {"error": f"알 수 없는 매장: {store_key}"}

        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"[무제한 파이프라인] {store['name']} 크롤링 시작")
        print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"설정: 채널당 {max_per_channel}개, 검색어당 {max_per_search}개")
        print(f"{'='*60}")

        stats = {
            "store": store_key,
            "videos_collected": 0,
            "videos_new": 0,
            "videos_with_transcript": 0,
            "products_extracted": 0,
            "products_matched": 0,
            "products_saved": 0,
            "errors": [],
        }

        # Step 1: 영상 수집 (yt-dlp)
        print("\n[Step 1/5] 영상 수집 (yt-dlp - 무제한)...")
        try:
            videos = self.crawler.full_crawl(
                store_key,
                max_channel_videos=max_per_channel,
                max_search_videos=max_per_search,
            )
            stats["videos_collected"] = len(videos)
            print(f"  -> {len(videos)}개 영상 수집됨")

            # DB에 저장 및 중복 체크
            new_videos = []
            for video in videos:
                existing = self.db.get_video_by_id(video['video_id'])
                if existing and skip_existing:
                    continue  # 이미 처리된 영상 스킵
                if self.db.insert_video(video):
                    new_videos.append(video)

            stats["videos_new"] = len(new_videos)
            print(f"  -> {len(new_videos)}개 신규 영상")

            # 처리할 영상 제한
            videos_to_process = new_videos[:max_videos]

        except Exception as e:
            print(f"  [에러] 영상 수집 실패: {e}")
            stats["errors"].append(f"영상 수집: {e}")
            videos_to_process = []

        if not videos_to_process:
            print("\n[완료] 처리할 새 영상이 없습니다.")
            return stats

        # Step 2: 자막 추출 및 검증
        print(f"\n[Step 2/5] 자막 추출 ({len(videos_to_process)}개 영상)...")
        valid_videos = []

        for video in tqdm(videos_to_process, desc="  자막"):
            video_id = video['video_id']

            # 자막 추출
            transcript = self.crawler.get_video_transcript(video_id)

            # 자막 없으면 제목+설명 사용
            if not transcript:
                title = video.get('title', '')
                description = video.get('description', '')
                if title or description:
                    transcript = f"{title}\n\n{description}"

            # 품질 검증
            if transcript:
                validation = self.validator.validate(transcript, store['name'])

                if validation.is_valid:
                    self.db.update_video_transcript(
                        video_id, transcript, validation.quality_score
                    )
                    valid_videos.append({
                        **video,
                        'transcript': transcript,
                        'quality_score': validation.quality_score,
                    })
                else:
                    self.db.update_video_status(video_id, 'low_quality')
            else:
                self.db.update_video_status(video_id, 'no_transcript')

            time.sleep(0.5)

        stats["videos_with_transcript"] = len(valid_videos)
        print(f"  -> 유효한 자막: {len(valid_videos)}개")

        if not valid_videos:
            print("\n[완료] 유효한 자막이 있는 영상이 없습니다.")
            return stats

        # Step 3: AI 상품 추출
        if not self.extractor:
            print("\n[Step 3/5] AI 상품 추출... (스킵 - AI 미설정)")
            all_products = []
        else:
            print(f"\n[Step 3/5] AI 상품 추출 ({len(valid_videos)}개 영상)...")
            all_products = []

            for video in tqdm(valid_videos, desc="  AI"):
                try:
                    products = self.extractor.extract_products(
                        video['transcript'], store['name']
                    )

                    for product in products:
                        product['video_id'] = video['video_id']
                        product['store_key'] = store_key
                        product['store_name'] = store['name']
                        product['source_view_count'] = video.get('view_count', 0)
                        product['channel_title'] = video.get('channel_title', '')
                        product['video_title'] = video.get('title', '')
                        all_products.append(product)

                    self.db.update_video_status(video['video_id'], 'analyzed')

                except Exception as e:
                    print(f"  [에러] {video['video_id']}: {e}")
                    stats["errors"].append(f"AI 추출: {e}")

                time.sleep(1)  # AI API 속도 제한

            stats["products_extracted"] = len(all_products)
            print(f"  -> {len(all_products)}개 상품 추출됨")

        # Step 4: 매장 상품 매칭
        print("\n[Step 4/5] 매장 상품 매칭...")
        enriched_products = []

        if self.matcher and self.matcher.catalog:
            for product in tqdm(all_products, desc="  매칭"):
                match = self.matcher.match(
                    product_name=product.get('name', ''),
                    price=product.get('price'),
                    category=product.get('category'),
                    keywords=product.get('keywords', []),
                )

                if match:
                    product['official'] = match.to_dict()
                    product['needs_manual_review'] = match.needs_manual_review
                    stats["products_matched"] += 1
                else:
                    product['official'] = {}
                    product['needs_manual_review'] = True

                enriched_products.append(product)

            print(f"  -> {stats['products_matched']}/{len(enriched_products)}개 매칭")
        else:
            enriched_products = all_products
            for p in enriched_products:
                p['needs_manual_review'] = True
            print("  -> 매칭 스킵 (카탈로그 없음)")

        # Step 5: DB 저장
        print("\n[Step 5/5] DB 저장...")
        for product in enriched_products:
            if self.db.insert_product(product):
                stats["products_saved"] += 1

        print(f"  -> {stats['products_saved']}개 저장됨")

        # 결과 요약
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        stats["elapsed_seconds"] = elapsed

        print(f"\n{'='*60}")
        print(f"[무제한 파이프라인] 완료!")
        print(f"{'='*60}")
        print(f"소요 시간: {elapsed:.1f}초")
        print(f"수집 영상: {stats['videos_collected']}")
        print(f"신규 영상: {stats['videos_new']}")
        print(f"유효 자막: {stats['videos_with_transcript']}")
        print(f"추출 상품: {stats['products_extracted']}")
        print(f"매칭 성공: {stats['products_matched']}")
        print(f"저장 완료: {stats['products_saved']}")

        if stats["errors"]:
            print(f"\n에러: {len(stats['errors'])}건")

        return stats

    def run_all_stores(self, **kwargs) -> Dict[str, Dict]:
        """모든 매장 수집"""
        results = {}

        stores = list(STORE_CATEGORIES.keys())
        print(f"\n=== 전체 매장 수집 시작 ({len(stores)}개 매장) ===")

        for i, store_key in enumerate(stores, 1):
            print(f"\n[{i}/{len(stores)}] {store_key}")
            try:
                results[store_key] = self.run(store_key, **kwargs)
            except Exception as e:
                print(f"  [에러] {store_key} 수집 실패: {e}")
                results[store_key] = {"error": str(e)}

        # 전체 통계
        total_videos = sum(r.get('videos_collected', 0) for r in results.values())
        total_products = sum(r.get('products_saved', 0) for r in results.values())

        print(f"\n=== 전체 수집 완료 ===")
        print(f"총 영상: {total_videos}개")
        print(f"총 상품: {total_products}개")

        return results

    def run_daemon(self, interval_seconds: int = 3600, stores: List[str] = None,
                   catalog_interval_hours: int = 24):
        """
        데몬 모드 - 주기적으로 수집 실행

        Args:
            interval_seconds: 영상 수집 간격 (초)
            stores: 수집할 매장 목록 (None이면 전체)
            catalog_interval_hours: 카탈로그 크롤링 간격 (시간)
        """
        if stores is None:
            stores = list(STORE_CATEGORIES.keys())

        print(f"\n=== 데몬 모드 시작 ===")
        print(f"수집 대상: {', '.join(stores)}")
        print(f"영상 수집 간격: {interval_seconds}초 ({interval_seconds/3600:.1f}시간)")
        print(f"카탈로그 업데이트 간격: {catalog_interval_hours}시간")
        print(f"종료: Ctrl+C")

        run_count = 0
        last_catalog_crawl = None

        while True:
            run_count += 1
            print(f"\n{'='*60}")
            print(f"[실행 #{run_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")

            # 카탈로그 업데이트 체크 (주기적으로)
            if CATALOG_CRAWLER_AVAILABLE:
                should_crawl_catalog = False
                if last_catalog_crawl is None:
                    should_crawl_catalog = True
                elif datetime.now() - last_catalog_crawl > timedelta(hours=catalog_interval_hours):
                    should_crawl_catalog = True

                if should_crawl_catalog:
                    print("\n[카탈로그 업데이트 시작]")
                    for store_key in stores:
                        if store_key in CATALOG_CONFIG:
                            try:
                                self.crawl_catalog(store_key)
                            except Exception as e:
                                print(f"[에러] 카탈로그 크롤링 실패 ({store_key}): {e}")
                    last_catalog_crawl = datetime.now()

            # 영상 수집
            for store_key in stores:
                try:
                    self.run(store_key, max_videos=20)
                except Exception as e:
                    print(f"[에러] {store_key}: {e}")

            print(f"\n다음 실행까지 {interval_seconds}초 대기...")
            time.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="꿀템장바구니 무제한 파이프라인")
    parser.add_argument('--store', type=str, default='daiso', help='수집할 매장 (기본: daiso)')
    parser.add_argument('--all', action='store_true', help='모든 매장 수집')
    parser.add_argument('--max-videos', type=int, default=50, help='처리할 최대 영상 수')
    parser.add_argument('--max-per-channel', type=int, default=20, help='채널당 최대 영상 수')
    parser.add_argument('--daemon', action='store_true', help='데몬 모드 (주기적 실행)')
    parser.add_argument('--interval', type=int, default=3600, help='데몬 실행 간격 (초)')
    parser.add_argument('--catalog-only', action='store_true', help='카탈로그만 크롤링')
    parser.add_argument('--with-catalog', action='store_true', help='카탈로그 크롤링 후 영상 수집')

    args = parser.parse_args()

    pipeline = UnlimitedPipeline()

    # 카탈로그만 크롤링
    if args.catalog_only:
        if not CATALOG_CRAWLER_AVAILABLE:
            print("[에러] Playwright가 설치되어 있지 않습니다")
            print("       pip install playwright && playwright install chromium")
            sys.exit(1)
        pipeline.crawl_catalog(args.store)
        return

    # 카탈로그 먼저 크롤링 후 영상 수집
    if args.with_catalog and CATALOG_CRAWLER_AVAILABLE:
        print("\n[Step 0] 카탈로그 크롤링...")
        pipeline.crawl_catalog(args.store)

    if args.daemon:
        stores = None if args.all else [args.store]
        pipeline.run_daemon(interval_seconds=args.interval, stores=stores)
    elif args.all:
        pipeline.run_all_stores(
            max_videos=args.max_videos,
            max_per_channel=args.max_per_channel,
        )
    else:
        pipeline.run(
            store_key=args.store,
            max_videos=args.max_videos,
            max_per_channel=args.max_per_channel,
        )


if __name__ == "__main__":
    main()
