"""
꿀템장바구니 - YouTube 크롤러
유튜브 채널에서 신규 영상을 감지하고 메타데이터를 수집합니다.

개선사항 (v2):
- Exponential backoff with jitter
- API 쿼터 모니터링
- Circuit breaker 패턴
- 배치 처리 최적화
"""
import json
import re
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    TRANSCRIPT_AVAILABLE = True
except ImportError:
    TRANSCRIPT_AVAILABLE = False
    print("youtube-transcript-api 미설치. 자막 추출 불가.")

import time

from config import YOUTUBE_API_KEY, TARGET_CHANNELS, STORE_CATEGORIES, CRAWL_CONFIG, SEARCH_KEYWORDS


class RateLimiter:
    """API Rate Limiting 관리"""
    def __init__(self, calls_per_second: float = 1.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0

    def wait(self):
        """필요시 대기"""
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


class CircuitBreaker:
    """Circuit Breaker 패턴 - 연속 실패시 요청 중단"""
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        """성공 기록"""
        self.failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        """실패 기록"""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            print(f"[WARNING] Circuit breaker OPEN - {self.failures}회 연속 실패")

    def can_proceed(self) -> bool:
        """요청 가능 여부"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True


class QuotaTracker:
    """YouTube API 쿼터 추적 (일일 10,000 유닛)"""
    # API 비용 참조: https://developers.google.com/youtube/v3/determine_quota_cost
    COSTS = {
        "search.list": 100,
        "videos.list": 1,
        "channels.list": 1,
        "playlistItems.list": 1,
    }
    DAILY_QUOTA = 10000

    def __init__(self):
        self.used = 0
        self.reset_date = datetime.now().date()

    def _check_reset(self):
        """일일 리셋 확인"""
        today = datetime.now().date()
        if today > self.reset_date:
            self.used = 0
            self.reset_date = today

    def add(self, operation: str, count: int = 1):
        """쿼터 사용 기록"""
        self._check_reset()
        cost = self.COSTS.get(operation, 1) * count
        self.used += cost

    def remaining(self) -> int:
        """남은 쿼터"""
        self._check_reset()
        return max(0, self.DAILY_QUOTA - self.used)

    def can_afford(self, operation: str, count: int = 1) -> bool:
        """요청 가능 여부"""
        cost = self.COSTS.get(operation, 1) * count
        return self.remaining() >= cost

    def status(self) -> str:
        """현재 상태"""
        return f"쿼터: {self.used}/{self.DAILY_QUOTA} ({self.remaining()} 남음)"


class YouTubeCrawler:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or YOUTUBE_API_KEY
        if not self.api_key:
            raise ValueError("YouTube API 키가 필요합니다. .env 파일을 확인하세요.")
        self.youtube = build("youtube", "v3", developerKey=self.api_key)

        # 개선된 컴포넌트들
        self.rate_limiter = RateLimiter(calls_per_second=2.0)  # 초당 2회
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
        self.quota = QuotaTracker()

        # 통계
        self.stats = {
            "api_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "retries": 0,
        }

    def _exponential_backoff(self, attempt: int, base_delay: float = 1.0, max_delay: float = 32.0) -> float:
        """Exponential backoff with jitter 계산"""
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, delay * 0.1)  # 10% jitter
        return delay + jitter

    def _api_call_with_retry(self, operation: str, api_func, max_retries: int = 3) -> Optional[dict]:
        """API 호출 with retry, backoff, circuit breaker"""
        if not self.circuit_breaker.can_proceed():
            print(f"[WARNING] Circuit breaker OPEN - 요청 스킵")
            return None

        if not self.quota.can_afford(operation):
            print(f"[WARNING] 쿼터 부족 - {self.quota.status()}")
            return None

        for attempt in range(max_retries):
            try:
                self.rate_limiter.wait()
                self.stats["api_calls"] += 1

                response = api_func()

                self.circuit_breaker.record_success()
                self.quota.add(operation)
                self.stats["successful_calls"] += 1
                return response

            except HttpError as e:
                self.stats["failed_calls"] += 1
                error_reason = e.resp.status if hasattr(e, 'resp') else 'unknown'

                if error_reason == 403:
                    # 쿼터 초과
                    print(f"[ERROR] API 쿼터 초과! {self.quota.status()}")
                    self.circuit_breaker.record_failure()
                    return None

                elif error_reason == 429 or "rate" in str(e).lower():
                    # Rate limit
                    if attempt < max_retries - 1:
                        delay = self._exponential_backoff(attempt)
                        print(f"[WAIT] Rate limit - {delay:.1f}초 대기 후 재시도 ({attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        self.stats["retries"] += 1
                        continue

                elif error_reason in [500, 502, 503, 504]:
                    # 서버 오류 - 재시도
                    if attempt < max_retries - 1:
                        delay = self._exponential_backoff(attempt)
                        print(f"[WAIT] 서버 오류 ({error_reason}) - {delay:.1f}초 대기 후 재시도")
                        time.sleep(delay)
                        self.stats["retries"] += 1
                        continue

                self.circuit_breaker.record_failure()
                print(f"[ERROR] API 오류: {e}")
                return None

            except Exception as e:
                self.stats["failed_calls"] += 1
                self.circuit_breaker.record_failure()
                print(f"[ERROR] 예외 발생: {e}")
                return None

        return None

    def get_stats(self) -> dict:
        """통계 조회"""
        return {
            **self.stats,
            "quota": self.quota.status(),
            "circuit_breaker": self.circuit_breaker.state,
        }

    def get_channel_id_by_name(self, channel_name: str) -> Optional[str]:
        """채널 이름으로 채널 ID 조회"""
        try:
            response = self.youtube.search().list(
                part="snippet",
                q=channel_name,
                type="channel",
                maxResults=1
            ).execute()

            if response.get("items"):
                return response["items"][0]["snippet"]["channelId"]
            return None
        except HttpError as e:
            print(f"채널 검색 오류: {e}")
            return None

    def get_channel_id_by_handle(self, handle: str) -> Optional[str]:
        """채널 핸들(@username)로 채널 ID 조회"""
        # @ 제거
        clean_handle = handle.lstrip("@")
        try:
            # forHandle 파라미터 사용 (YouTube API v3)
            response = self.youtube.channels().list(
                part="id,snippet",
                forHandle=clean_handle
            ).execute()

            if response.get("items"):
                return response["items"][0]["id"]

            # 핸들로 못 찾으면 검색으로 시도
            return self.get_channel_id_by_name(handle)
        except HttpError as e:
            print(f"채널 핸들 조회 오류 ({handle}): {e}")
            # 검색으로 fallback
            return self.get_channel_id_by_name(handle)

    @staticmethod
    def _format_transcript_with_timestamps(fetched) -> str:
        """자막 snippet 목록을 [MM:SS] 타임스탬프 포함 텍스트로 변환"""
        parts = []
        for snippet in fetched:
            text = snippet.text.strip()
            if not text:
                continue
            start = getattr(snippet, 'start', None)
            if start is not None:
                total_sec = int(start)
                mins = total_sec // 60
                secs = total_sec % 60
                parts.append(f"[{mins}:{secs:02d}] {text}")
            else:
                parts.append(text)
        return " ".join(parts)

    def get_video_transcript(self, video_id: str, languages: list = None,
                               retry_count: int = 3, retry_delay: float = 2.0) -> Optional[str]:
        """영상 자막 추출 (Rate limiting 대응) - youtube-transcript-api v1.2+ 지원

        반환 형식: "[0:30] 텍스트 [0:45] 텍스트 ..." (타임스탬프 포함)
        """
        if not TRANSCRIPT_AVAILABLE:
            return None

        if languages is None:
            languages = ["ko", "ko-KR", "en"]

        for attempt in range(retry_count):
            try:
                # youtube-transcript-api v1.2+ 새 API 사용
                api = YouTubeTranscriptApi()

                # 1. 먼저 사용 가능한 자막 목록 확인
                try:
                    transcript_list = api.list(video_id)

                    # 2. 선호 언어 순서로 자막 찾기
                    selected_lang = None
                    for lang in languages:
                        for transcript in transcript_list:
                            if transcript.language_code == lang or transcript.language_code.startswith(lang.split('-')[0]):
                                selected_lang = transcript.language_code
                                break
                        if selected_lang:
                            break

                    # 3. 선호 언어가 없으면 첫 번째 자막 사용
                    if not selected_lang and transcript_list:
                        selected_lang = transcript_list[0].language_code

                    if selected_lang:
                        fetched = api.fetch(video_id, languages=[selected_lang])
                        return self._format_transcript_with_timestamps(fetched)

                except Exception as list_error:
                    # list가 실패하면 직접 fetch 시도
                    for lang in languages:
                        try:
                            fetched = api.fetch(video_id, languages=[lang])
                            return self._format_transcript_with_timestamps(fetched)
                        except Exception:
                            continue

            except Exception as e:
                error_msg = str(e)
                if "Too Many Requests" in error_msg or "429" in error_msg:
                    # Rate limit - 대기 후 재시도
                    if attempt < retry_count - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"  Rate limit 감지. {wait_time}초 대기 후 재시도...")
                        time.sleep(wait_time)
                        continue
                elif "Subtitles are disabled" in error_msg or "No transcripts" in error_msg:
                    # 자막 없음 - 재시도 불필요
                    return None
                else:
                    print(f"자막 추출 실패 ({video_id}): {error_msg[:80]}")
                break

        return None

    def search_videos_by_keyword(self, keyword: str, max_results: int = 50,
                                  published_after_days: int = 30) -> list:
        """키워드로 영상 검색 (개선된 버전)"""
        published_after = (datetime.utcnow() - timedelta(days=published_after_days)).isoformat() + "Z"

        videos = []
        next_page_token = None

        while len(videos) < max_results:
            # 개선된 API 호출
            def api_call():
                return self.youtube.search().list(
                    part="snippet",
                    q=keyword,
                    type="video",
                    order="viewCount",
                    publishedAfter=published_after,
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                ).execute()

            response = self._api_call_with_retry("search.list", api_call)

            if not response:
                break

            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]

                videos.append({
                    "video_id": video_id,
                    "title": snippet["title"],
                    "description": snippet["description"],
                    "channel_id": snippet["channelId"],
                    "channel_title": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"],
                    "thumbnail_url": snippet["thumbnails"]["high"]["url"],
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return videos

    def get_video_details(self, video_ids: list) -> list:
        """영상 상세 정보 (조회수, 좋아요 등) 조회 (개선된 버전)"""
        if not video_ids:
            return []

        # 50개씩 나누어 요청 (API 제한)
        all_details = []
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]

            def api_call():
                return self.youtube.videos().list(
                    part="statistics,contentDetails",
                    id=",".join(batch_ids)
                ).execute()

            response = self._api_call_with_retry("videos.list", api_call)

            if not response:
                continue

            for item in response.get("items", []):
                stats = item.get("statistics", {})
                all_details.append({
                    "video_id": item["id"],
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                    "duration": item["contentDetails"]["duration"],
                })

        return all_details

    def get_channel_videos(self, channel_id: str, max_results: int = 10,
                           published_after_days: int = 30) -> list:
        """특정 채널의 최신 영상 조회"""
        published_after = (datetime.utcnow() - timedelta(days=published_after_days)).isoformat() + "Z"

        try:
            response = self.youtube.search().list(
                part="snippet",
                channelId=channel_id,
                type="video",
                order="date",
                publishedAfter=published_after,
                maxResults=max_results
            ).execute()

            videos = []
            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]

                videos.append({
                    "video_id": video_id,
                    "title": snippet["title"],
                    "description": snippet["description"],
                    "channel_id": channel_id,
                    "channel_title": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"],
                    "thumbnail_url": snippet["thumbnails"]["high"]["url"],
                })

            return videos
        except HttpError as e:
            print(f"채널 영상 조회 오류: {e}")
            return []

    def crawl_store_videos(self, store_key: str, max_per_keyword: int = 20) -> list:
        """특정 매장 관련 영상 수집"""
        if store_key not in STORE_CATEGORIES:
            raise ValueError(f"알 수 없는 매장: {store_key}")

        store = STORE_CATEGORIES[store_key]
        all_videos = []
        seen_ids = set()

        print(f"\n[{store['name']}] 영상 수집 시작...")

        for keyword in store["keywords"]:
            print(f"  키워드 검색: {keyword}")
            videos = self.search_videos_by_keyword(
                keyword,
                max_results=max_per_keyword,
                published_after_days=CRAWL_CONFIG["published_after_days"]
            )

            for video in videos:
                if video["video_id"] not in seen_ids:
                    video["store_key"] = store_key
                    video["store_name"] = store["name"]
                    all_videos.append(video)
                    seen_ids.add(video["video_id"])

        # 조회수 정보 추가
        if all_videos:
            video_ids = [v["video_id"] for v in all_videos]
            details = self.get_video_details(video_ids)
            details_map = {d["video_id"]: d for d in details}

            for video in all_videos:
                if video["video_id"] in details_map:
                    video.update(details_map[video["video_id"]])

        # 조회수 순 정렬
        all_videos.sort(key=lambda x: x.get("view_count", 0), reverse=True)

        print(f"  총 {len(all_videos)}개 영상 수집 완료")
        return all_videos

    def crawl_target_channels(self, store_key: str, max_per_channel: int = 10) -> list:
        """등록된 타겟 채널에서 영상 수집"""
        if store_key not in TARGET_CHANNELS:
            print(f"타겟 채널 없음: {store_key}")
            return []

        channels = TARGET_CHANNELS[store_key]
        all_videos = []
        seen_ids = set()

        store_name = STORE_CATEGORIES.get(store_key, {}).get("name", store_key)
        print(f"\n[{store_name}] 타겟 채널 수집 시작...")

        for channel_info in channels:
            channel_name = channel_info.get("name", "Unknown")
            priority = channel_info.get("priority", 3)

            # 채널 ID 획득
            channel_id = channel_info.get("id")
            if not channel_id and channel_info.get("handle"):
                channel_id = self.get_channel_id_by_handle(channel_info["handle"])
                if channel_id:
                    print(f"  {channel_name} 채널 ID: {channel_id}")

            if not channel_id:
                print(f"  {channel_name} 채널 ID 조회 실패")
                continue

            try:
                videos = self.get_channel_videos(
                    channel_id,
                    max_results=max_per_channel,
                    published_after_days=CRAWL_CONFIG["published_after_days"]
                )

                for video in videos:
                    if video["video_id"] not in seen_ids:
                        video["store_key"] = store_key
                        video["store_name"] = store_name
                        video["source_channel"] = channel_name
                        video["priority"] = priority
                        all_videos.append(video)
                        seen_ids.add(video["video_id"])

                print(f"  {channel_name}: {len(videos)}개 영상")

            except Exception as e:
                print(f"  {channel_name} 수집 오류: {e}")

        # 조회수 정보 추가
        if all_videos:
            video_ids = [v["video_id"] for v in all_videos]
            details = self.get_video_details(video_ids)
            details_map = {d["video_id"]: d for d in details}

            for video in all_videos:
                if video["video_id"] in details_map:
                    video.update(details_map[video["video_id"]])

        # 우선순위 + 조회수 순 정렬
        all_videos.sort(key=lambda x: (-x.get("priority", 3), -x.get("view_count", 0)))

        print(f"  총 {len(all_videos)}개 영상 수집 완료")
        return all_videos

    def crawl_search_keywords(self, store_key: str, max_per_keyword: int = 20) -> list:
        """검색 키워드로 영상 수집"""
        if store_key not in SEARCH_KEYWORDS:
            print(f"검색 키워드 없음: {store_key}")
            return []

        keywords = SEARCH_KEYWORDS[store_key]
        all_videos = []
        seen_ids = set()

        store_name = STORE_CATEGORIES.get(store_key, {}).get("name", store_key)
        print(f"\n[{store_name}] 키워드 검색 시작...")

        for keyword in keywords:
            try:
                print(f"  검색: {keyword}")
                videos = self.search_videos_by_keyword(
                    keyword,
                    max_results=max_per_keyword,
                    published_after_days=CRAWL_CONFIG["published_after_days"]
                )

                for video in videos:
                    if video["video_id"] not in seen_ids:
                        video["store_key"] = store_key
                        video["store_name"] = store_name
                        video["search_keyword"] = keyword
                        all_videos.append(video)
                        seen_ids.add(video["video_id"])

            except Exception as e:
                print(f"  검색 오류 ({keyword}): {e}")

        # 조회수 정보 추가
        if all_videos:
            video_ids = [v["video_id"] for v in all_videos]
            details = self.get_video_details(video_ids)
            details_map = {d["video_id"]: d for d in details}

            for video in all_videos:
                if video["video_id"] in details_map:
                    video.update(details_map[video["video_id"]])

        # 조회수 순 정렬
        all_videos.sort(key=lambda x: x.get("view_count", 0), reverse=True)

        print(f"  총 {len(all_videos)}개 영상 수집 완료")
        return all_videos

    def full_crawl(self, store_key: str = "daiso") -> list:
        """전체 수집 (채널 + 키워드)"""
        all_videos = []
        seen_ids = set()

        # 1. 타겟 채널 수집
        channel_videos = self.crawl_target_channels(store_key)
        for v in channel_videos:
            if v["video_id"] not in seen_ids:
                v["source_type"] = "channel"
                all_videos.append(v)
                seen_ids.add(v["video_id"])

        # 2. 키워드 검색
        keyword_videos = self.crawl_search_keywords(store_key)
        for v in keyword_videos:
            if v["video_id"] not in seen_ids:
                v["source_type"] = "keyword"
                all_videos.append(v)
                seen_ids.add(v["video_id"])

        print(f"\n=== 전체 수집 완료: {len(all_videos)}개 영상 ===")
        return all_videos


def main():
    """테스트 실행"""
    try:
        crawler = YouTubeCrawler()

        # 다이소 관련 영상 수집 테스트
        videos = crawler.crawl_store_videos("daiso", max_per_keyword=10)

        print("\n=== 수집 결과 (상위 10개) ===")
        for i, video in enumerate(videos[:10], 1):
            print(f"\n{i}. {video['title']}")
            print(f"   채널: {video['channel_title']}")
            print(f"   조회수: {video.get('view_count', 'N/A'):,}")
            print(f"   업로드: {video['published_at'][:10]}")
            print(f"   ID: {video['video_id']}")

        # 결과 저장
        output_file = "data/sample_videos.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장됨: {output_file}")

    except ValueError as e:
        print(f"오류: {e}")
        print("\n[YouTube API 키 발급 방법]")
        print("1. https://console.cloud.google.com/ 접속")
        print("2. 프로젝트 생성/선택")
        print("3. API 및 서비스 > 라이브러리 > 'YouTube Data API v3' 활성화")
        print("4. API 및 서비스 > 사용자 인증 정보 > API 키 생성")
        print("5. .env 파일에 YOUTUBE_API_KEY=발급받은키 추가")


if __name__ == "__main__":
    main()
