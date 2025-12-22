# -*- coding: utf-8 -*-
"""
SNS 크롤러 - Instagram, Threads, 블로그 등
다양한 소셜 미디어에서 상품 추천 콘텐츠를 수집합니다.

주의: Instagram/Threads는 공식 API가 제한적이므로
- Instagram Graph API (비즈니스 계정 필요)
- Apify 같은 서드파티 서비스
- 해시태그 검색 기반 수집
등의 방법을 사용합니다.
"""
import json
import time
import re
import requests
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from config import DATA_DIR


@dataclass
class SocialPost:
    """소셜 미디어 게시물"""
    post_id: str
    platform: str  # instagram, threads, naver_blog, etc
    author: str
    author_id: str = ""
    content: str = ""
    image_urls: list = None
    video_url: str = ""
    likes: int = 0
    comments: int = 0
    shares: int = 0
    posted_at: str = ""
    url: str = ""
    hashtags: list = None
    store_key: str = ""
    store_name: str = ""

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []
        if self.hashtags is None:
            self.hashtags = []

    def to_dict(self):
        return asdict(self)


class BaseSNSCrawler(ABC):
    """SNS 크롤러 베이스 클래스"""

    @abstractmethod
    def search_by_hashtag(self, hashtag: str, limit: int = 20) -> list[SocialPost]:
        """해시태그로 검색"""
        pass

    @abstractmethod
    def get_user_posts(self, user_id: str, limit: int = 10) -> list[SocialPost]:
        """특정 사용자의 게시물 가져오기"""
        pass


