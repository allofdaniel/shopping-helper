# -*- coding: utf-8 -*-
"""
YouTube Scraper - API 쿼터 제한 없는 YouTube 데이터 수집기

scrapetube + yt-dlp + youtube-transcript-api 조합 사용
YouTube Data API v3 쿼터(10,000/일) 제한 없이 무제한 수집 가능

사용법:
    scraper = YouTubeScraper()
    videos = scraper.search("다이소 추천템", limit=50)
    scraper.save_to_db(videos)
"""
import time
import random
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass, asdict

import scrapetube
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# 로그 디렉토리 생성
LOG_DIR = Path(__file__).parent / 'data' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'youtube_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / 'data' / 'products.db'


@dataclass
class VideoData:
    """비디오 데이터 구조"""
    video_id: str
    title: str
    channel_title: str
    channel_id: str
    description: str
    view_count: int
    like_count: int
    upload_date: str
    duration: int
    thumbnail_url: str
    tags: List[str]
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None


class RateLimiter:
    """요청 속도 제한기"""
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request = 0

    def wait(self):
        """랜덤 딜레이로 봇 감지 회피"""
        elapsed = time.time() - self.last_request
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request = time.time()


class YouTubeScraper:
    """YouTube 스크래퍼 (API 쿼터 무제한)"""

    def __init__(self):
        self.rate_limiter = RateLimiter(min_delay=1.5, max_delay=3.0)
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
        }
        self.stats = {
            'searched': 0,
            'metadata_fetched': 0,
            'transcripts_fetched': 0,
            'errors': 0
        }

        # 로그 디렉토리 생성
        log_dir = Path('data/logs')
        log_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, limit: int = 50) -> Generator[Dict, None, None]:
        """
        키워드로 YouTube 검색 (scrapetube 사용)

        Args:
            query: 검색어
            limit: 최대 결과 수

        Yields:
            비디오 기본 정보 딕셔너리
        """
        logger.info(f"Searching: '{query}' (limit: {limit})")

        try:
            results = scrapetube.get_search(query)
            count = 0

            for video in results:
                if count >= limit:
                    break

                try:
                    video_data = {
                        'video_id': video.get('videoId'),
                        'title': self._extract_title(video),
                        'channel': self._extract_channel(video),
                        'view_count': self._extract_views(video),
                        'duration': self._extract_duration(video),
                        'thumbnail': video.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url', '')
                    }

                    if video_data['video_id']:
                        yield video_data
                        count += 1
                        self.stats['searched'] += 1

                except Exception as e:
                    logger.warning(f"Error parsing search result: {e}")
                    self.stats['errors'] += 1

        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            self.stats['errors'] += 1

    def _extract_title(self, video: dict) -> str:
        """제목 추출"""
        title_data = video.get('title', {})
        if isinstance(title_data, dict):
            runs = title_data.get('runs', [])
            if runs:
                return runs[0].get('text', '')
            return title_data.get('simpleText', '')
        return str(title_data)

    def _extract_channel(self, video: dict) -> str:
        """채널명 추출"""
        owner = video.get('ownerText', {})
        if isinstance(owner, dict):
            runs = owner.get('runs', [])
            if runs:
                return runs[0].get('text', '')
        return ''

    def _extract_views(self, video: dict) -> int:
        """조회수 추출"""
        view_text = video.get('viewCountText', {})
        if isinstance(view_text, dict):
            text = view_text.get('simpleText', '') or view_text.get('runs', [{}])[0].get('text', '')
            # "조회수 1.2만회" 또는 "1.2M views" 파싱
            text = text.replace(',', '').replace('조회수', '').replace('회', '').strip()
            try:
                if '만' in text:
                    return int(float(text.replace('만', '')) * 10000)
                elif '천' in text:
                    return int(float(text.replace('천', '')) * 1000)
                elif 'M' in text.upper():
                    return int(float(text.upper().replace('M', '')) * 1000000)
                elif 'K' in text.upper():
                    return int(float(text.upper().replace('K', '')) * 1000)
                else:
                    return int(text) if text.isdigit() else 0
            except (ValueError, TypeError):
                return 0
        return 0

    def _extract_duration(self, video: dict) -> int:
        """영상 길이(초) 추출"""
        duration_text = video.get('lengthText', {}).get('simpleText', '')
        if not duration_text:
            return 0

        parts = duration_text.split(':')
        try:
            if len(parts) == 3:  # H:M:S
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:  # M:S
                return int(parts[0]) * 60 + int(parts[1])
            else:
                return int(parts[0])
        except (ValueError, IndexError):
            return 0

    def get_video_details(self, video_id: str) -> Optional[VideoData]:
        """
        비디오 상세 정보 가져오기 (yt-dlp 사용)

        Args:
            video_id: YouTube 비디오 ID

        Returns:
            VideoData 또는 None
        """
        self.rate_limiter.wait()

        url = f'https://www.youtube.com/watch?v={video_id}'

        try:
            with YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None

                video_data = VideoData(
                    video_id=video_id,
                    title=info.get('title', ''),
                    channel_title=info.get('channel', '') or info.get('uploader', ''),
                    channel_id=info.get('channel_id', ''),
                    description=info.get('description', '') or '',
                    view_count=info.get('view_count', 0) or 0,
                    like_count=info.get('like_count', 0) or 0,
                    upload_date=self._format_date(info.get('upload_date', '')),
                    duration=info.get('duration', 0) or 0,
                    thumbnail_url=info.get('thumbnail', ''),
                    tags=info.get('tags', []) or []
                )

                self.stats['metadata_fetched'] += 1
                logger.debug(f"Fetched metadata: {video_id}")
                return video_data

        except Exception as e:
            logger.warning(f"Failed to get details for {video_id}: {e}")
            self.stats['errors'] += 1
            return None

    def _format_date(self, date_str: str) -> str:
        """날짜 포맷 변환 (YYYYMMDD -> YYYY-MM-DD)"""
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    def get_transcript(self, video_id: str, languages: List[str] = None) -> Optional[str]:
        """
        비디오 자막/트랜스크립트 가져오기

        Args:
            video_id: YouTube 비디오 ID
            languages: 선호 언어 목록 (기본: ['ko', 'en'])

        Returns:
            트랜스크립트 텍스트 또는 None
        """
        if languages is None:
            languages = ['ko', 'en']

        self.rate_limiter.wait()

        try:
            # 새로운 인스턴스 기반 API 사용
            api = YouTubeTranscriptApi()

            # 선호 언어 순서대로 시도
            for lang in languages:
                try:
                    transcript = api.fetch(video_id, languages=[lang])
                    text_parts = []
                    for segment in transcript:
                        if hasattr(segment, 'text'):
                            text_parts.append(segment.text)
                        elif isinstance(segment, dict):
                            text_parts.append(segment.get('text', ''))

                    if text_parts:
                        text = ' '.join(text_parts)
                        self.stats['transcripts_fetched'] += 1
                        logger.debug(f"Fetched transcript: {video_id}")
                        return text
                except (TranscriptsDisabled, NoTranscriptFound):
                    continue
                except Exception as e:
                    logger.debug(f"Transcript fetch failed for lang {lang}: {e}")
                    continue

            # 모든 언어 실패 시 기본 언어로 시도
            try:
                transcript = api.fetch(video_id)
                text_parts = [getattr(s, 'text', s.get('text', '')) if hasattr(s, 'text') or isinstance(s, dict) else '' for s in transcript]
                if text_parts:
                    text = ' '.join(text_parts)
                    self.stats['transcripts_fetched'] += 1
                    return text
            except (TranscriptsDisabled, NoTranscriptFound):
                logger.debug(f"No transcript available for {video_id}")
            except Exception as e:
                logger.debug(f"Fallback transcript fetch failed: {e}")

        except TranscriptsDisabled:
            logger.debug(f"Transcripts disabled: {video_id}")
        except NoTranscriptFound:
            logger.debug(f"No transcript found: {video_id}")
        except Exception as e:
            logger.warning(f"Transcript error for {video_id}: {e}")
            self.stats['errors'] += 1

        return None

    def search_and_extract(self, query: str, limit: int = 30,
                           get_details: bool = True,
                           get_transcripts: bool = True) -> List[VideoData]:
        """
        검색 + 상세정보 + 자막 한번에 수집

        Args:
            query: 검색어
            limit: 최대 결과 수
            get_details: 상세 정보 수집 여부
            get_transcripts: 자막 수집 여부

        Returns:
            VideoData 리스트
        """
        logger.info(f"=== Search & Extract: '{query}' ===")
        results = []

        for basic_info in self.search(query, limit):
            video_id = basic_info['video_id']

            if get_details:
                video_data = self.get_video_details(video_id)
                if not video_data:
                    continue
            else:
                # 기본 정보만 사용
                video_data = VideoData(
                    video_id=video_id,
                    title=basic_info['title'],
                    channel_title=basic_info['channel'],
                    channel_id='',
                    description='',
                    view_count=basic_info['view_count'],
                    like_count=0,
                    upload_date='',
                    duration=basic_info['duration'],
                    thumbnail_url=basic_info['thumbnail'],
                    tags=[]
                )

            if get_transcripts:
                video_data.transcript = self.get_transcript(video_id)

            results.append(video_data)
            logger.info(f"  [{len(results)}/{limit}] {video_data.title[:40]}...")

        logger.info(f"=== Completed: {len(results)} videos ===")
        return results

    def get_channel_videos(self, channel_id: str, limit: int = 50) -> Generator[Dict, None, None]:
        """
        채널의 최신 비디오 가져오기

        Args:
            channel_id: YouTube 채널 ID
            limit: 최대 결과 수

        Yields:
            비디오 기본 정보
        """
        logger.info(f"Getting videos from channel: {channel_id}")

        try:
            videos = scrapetube.get_channel(channel_id)
            count = 0

            for video in videos:
                if count >= limit:
                    break

                video_data = {
                    'video_id': video.get('videoId'),
                    'title': self._extract_title(video),
                    'view_count': self._extract_views(video),
                    'duration': self._extract_duration(video)
                }

                if video_data['video_id']:
                    yield video_data
                    count += 1

        except Exception as e:
            logger.error(f"Failed to get channel videos: {e}")

    def save_to_db(self, videos: List[VideoData], store_key: str = 'unknown') -> int:
        """
        비디오 데이터를 DB에 저장

        Args:
            videos: VideoData 리스트
            store_key: 매장 키 (daiso, costco, etc.)

        Returns:
            저장된 비디오 수
        """
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        saved = 0
        for video in videos:
            try:
                cur.execute('''
                    INSERT OR REPLACE INTO videos
                    (video_id, title, channel_title, channel_id, description,
                     view_count, like_count, upload_date, duration, thumbnail_url,
                     tags, transcript, store_key, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    video.video_id,
                    video.title,
                    video.channel_title,
                    video.channel_id,
                    video.description[:5000] if video.description else '',
                    video.view_count,
                    video.like_count,
                    video.upload_date,
                    video.duration,
                    video.thumbnail_url,
                    ','.join(video.tags[:20]) if video.tags else '',
                    video.transcript[:20000] if video.transcript else '',
                    store_key,
                    'pending' if video.transcript else 'no_transcript'
                ))
                saved += 1
            except Exception as e:
                logger.warning(f"Failed to save video {video.video_id}: {e}")

        conn.commit()
        conn.close()

        logger.info(f"Saved {saved}/{len(videos)} videos to DB")
        return saved

    def get_stats(self) -> Dict:
        """수집 통계 반환"""
        return self.stats.copy()


def run_full_collection(store_keywords: Dict[str, List[str]] = None,
                        videos_per_keyword: int = 20) -> Dict:
    """
    전체 매장 키워드로 YouTube 수집 실행

    Args:
        store_keywords: 매장별 검색 키워드
        videos_per_keyword: 키워드당 수집할 비디오 수

    Returns:
        수집 결과 통계
    """
    if store_keywords is None:
        store_keywords = {
            'daiso': [
                '다이소 추천템', '다이소 신상', '다이소 꿀템',
                '다이소 하울', '다이소 정리', '다이소 인테리어'
            ],
            'costco': [
                '코스트코 추천', '코스트코 장보기', '코스트코 하울',
                '코스트코 식품', '코스트코 신상'
            ],
            'oliveyoung': [
                '올리브영 추천', '올리브영 하울', '올리브영 세일',
                '올리브영 스킨케어', '올리브영 베스트'
            ],
            'ikea': [
                '이케아 추천', '이케아 수납', '이케아 꿀템',
                '이케아 원룸', '이케아 인테리어'
            ],
            'traders': [
                '트레이더스 추천', '트레이더스 장보기', '이마트 트레이더스'
            ],
            'convenience': [
                '편의점 신상', 'CU 추천', 'GS25 추천',
                '편의점 먹방', '편의점 디저트'
            ]
        }

    scraper = YouTubeScraper()
    results = {
        'total_videos': 0,
        'total_with_transcript': 0,
        'by_store': {}
    }

    for store_key, keywords in store_keywords.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"Collecting for: {store_key}")
        logger.info(f"{'='*50}")

        store_videos = []

        for keyword in keywords:
            videos = scraper.search_and_extract(
                keyword,
                limit=videos_per_keyword,
                get_details=True,
                get_transcripts=True
            )
            store_videos.extend(videos)

            # 키워드 간 딜레이
            time.sleep(random.uniform(2, 4))

        # DB 저장
        saved = scraper.save_to_db(store_videos, store_key)

        with_transcript = sum(1 for v in store_videos if v.transcript)

        results['by_store'][store_key] = {
            'collected': len(store_videos),
            'saved': saved,
            'with_transcript': with_transcript
        }
        results['total_videos'] += saved
        results['total_with_transcript'] += with_transcript

    logger.info(f"\n{'='*50}")
    logger.info("COLLECTION COMPLETE")
    logger.info(f"{'='*50}")
    logger.info(f"Total videos: {results['total_videos']}")
    logger.info(f"With transcripts: {results['total_with_transcript']}")

    return results


if __name__ == '__main__':
    # 테스트 실행
    scraper = YouTubeScraper()

    # 다이소 추천템 10개 수집 테스트
    videos = scraper.search_and_extract("다이소 추천템 2024", limit=10)

    print(f"\n수집 결과: {len(videos)}개")
    for v in videos[:3]:
        print(f"  - {v.title[:50]}")
        print(f"    조회수: {v.view_count:,}, 자막: {'O' if v.transcript else 'X'}")

    # DB 저장
    scraper.save_to_db(videos, 'daiso')

    print(f"\n통계: {scraper.get_stats()}")
