"""
꿀템장바구니 - YouTube 크롤러
유튜브 채널에서 신규 영상을 감지하고 메타데이터를 수집합니다.
"""
import json
import re
from datetime import datetime, timedelta
from typing import Optional
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


class YouTubeCrawler:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or YOUTUBE_API_KEY
        if not self.api_key:
            raise ValueError("YouTube API 키가 필요합니다. .env 파일을 확인하세요.")
        self.youtube = build("youtube", "v3", developerKey=self.api_key)

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

    def get_video_transcript(self, video_id: str, languages: list = None,
                               retry_count: int = 3, retry_delay: float = 2.0) -> Optional[str]:
        """영상 자막 추출 (Rate limiting 대응)"""
        if not TRANSCRIPT_AVAILABLE:
            return None

        if languages is None:
            languages = ["ko", "ko-KR", "en"]

        for attempt in range(retry_count):
            try:
                # 1. list_transcripts로 사용 가능한 자막 먼저 확인
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

                # 2. 선호 언어 순서로 자막 찾기
                transcript = None
                for lang in languages:
                    try:
                        transcript = transcript_list.find_transcript([lang])
                        break
                    except Exception:
                        continue

                # 3. 없으면 자동 생성 자막 시도
                if transcript is None:
                    try:
                        transcript = transcript_list.find_generated_transcript(languages)
                    except Exception:
                        # 아무 자막이나 가져와서 번역
                        for t in transcript_list:
                            try:
                                transcript = t.translate("ko")
                                break
                            except Exception:
                                transcript = t
                                break

                if transcript:
                    entries = transcript.fetch()
                    text = " ".join([entry["text"] for entry in entries])
                    return text

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
        """키워드로 영상 검색"""
        published_after = (datetime.utcnow() - timedelta(days=published_after_days)).isoformat() + "Z"

        try:
            videos = []
            next_page_token = None

            while len(videos) < max_results:
                response = self.youtube.search().list(
                    part="snippet",
                    q=keyword,
                    type="video",
                    order="viewCount",  # 조회수 순
                    publishedAfter=published_after,
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                ).execute()

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
        except HttpError as e:
            print(f"영상 검색 오류: {e}")
            return []

    def get_video_details(self, video_ids: list) -> list:
        """영상 상세 정보 (조회수, 좋아요 등) 조회"""
        if not video_ids:
            return []

        try:
            # 50개씩 나누어 요청 (API 제한)
            all_details = []
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                response = self.youtube.videos().list(
                    part="statistics,contentDetails",
                    id=",".join(batch_ids)
                ).execute()

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
        except HttpError as e:
            print(f"영상 상세 정보 조회 오류: {e}")
            return []

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
