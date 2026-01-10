# -*- coding: utf-8 -*-
"""
꿀템장바구니 - yt-dlp 기반 YouTube 크롤러
YouTube API 쿼터 제한 없이 무제한 수집 가능

기능:
- 채널의 모든 영상 목록 가져오기
- 영상 메타데이터 (제목, 설명, 조회수, 날짜)
- 자막 추출 (한국어/영어)
- 검색 결과 가져오기
- 플레이리스트 영상 가져오기
"""
import json
import re
import time
import subprocess
from datetime import datetime, timedelta
from typing import Optional, List, Dict
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

    def __init__(self, cookies_file: str = None):
        """
        Args:
            cookies_file: YouTube 쿠키 파일 경로 (로그인 필요 시)
        """
        if not YTDLP_AVAILABLE:
            raise ImportError("yt-dlp가 설치되지 않았습니다. pip install yt-dlp")

        self.cookies_file = cookies_file

        # 기본 yt-dlp 옵션
        self.base_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
        }

        if cookies_file:
            self.base_opts['cookiefile'] = cookies_file

        # 통계
        self.stats = {
            'videos_fetched': 0,
            'transcripts_fetched': 0,
            'errors': 0,
        }

    def _get_ydl_opts(self, **kwargs) -> dict:
        """yt-dlp 옵션 생성"""
        opts = self.base_opts.copy()
        opts.update(kwargs)
        return opts

    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """단일 영상 정보 가져오기"""
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
                    # 자막 다운로드 및 파싱
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

            # VTT 파싱 - 타임스탬프와 태그 제거
            lines = []
            for line in vtt_content.split('\n'):
                line = line.strip()
                # 헤더, 타임스탬프, 빈 줄 스킵
                if not line or line.startswith('WEBVTT') or '-->' in line:
                    continue
                if line.isdigit():
                    continue
                # HTML 태그 제거
                line = re.sub(r'<[^>]+>', '', line)
                if line:
                    lines.append(line)

            # 중복 제거 (자막은 종종 반복됨)
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

    def get_channel_videos(self, channel_id: str = None, channel_handle: str = None,
                           max_results: int = 50, published_after_days: int = None) -> List[Dict]:
        """채널의 영상 목록 가져오기"""
        if channel_handle:
            # @ 제거
            handle = channel_handle.lstrip('@')
            url = f"https://www.youtube.com/@{handle}/videos"
        elif channel_id:
            url = f"https://www.youtube.com/channel/{channel_id}/videos"
        else:
            return []

        opts = self._get_ydl_opts(
            extract_flat='in_playlist',
            playlistend=max_results,
        )

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info or 'entries' not in info:
                    return []

                videos = []
                cutoff_date = None
                if published_after_days:
                    cutoff_date = datetime.now() - timedelta(days=published_after_days)

                for entry in info.get('entries', []):
                    if not entry:
                        continue

                    # 상세 정보 가져오기 (조회수 등)
                    video_info = self.get_video_info(entry.get('id'))

                    if video_info:
                        # 날짜 필터링
                        if cutoff_date and video_info.get('published_at'):
                            try:
                                pub_date = datetime.fromisoformat(video_info['published_at'].rstrip('Z'))
                                if pub_date < cutoff_date:
                                    continue
                            except:
                                pass

                        videos.append(video_info)

                    if len(videos) >= max_results:
                        break

                    time.sleep(0.5)  # Rate limiting

                return videos

        except Exception as e:
            self.stats['errors'] += 1
            print(f"[에러] 채널 영상 목록 가져오기 실패: {e}")
            return []

    def search_videos(self, query: str, max_results: int = 20) -> List[Dict]:
        """YouTube 검색"""
        url = f"ytsearch{max_results}:{query}"

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

                    # 상세 정보 가져오기
                    video_info = self.get_video_info(entry.get('id'))
                    if video_info:
                        videos.append(video_info)
                        time.sleep(0.3)

                return videos

        except Exception as e:
            self.stats['errors'] += 1
            print(f"[에러] 검색 실패 ({query}): {e}")
            return []

    def crawl_target_channels(self, store_key: str, max_per_channel: int = 20,
                               published_after_days: int = None) -> List[Dict]:
        """등록된 타겟 채널에서 영상 수집"""
        if store_key not in TARGET_CHANNELS:
            print(f"[!] 타겟 채널 없음: {store_key}")
            return []

        if published_after_days is None:
            published_after_days = CRAWL_CONFIG.get('published_after_days', 30)

        channels = TARGET_CHANNELS[store_key]
        all_videos = []
        seen_ids = set()

        store_name = STORE_CATEGORIES.get(store_key, {}).get('name', store_key)
        print(f"\n[{store_name}] 타겟 채널 수집 시작...")

        for channel_info in channels:
            channel_name = channel_info.get('name', 'Unknown')
            priority = channel_info.get('priority', 3)

            print(f"  채널: {channel_name}")

            try:
                videos = self.get_channel_videos(
                    channel_id=channel_info.get('id'),
                    channel_handle=channel_info.get('handle'),
                    max_results=max_per_channel,
                    published_after_days=published_after_days,
                )

                for video in videos:
                    if video['video_id'] not in seen_ids:
                        video['store_key'] = store_key
                        video['store_name'] = store_name
                        video['source_channel'] = channel_name
                        video['priority'] = priority
                        video['source_type'] = 'channel'
                        all_videos.append(video)
                        seen_ids.add(video['video_id'])

                print(f"    -> {len(videos)}개 영상 수집")

            except Exception as e:
                print(f"    [에러] {e}")

            time.sleep(1)  # 채널 간 딜레이

        # 우선순위 + 조회수 순 정렬
        all_videos.sort(key=lambda x: (-x.get('priority', 3), -x.get('view_count', 0)))

        print(f"  총 {len(all_videos)}개 영상 수집 완료")
        return all_videos

    def crawl_search_keywords(self, store_key: str, max_per_keyword: int = 10) -> List[Dict]:
        """검색 키워드로 영상 수집"""
        if store_key not in SEARCH_KEYWORDS:
            print(f"[!] 검색 키워드 없음: {store_key}")
            return []

        keywords = SEARCH_KEYWORDS[store_key]
        all_videos = []
        seen_ids = set()

        store_name = STORE_CATEGORIES.get(store_key, {}).get('name', store_key)
        print(f"\n[{store_name}] 키워드 검색 시작...")

        for keyword in keywords:
            print(f"  검색: {keyword}")

            try:
                videos = self.search_videos(keyword, max_results=max_per_keyword)

                for video in videos:
                    if video['video_id'] not in seen_ids:
                        video['store_key'] = store_key
                        video['store_name'] = store_name
                        video['search_keyword'] = keyword
                        video['source_type'] = 'search'
                        all_videos.append(video)
                        seen_ids.add(video['video_id'])

                print(f"    -> {len(videos)}개 영상")

            except Exception as e:
                print(f"    [에러] {e}")

            time.sleep(1)

        # 조회수 순 정렬
        all_videos.sort(key=lambda x: x.get('view_count', 0), reverse=True)

        print(f"  총 {len(all_videos)}개 영상 수집 완료")
        return all_videos

    def full_crawl(self, store_key: str = 'daiso', max_channel_videos: int = 20,
                   max_search_videos: int = 10) -> List[Dict]:
        """전체 수집 (채널 + 키워드)"""
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

        print(f"\n=== 전체 수집 완료: {len(all_videos)}개 영상 ===")
        print(f"통계: {self.stats}")

        return all_videos

    def get_stats(self) -> Dict:
        """통계 조회"""
        return self.stats.copy()


# 기존 YouTubeCrawler와 호환성 유지를 위한 별칭
TRANSCRIPT_AVAILABLE = YTDLP_AVAILABLE


def main():
    """테스트 실행"""
    print("=== yt-dlp 크롤러 테스트 ===\n")

    crawler = YTDLPCrawler()

    # 1. 단일 영상 테스트
    print("[테스트 1] 단일 영상 정보")
    video = crawler.get_video_info("dQw4w9WgXcQ")
    if video:
        print(f"  제목: {video['title']}")
        print(f"  채널: {video['channel_title']}")
        print(f"  조회수: {video['view_count']:,}")

    # 2. 자막 테스트
    print("\n[테스트 2] 자막 추출")
    transcript = crawler.get_video_transcript("dQw4w9WgXcQ")
    if transcript:
        print(f"  자막 길이: {len(transcript)}자")
        print(f"  미리보기: {transcript[:100]}...")

    # 3. 검색 테스트
    print("\n[테스트 3] 검색")
    results = crawler.search_videos("다이소 꿀템", max_results=3)
    for r in results:
        print(f"  - {r['title']} ({r['view_count']:,}회)")

    print(f"\n통계: {crawler.get_stats()}")


if __name__ == "__main__":
    main()