class InstagramCrawler(BaseSNSCrawler):
    """
    Instagram 크롤러

    방법 1: Instagram Graph API (비즈니스/크리에이터 계정 필요)
    방법 2: Apify Actor (유료, 안정적)
    방법 3: RapidAPI Instagram Scrapers (유료)

    여기서는 RapidAPI 기반 예시를 제공합니다.
    """

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: RapidAPI 키 또는 Apify 토큰
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def search_by_hashtag(self, hashtag: str, limit: int = 20) -> list[SocialPost]:
        """
        해시태그로 Instagram 게시물 검색

        참고: Instagram 공식 API는 해시태그 검색을 지원하지 않음
        RapidAPI의 Instagram Scraper 등을 사용해야 함
        """
        posts = []

        if not self.api_key:
            print("[Instagram] API 키가 필요합니다.")
            print("  RapidAPI: https://rapidapi.com/hub")
            print("  Apify: https://apify.com/")
            return posts

        # RapidAPI Instagram Scraper 예시
        # 실제 사용 시 해당 API 문서 참조
        try:
            url = "https://instagram-scraper-api2.p.rapidapi.com/v1/hashtag"
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
            }
            params = {"hashtag": hashtag.lstrip("#")}

            response = self.session.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("data", {}).get("items", [])[:limit]:
                    post = self._parse_instagram_post(item)
                    if post:
                        posts.append(post)

        except Exception as e:
            print(f"[Instagram] 검색 오류: {e}")

        return posts

    def get_user_posts(self, user_id: str, limit: int = 10) -> list[SocialPost]:
        """특정 사용자의 게시물 가져오기"""
        posts = []

        if not self.api_key:
            return posts

        # 구현 필요 (API에 따라 다름)
        return posts

    def _parse_instagram_post(self, item: dict) -> Optional[SocialPost]:
        """Instagram 게시물 파싱"""
        try:
            caption = item.get("caption", {})
            return SocialPost(
                post_id=item.get("id", ""),
                platform="instagram",
                author=item.get("user", {}).get("username", ""),
                author_id=item.get("user", {}).get("id", ""),
                content=caption.get("text", "") if caption else "",
                image_urls=[item.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")],
                likes=item.get("like_count", 0),
                comments=item.get("comment_count", 0),
                posted_at=datetime.fromtimestamp(item.get("taken_at", 0)).isoformat(),
                url=f"https://www.instagram.com/p/{item.get('code', '')}/",
                hashtags=self._extract_hashtags(caption.get("text", "") if caption else ""),
            )
        except Exception:
            return None

    def _extract_hashtags(self, text: str) -> list:
        """텍스트에서 해시태그 추출"""
        return re.findall(r'#(\w+)', text)


class ThreadsCrawler(BaseSNSCrawler):
    """
    Threads 크롤러

    Threads API는 2024년부터 제공되기 시작
    현재는 제한적인 기능만 지원
    """

    def __init__(self, access_token: str = None):
        self.access_token = access_token
        self.base_url = "https://graph.threads.net/v1.0"

    def search_by_hashtag(self, hashtag: str, limit: int = 20) -> list[SocialPost]:
        """
        Threads는 현재 해시태그 검색 API를 제공하지 않음
        향후 업데이트 예정
        """
        print("[Threads] 해시태그 검색 API 미지원")
        return []

    def get_user_posts(self, user_id: str, limit: int = 10) -> list[SocialPost]:
        """사용자 게시물 가져오기 (API 토큰 필요)"""
        posts = []

        if not self.access_token:
            print("[Threads] Access Token이 필요합니다.")
            return posts

        try:
            url = f"{self.base_url}/{user_id}/threads"
            params = {
                "access_token": self.access_token,
                "fields": "id,text,timestamp,permalink,like_count,reply_count",
                "limit": limit
            }

            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("data", []):
                    post = SocialPost(
                        post_id=item.get("id", ""),
                        platform="threads",
                        author=user_id,
                        content=item.get("text", ""),
                        likes=item.get("like_count", 0),
                        comments=item.get("reply_count", 0),
                        posted_at=item.get("timestamp", ""),
                        url=item.get("permalink", ""),
                        hashtags=self._extract_hashtags(item.get("text", "")),
                    )
                    posts.append(post)

        except Exception as e:
            print(f"[Threads] 오류: {e}")

        return posts

    def _extract_hashtags(self, text: str) -> list:
        return re.findall(r'#(\w+)', text)


class NaverBlogCrawler(BaseSNSCrawler):
    """
    네이버 블로그 크롤러 (검색 API 사용)

    네이버 개발자센터에서 API 키 발급 필요:
    https://developers.naver.com/
    """

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.search_url = "https://openapi.naver.com/v1/search/blog.json"

    def search_by_hashtag(self, hashtag: str, limit: int = 20) -> list[SocialPost]:
        """키워드로 블로그 검색 (해시태그 대신)"""
        return self.search(hashtag, limit)

    def search(self, query: str, limit: int = 20) -> list[SocialPost]:
        """블로그 검색"""
        posts = []

        if not self.client_id or not self.client_secret:
            print("[NaverBlog] API 키가 필요합니다.")
            print("  https://developers.naver.com/ 에서 발급")
            return posts

        try:
            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret
            }
            params = {
                "query": query,
                "display": min(limit, 100),
                "sort": "date"  # sim (정확도) 또는 date (날짜순)
            }

            response = requests.get(self.search_url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    # HTML 태그 제거
                    title = re.sub(r'<[^>]+>', '', item.get("title", ""))
                    description = re.sub(r'<[^>]+>', '', item.get("description", ""))

                    post = SocialPost(
                        post_id=item.get("link", "").split("/")[-1],
                        platform="naver_blog",
                        author=item.get("bloggername", ""),
                        content=f"{title}\n\n{description}",
                        posted_at=item.get("postdate", ""),
                        url=item.get("link", ""),
                        hashtags=[],
                    )
                    posts.append(post)

        except Exception as e:
            print(f"[NaverBlog] 검색 오류: {e}")

        return posts

    def get_user_posts(self, user_id: str, limit: int = 10) -> list[SocialPost]:
        """특정 블로거의 게시물 (별도 구현 필요)"""
        return []


class SNSCollector:
    """통합 SNS 수집기"""

    # 매장별 검색 해시태그/키워드
    SEARCH_KEYWORDS = {
        "daiso": {
            "instagram": ["#다이소추천", "#다이소꿀템", "#다이소신상", "#다이소살림템", "#다이소화장품"],
            "threads": ["다이소 추천", "다이소 꿀템"],
            "naver_blog": ["다이소 추천템", "다이소 꿀템 리뷰", "다이소 신상품"],
        },
        "costco": {
            "instagram": ["#코스트코추천", "#코스트코꿀템", "#코스트코쇼핑"],
            "threads": ["코스트코 추천"],
            "naver_blog": ["코스트코 추천 상품", "코스트코 꿀템"],
        },
        "oliveyoung": {
            "instagram": ["#올리브영추천", "#올영세일", "#올리브영꿀템"],
            "threads": ["올리브영 추천"],
            "naver_blog": ["올리브영 추천템", "올리브영 세일"],
        },
    }

    def __init__(self, config: dict = None):
        """
        Args:
            config: API 키 설정
                {
                    "instagram_api_key": "...",
                    "threads_token": "...",
                    "naver_client_id": "...",
                    "naver_client_secret": "...",
                }
        """
        config = config or {}

        self.crawlers = {
            "instagram": InstagramCrawler(api_key=config.get("instagram_api_key")),
            "threads": ThreadsCrawler(access_token=config.get("threads_token")),
            "naver_blog": NaverBlogCrawler(
                client_id=config.get("naver_client_id"),
                client_secret=config.get("naver_client_secret")
            ),
        }

    def collect_by_store(self, store_key: str, platforms: list = None,
                         limit_per_keyword: int = 10) -> list[SocialPost]:
        """
        매장별 SNS 콘텐츠 수집

        Args:
            store_key: 매장 키 (daiso, costco, etc)
            platforms: 수집할 플랫폼 리스트 (None이면 전체)
            limit_per_keyword: 키워드당 최대 수집 수

        Returns:
            수집된 게시물 리스트
        """
        if store_key not in self.SEARCH_KEYWORDS:
            print(f"[SNS] 알 수 없는 매장: {store_key}")
            return []

        if platforms is None:
            platforms = list(self.crawlers.keys())

        all_posts = []
        seen_ids = set()

        store_keywords = self.SEARCH_KEYWORDS[store_key]

        for platform in platforms:
            if platform not in self.crawlers:
                continue

            crawler = self.crawlers[platform]
            keywords = store_keywords.get(platform, [])

            print(f"\n[{platform.upper()}] 수집 시작...")

            for keyword in keywords:
                try:
                    posts = crawler.search_by_hashtag(keyword, limit=limit_per_keyword)

                    for post in posts:
                        if post.post_id not in seen_ids:
                            post.store_key = store_key
                            all_posts.append(post)
                            seen_ids.add(post.post_id)

                    print(f"  {keyword}: {len(posts)}개")
                    time.sleep(1)  # Rate limiting

                except Exception as e:
                    print(f"  {keyword}: 오류 - {e}")

        print(f"\n총 {len(all_posts)}개 게시물 수집됨")
        return all_posts

    def save_to_json(self, posts: list[SocialPost], filename: str = None):
        """수집 결과 JSON 저장"""
        if filename is None:
            filename = DATA_DIR / f"sns_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        data = [p.to_dict() for p in posts]
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"저장됨: {filename}")
        return filename


