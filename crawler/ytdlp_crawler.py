# -*- coding: utf-8 -*-
"""
꿀템장바구니 - yt-dlp 기반 YouTube 크롤러 (개선판)
YouTube API 쿼터 제한 없이 무제한 수집 가능

개선 사항:
- 최신 영상 우선 수집 (업로드 날짜순)
- DB 기반 중복 체크 (이미 수집한 영상 스킵)
- 마지막 수집 이후 새 영상만 가져오기
- 채널별 마지막 수집 날짜 추적
"""
import json
import re
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
from pathlib import Path

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    print("[!] yt-dlp 미설치. pip install yt-dlp 실행 필요")

from config import TARGET_CHANNELS, STORE_CATEGORIES, CRAWL_CONFIG, SEARCH_KEYWORDS


class YTDLPCrawler:
    """yt-dlp 기반 YouTube 크롤러 (API 쿼터 제한 없음)"""

    def __init__(self, cookies_file: str = None, db=None):
        """
        Args:
            cookies_file: YouTube 쿠키 파일 경로 (로그인 필요 시)
            db: 데이터베이스 인스턴스 (중복 체크용)
        """
        if not YTDLP_AVAILABLE:
            raise ImportError("yt-dlp가 설치되지 않았습니다. pip install yt-dlp")

        self.cookies_file = cookies_file
        self.db = db

        # 기본 yt-dlp 옵션
        self.base_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
        }

        if cookies_file:
            self.base_opts['cookiefile'] = cookies_file

        # 이미 수집한 video_id 캐시
        self._collected_ids: Set[str] = set()
        if db:
            self._load_collected_ids()

        # 통계
        self.stats = {
            'videos_fetched': 0,
            'videos_skipped': 0,  # 이미 수집된 영상
            'videos_new': 0,      # 새로 수집된 영상
            'transcripts_fetched': 0,
            'errors': 0,
        }

    def _load_collected_ids(self):
        """DB에서 이미 수집한 영상 ID 로드"""
        try:
            if self.db and hasattr(self.db, 'get_all_video_ids'):
                self._collected_ids = set(self.db.get_all_video_ids())
                print(f"[INFO] 기존 수집 영상: {len(self._collected_ids)}개")
        except Exception as e:
            print(f"[WARNING] 기존 영상 ID 로드 실패: {e}")

    def is_already_collected(self, video_id: str) -> bool:
        """이미 수집된 영상인지 확인"""
        return video_id in self._collected_ids

    def mark_as_collected(self, video_id: str):
        """수집 완료로 표시"""
        self._collected_ids.add(video_id)

    def _get_ydl_opts(self, **kwargs) -> dict:
        """yt-dlp 옵션 생성"""
        opts = self.base_opts.copy()
        opts.update(kwargs)
        return opts

    def get_video_info(self, video_id: str, skip_if_collected: bool = True) -> Optional[Dict]:
        """단일 영상 정보 가져오기"""
        # 중복 체크
        if skip_if_collected and self.is_already_collected(video_id):
            self.stats['videos_skipped'] += 1
            return None

        url = f"https://www.youtube.com/watch?v={video_id}"

        opts = self._get_ydl_opts(
            skip_download=True,
        )

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None

                self.stats['videos_fetched'] += 1
                self.stats['videos_new'] += 1

                return {
                    'video_id': info.get('id'),
                    'title': info.get('title'),
                    'description': info.get('description', ''),
                    'channel_id': info.get('channel_id'),
                    'channel_title': info.get('channel') or info.get('uploader'),
                    'published_at': self._parse_upload_date(info.get('upload_date')),
                    'thumbnail_url': info.get('thumbnail'),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'comment_count': info.get('comment_count', 0),
                    'duration': info.get('duration', 0),
                    'tags': info.get('tags', []),
                }

        except Exception as e:
            self.stats['errors'] += 1
            print(f"[에러] 영상 정보 가져오기 실패 ({video_id}): {e}")
            return None

    def get_video_transcript(self, video_id: str, languages: List[str] = None) -> Optional[str]:
        """영상 자막 추출"""
        if languages is None:
            languages = ['ko', 'ko-KR', 'en', 'en-US']

        url = f"https://www.youtube.com/watch?v={video_id}"

        opts = self._get_ydl_opts(
            skip_download=True,
            writesubtitles=True,
            writeautomaticsub=True,
            subtitleslangs=languages,
            subtitlesformat='vtt',
        )

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None

                # 자막 정보 확인
                subtitles = info.get('subtitles', {})
                auto_captions = info.get('automatic_captions', {})

                # 선호 언어 순서로 자막 찾기
                transcript_url = None
                for lang in languages:
                    # 수동 자막 우선
                    if lang in subtitles and subtitles[lang]:
                        for sub in subtitles[lang]:
                            if sub.get('ext') == 'vtt' or sub.get('ext') == 'srv1':
                                transcript_url = sub.get('url')
                                break
                    # 자동 생성 자막
                    if not transcript_url and lang in auto_captions and auto_captions[lang]:
                        for sub in auto_captions[lang]:
                            if sub.get('ext') == 'vtt' or sub.get('ext') == 'srv1':
                                transcript_url = sub.get('url')
                                break
                    if transcript_url:
                        break

                if transcript_url:
                    transcript_text = self._download_and_parse_vtt(transcript_url)
                    if transcript_text:
                        self.stats['transcripts_fetched'] += 1
                        return transcript_text

                return None

        except Exception as e:
            self.stats['errors'] += 1
            print(f"[에러] 자막 추출 실패 ({video_id}): {e}")
            return None

    def _download_and_parse_vtt(self, url: str) -> Optional[str]:
        """VTT 자막 다운로드 및 텍스트 추출"""
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=30) as response:
                vtt_content = response.read().decode('utf-8')

            lines = []
            for line in vtt_content.split('\n'):
                line = line.strip()
                if not line or line.startswith('WEBVTT') or '-->' in line:
                    continue
                if line.isdigit():
                    continue
                line = re.sub(r'<[^>]+>', '', line)
                if line:
                    lines.append(line)

            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)

            return ' '.join(unique_lines)

        except Exception as e:
            print(f"[에러] VTT 파싱 실패: {e}")
            return None

    def _parse_upload_date(self, date_str: str) -> Optional[str]:
        """업로드 날짜 파싱 (YYYYMMDD -> ISO format)"""
        if not date_str:
            return None
        try:
            dt = datetime.strptime(date_str, '%Y%m%d')
            return dt.isoformat() + 'Z'
        except:
            return date_str

    def get_channel_videos_newest_first(self, channel_id: str = None, channel_handle: str = None,
                                         max_results: int = 50, since_date: datetime = None,
                                         skip_collected: bool = True) -> List[Dict]:
        """
        채널의 최신 영상 목록 가져오기 (최신순 정렬)

        Args:
            channel_id: 채널 ID
            channel_handle: 채널 핸들 (@username)
            max_results: 최대 결과 수
            since_date: 이 날짜 이후 영상만 가져오기
            skip_collected: 이미 수집된 영상 스킵
        """
        if channel_handle:
            handle = channel_handle.lstrip('@')
            url = f"https://www.youtube.com/@{handle}/videos"
        elif channel_id:
            url = f"https://www.youtube.com/channel/{channel_id}/videos"
        else:
            return []

        opts = self._get_ydl_opts(
            extract_flat='in_playlist',
            playlistend=max_results * 2,  # 중복/필터 고려해서 여유있게
        )

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info or 'entries' not in info:
                    return []

                videos = []
                skipped_count = 0

                for entry in info.get('entries', []):
                    if not entry:
                        continue

                    video_id = entry.get('id')

                    # 이미 수집된 영상 스킵
                    if skip_collected and self.is_already_collected(video_id):
                        skipped_count += 1
                        self.stats['videos_skipped'] += 1
                        continue

                    # 상세 정보 가져오기
                    video_info = self.get_video_info(video_id, skip_if_collected=False)

                    if video_info:
                        # 날짜 필터링
                        if since_date and video_info.get('published_at'):
                            try:
                                pub_date = datetime.fromisoformat(video_info['published_at'].rstrip('Z'))
                                if pub_date < since_date:
                                    # 날짜순이므로 이후 영상도 오래된 것
                                    print(f"    (날짜 필터: {pub_date.date()} < {since_date.date()})")
                                    break
                            except:
                                pass

                        videos.append(video_info)
                        self.mark_as_collected(video_id)

                    if len(videos) >= max_results:
                        break

                    time.sleep(0.5)

                if skipped_count > 0:
                    print(f"    (이미 수집: {skipped_count}개 스킵)")

                # 최신순 정렬 (업로드 날짜 기준)
                videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)

                return videos

        except Exception as e:
            self.stats['errors'] += 1
            print(f"[에러] 채널 영상 목록 가져오기 실패: {e}")
            return []

    def search_videos_newest_first(self, query: str, max_results: int = 20,
                                    skip_collected: bool = True) -> List[Dict]:
        """
        YouTube 검색 (최신순)

        Args:
            query: 검색어
            max_results: 최대 결과 수
            skip_collected: 이미 수집된 영상 스킵
        """
        # 최신순 검색을 위해 날짜 필터 추가
        url = f"ytsearch{max_results * 2}:{query}"

        opts = self._get_ydl_opts(
            extract_flat='in_playlist',
        )

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info or 'entries' not in info:
                    return []

                videos = []
                for entry in info.get('entries', []):
                    if not entry:
                        continue

                    video_id = entry.get('id')

                    # 이미 수집된 영상 스킵
                    if skip_collected and self.is_already_collected(video_id):
                        self.stats['videos_skipped'] += 1
                        continue

                    video_info = self.get_video_info(video_id, skip_if_collected=False)
                    if video_info:
                        videos.append(video_info)
                        self.mark_as_collected(video_id)
                        time.sleep(0.3)

                    if len(videos) >= max_results:
                        break

                # 최신순 정렬
                videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)

                return videos

        except Exception as e:
            self.stats['errors'] += 1
            print(f"[에러] 검색 실패 ({query}): {e}")
            return []

    # 기존 메서드들 (하위 호환성)
    def get_channel_videos(self, channel_id: str = None, channel_handle: str = None,
                           max_results: int = 50, published_after_days: int = None) -> List[Dict]:
        """채널의 영상 목록 가져오기 (하위 호환성)"""
        since_date = None
        if published_after_days:
            since_date = datetime.now() - timedelta(days=published_after_days)

        return self.get_channel_videos_newest_first(
            channel_id=channel_id,
            channel_handle=channel_handle,
            max_results=max_results,
            since_date=since_date,
        )

    def search_videos(self, query: str, max_results: int = 20) -> List[Dict]:
        """YouTube 검색 (하위 호환성)"""
        return self.search_videos_newest_first(query, max_results)

    def crawl_target_channels(self, store_key: str, max_per_channel: int = 20,
                               published_after_days: int = None) -> List[Dict]:
        """등록된 타겟 채널에서 최신 영상 수집"""
        if store_key not in TARGET_CHANNELS:
            print(f"[!] 타겟 채널 없음: {store_key}")
            return []

        if published_after_days is None:
            published_after_days = CRAWL_CONFIG.get('published_after_days', 30)

        since_date = datetime.now() - timedelta(days=published_after_days)

        channels = TARGET_CHANNELS[store_key]
        all_videos = []
        seen_ids = set()

        store_name = STORE_CATEGORIES.get(store_key, {}).get('name', store_key)
        print(f"\n[{store_name}] 타겟 채널 수집 (최신 영상 우선)...")
        print(f"  기준 날짜: {since_date.date()} 이후")

        for channel_info in channels:
            channel_name = channel_info.get('name', 'Unknown')
            priority = channel_info.get('priority', 3)

            print(f"  채널: {channel_name}")

            try:
                videos = self.get_channel_videos_newest_first(
                    channel_id=channel_info.get('id'),
                    channel_handle=channel_info.get('handle'),
                    max_results=max_per_channel,
                    since_date=since_date,
                )

                new_count = 0
                for video in videos:
                    if video['video_id'] not in seen_ids:
                        video['store_key'] = store_key
                        video['store_name'] = store_name
                        video['source_channel'] = channel_name
                        video['priority'] = priority
                        video['source_type'] = 'channel'
                        all_videos.append(video)
                        seen_ids.add(video['video_id'])
                        new_count += 1

                print(f"    -> {new_count}개 새 영상")

            except Exception as e:
                print(f"    [에러] {e}")

            time.sleep(1)

        # 최신순 정렬
        all_videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)

        print(f"  총 {len(all_videos)}개 새 영상 수집")
        return all_videos

    def crawl_search_keywords(self, store_key: str, max_per_keyword: int = 10) -> List[Dict]:
        """검색 키워드로 최신 영상 수집"""
        if store_key not in SEARCH_KEYWORDS:
            print(f"[!] 검색 키워드 없음: {store_key}")
            return []

        keywords = SEARCH_KEYWORDS[store_key]
        all_videos = []
        seen_ids = set()

        store_name = STORE_CATEGORIES.get(store_key, {}).get('name', store_key)
        print(f"\n[{store_name}] 키워드 검색 (최신 영상 우선)...")

        for keyword in keywords:
            print(f"  검색: {keyword}")

            try:
                videos = self.search_videos_newest_first(keyword, max_results=max_per_keyword)

                new_count = 0
                for video in videos:
                    if video['video_id'] not in seen_ids:
                        video['store_key'] = store_key
                        video['store_name'] = store_name
                        video['search_keyword'] = keyword
                        video['source_type'] = 'search'
                        all_videos.append(video)
                        seen_ids.add(video['video_id'])
                        new_count += 1

                print(f"    -> {new_count}개 새 영상")

            except Exception as e:
                print(f"    [에러] {e}")

            time.sleep(1)

        # 최신순 정렬
        all_videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)

        print(f"  총 {len(all_videos)}개 새 영상 수집")
        return all_videos

    def full_crawl(self, store_key: str = 'daiso', max_channel_videos: int = 20,
                   max_search_videos: int = 10) -> List[Dict]:
        """전체 수집 (채널 + 키워드, 최신 영상 우선)"""
        all_videos = []
        seen_ids = set()

        # 1. 타겟 채널 수집
        channel_videos = self.crawl_target_channels(store_key, max_per_channel=max_channel_videos)
        for v in channel_videos:
            if v['video_id'] not in seen_ids:
                all_videos.append(v)
                seen_ids.add(v['video_id'])

        # 2. 키워드 검색
        keyword_videos = self.crawl_search_keywords(store_key, max_per_keyword=max_search_videos)
        for v in keyword_videos:
            if v['video_id'] not in seen_ids:
                all_videos.append(v)
                seen_ids.add(v['video_id'])

        # 최신순 정렬
        all_videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)

        print(f"\n=== 전체 수집 완료 ===")
        print(f"  새 영상: {len(all_videos)}개")
        print(f"  스킵 (이미 수집): {self.stats['videos_skipped']}개")
        print(f"  에러: {self.stats['errors']}개")

        return all_videos

    def get_stats(self) -> Dict:
        """통계 조회"""
        return self.stats.copy()


# 기존 YouTubeCrawler와 호환성 유지를 위한 별칭
TRANSCRIPT_AVAILABLE = YTDLP_AVAILABLE


def main():
    """테스트 실행"""
    print("=== yt-dlp 크롤러 테스트 (개선판) ===\n")

    crawler = YTDLPCrawler()

    # 1. 단일 영상 테스트
    print("[테스트 1] 단일 영상 정보")
    video = crawler.get_video_info("dQw4w9WgXcQ")
    if video:
        print(f"  제목: {video['title']}")
        print(f"  채널: {video['channel_title']}")
        print(f"  조회수: {video['view_count']:,}")

    # 2. 최신 영상 검색 테스트
    print("\n[테스트 2] 최신 영상 검색")
    results = crawler.search_videos_newest_first("다이소 꿀템 2024", max_results=3)
    for r in results:
        pub_date = r.get('published_at', '')[:10] if r.get('published_at') else 'N/A'
        print(f"  - [{pub_date}] {r['title'][:40]}...")

    print(f"\n통계: {crawler.get_stats()}")


if __name__ == "__main__":
    main()