def main():
    """테스트"""
    print("=== SNS 크롤러 테스트 ===\n")

    # 설정 (실제 사용 시 .env에서 로드)
    config = {
        # "instagram_api_key": "your_rapidapi_key",
        # "naver_client_id": "your_naver_id",
        # "naver_client_secret": "your_naver_secret",
    }

    collector = SNSCollector(config)

    # 네이버 블로그만 테스트 (무료)
    print("\n[네이버 블로그 검색 테스트]")
    blog_crawler = collector.crawlers["naver_blog"]

    if blog_crawler.client_id:
        posts = blog_crawler.search("다이소 추천템", limit=5)
        for post in posts:
            print(f"\n- {post.author}")
            print(f"  {post.content[:100]}...")
            print(f"  {post.url}")
    else:
        print("  -> 네이버 API 키 필요")
        print("  -> https://developers.naver.com/ 에서 발급")

    print("\n\n[Instagram/Threads 크롤링 방법]")
    print("1. Instagram Graph API (비즈니스 계정)")
    print("   - Meta for Developers: https://developers.facebook.com/")
    print("   - 비즈니스/크리에이터 계정 필요")

    print("\n2. RapidAPI (유료, 간편)")
    print("   - https://rapidapi.com/hub")
    print("   - 'Instagram Scraper' 검색")

    print("\n3. Apify (유료, 안정적)")
    print("   - https://apify.com/")
    print("   - Instagram Scraper Actor 사용")


if __name__ == "__main__":
    main()
