# 꿀템장바구니 - 시스템 개요

오프라인 매장(다이소, 코스트코, 이케아, 올리브영 등)의 추천 상품을 YouTube/SNS에서 자동 수집하고, 공식 품번과 매칭하여 DB를 구축하는 시스템입니다.

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        데이터 소스                                │
├─────────────────────────────────────────────────────────────────┤
│  YouTube          Instagram       Threads       네이버 블로그    │
│  (API + 자막)     (RapidAPI)      (Meta API)    (네이버 API)     │
└─────────┬───────────────┬─────────────┬─────────────┬───────────┘
          │               │             │             │
          ▼               ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     수집 파이프라인                               │
├─────────────────────────────────────────────────────────────────┤
│  1. 콘텐츠 수집 (영상/게시물)                                     │
│  2. 자막/텍스트 추출                                              │
│  3. AI 상품 추출 (Gemini/GPT)                                    │
│  4. 공식 품번 매칭                                                │
│  5. DB 저장                                                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     데이터베이스                                  │
├─────────────────────────────────────────────────────────────────┤
│  [로컬 개발]         [프로덕션]                                   │
│  SQLite              Supabase (PostgreSQL)                       │
│                      또는 Firebase                                │
├─────────────────────────────────────────────────────────────────┤
│  테이블:                                                          │
│  - videos: 수집된 영상                                            │
│  - products: 추출된 상품                                          │
│  - daiso_catalog: 다이소몰 공식 카탈로그                          │
│  - channels: 모니터링 채널                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 폴더 구조

```
offline-shopping-helper/
├── crawler/                    # 크롤러 모듈
│   ├── config.py              # 설정 (API 키, 타겟 채널 등)
│   ├── database.py            # SQLite 데이터베이스
│   ├── youtube_crawler.py     # YouTube 영상/자막 수집
│   ├── daiso_crawler.py       # 다이소몰 상품 크롤러
│   ├── product_extractor.py   # AI 상품 추출 (Gemini/GPT)
│   ├── product_matcher.py     # 품번 매칭 알고리즘
│   ├── sns_crawler.py         # Instagram/Threads/블로그 크롤러
│   ├── pipeline.py            # 통합 파이프라인
│   └── build_daiso_catalog.py # 다이소 카탈로그 구축
├── admin/                      # 관리자 대시보드
│   └── dashboard.py           # Streamlit 대시보드
├── data/                       # 데이터 저장
│   └── products.db            # SQLite DB
├── .env                        # 환경 변수 (API 키)
└── requirements.txt            # 의존성
```

---

## 주요 컴포넌트

### 1. YouTube 크롤러 (`youtube_crawler.py`)

**기능:**
- 타겟 채널에서 최신 영상 수집
- 키워드로 영상 검색
- 영상 자막 추출
- 조회수/좋아요 등 통계 수집

**타겟 채널 (config.py에 등록):**
```python
TARGET_CHANNELS = {
    "daiso": [
        {"handle": "@살림설렘", "name": "살림설렘", "priority": 1},
        {"handle": "@hejdoo", "name": "헤이두 Hejdoo", "priority": 1},
        {"handle": "@살림연구소오클", "name": "살림연구소 오클", "priority": 1},
        {"id": "UCrlUlicedicJ5mlibqC62Eg", "name": "인씨 (뷰드름)", "priority": 1},
        # ... 더 많은 채널
    ],
    "costco": [...],
    "oliveyoung": [...],
}
```

**사용법:**
```python
from youtube_crawler import YouTubeCrawler

crawler = YouTubeCrawler()

# 타겟 채널에서 수집
videos = crawler.crawl_target_channels("daiso")

# 키워드로 검색
videos = crawler.crawl_search_keywords("daiso")

# 전체 수집 (채널 + 키워드)
videos = crawler.full_crawl("daiso")

# 자막 추출
transcript = crawler.get_video_transcript("video_id")
```

---

### 2. 다이소몰 크롤러 (`daiso_crawler.py`)

**기능:**
- 다이소몰 검색 API로 상품 검색
- 품번, 가격, 카테고리, 리뷰 수, 주문 수 등 수집
- 상품명 유사도 기반 매칭

**API 엔드포인트:**
```
검색: https://www.daisomall.co.kr/ssn/search/SearchGoods
상품: https://www.daisomall.co.kr/pd/pdr/SCR_PDR_0001?pdNo={품번}
```

**사용법:**
```python
from daiso_crawler import DaisoCrawler

crawler = DaisoCrawler()

# 키워드 검색
products = crawler.search("배수구망", max_results=20)

# 상품명 매칭
match = crawler.search_and_match("스텐 배수구망", threshold=0.5)
```

---

### 3. AI 상품 추출기 (`product_extractor.py`)

**기능:**
- 영상 자막에서 추천 상품 추출
- Gemini (무료) 또는 GPT 사용
- JSON 형식으로 상품 정보 파싱

**추출 정보:**
- 상품명
- 가격
- 카테고리
- 추천 이유
- 타임스탬프
- 검색 키워드

**사용법:**
```python
from product_extractor import ProductExtractor

extractor = ProductExtractor(provider="gemini")  # 또는 "openai"

products = extractor.extract_products(
    transcript="오늘 소개할 다이소 꿀템은 스텐 배수구망이에요...",
    store_name="다이소"
)
# Returns: [{"name": "스텐 배수구망", "price": 2000, ...}]
```

---

### 4. 상품 매칭기 (`product_matcher.py`)

**기능:**
- YouTube 상품명을 다이소몰 품번과 매칭
- 로컬 카탈로그 DB 우선 검색
- 매칭 실패 시 API 실시간 검색

**매칭 알고리즘:**
1. 단어 겹침 (Jaccard 유사도)
2. 부분 문자열 포함
3. 가격 일치 보너스
4. 인기도(주문 수) 보너스

**사용법:**
```python
from product_matcher import ProductMatcher

matcher = ProductMatcher()

result = matcher.match_product(
    product_name="스텐 배수구망",
    price=2000,
    keywords=["배수구", "스텐"]
)
# Returns: {"product_code": "1043198", "official_name": "스텐 304 배수구망 13.5cm", ...}
```

---

### 5. SNS 크롤러 (`sns_crawler.py`)

**지원 플랫폼:**
- Instagram (RapidAPI 또는 Graph API)
- Threads (Meta API)
- 네이버 블로그 (네이버 검색 API)

**사용법:**
```python
from sns_crawler import SNSCollector

config = {
    "instagram_api_key": "your_rapidapi_key",
    "naver_client_id": "your_id",
    "naver_client_secret": "your_secret",
}

collector = SNSCollector(config)
posts = collector.collect_by_store("daiso", platforms=["instagram", "naver_blog"])
```

---

### 6. 통합 파이프라인 (`pipeline.py`)

**전체 워크플로우:**
1. YouTube 영상 수집 (채널 + 키워드)
2. 자막 추출
3. AI 상품 추출
4. 다이소몰 매칭
5. DB 저장

**사용법:**
```python
from pipeline import DataPipeline

pipeline = DataPipeline()
result = pipeline.run_full_pipeline("daiso", max_videos=10)

# 결과
# {
#     "videos_collected": 50,
#     "products_extracted": 120,
#     "products_matched": 85,
#     "elapsed_seconds": 180
# }
```

---

## 데이터베이스 스키마

### videos 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| video_id | TEXT | YouTube 영상 ID |
| title | TEXT | 영상 제목 |
| channel_id | TEXT | 채널 ID |
| channel_title | TEXT | 채널명 |
| view_count | INTEGER | 조회수 |
| transcript | TEXT | 자막 텍스트 |
| store_key | TEXT | 매장 키 (daiso, costco 등) |
| status | TEXT | 처리 상태 |

### products 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| name | TEXT | 상품명 (YouTube에서 추출) |
| price | INTEGER | 가격 |
| category | TEXT | 카테고리 |
| reason | TEXT | 추천 이유 |
| video_id | TEXT | 출처 영상 ID |
| official_code | TEXT | 다이소몰 품번 |
| official_name | TEXT | 공식 상품명 |
| official_price | INTEGER | 공식 가격 |
| is_matched | INTEGER | 매칭 여부 |
| source_view_count | INTEGER | 출처 영상 조회수 |

### daiso_catalog 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| product_no | TEXT | 품번 (PK) |
| name | TEXT | 상품명 |
| price | INTEGER | 가격 |
| category_large | TEXT | 대분류 |
| category_middle | TEXT | 중분류 |
| order_count | INTEGER | 주문 수 |
| rating | REAL | 평점 |
| is_best | INTEGER | 베스트 상품 |

---

## API 키 설정

### .env 파일
```env
# YouTube Data API v3
YOUTUBE_API_KEY=AIzaSy...

# AI (하나 이상 필수)
GEMINI_API_KEY=AIzaSy...      # 권장 (무료 티어 있음)
OPENAI_API_KEY=sk-...

# SNS (선택)
INSTAGRAM_API_KEY=...          # RapidAPI
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

### API 키 발급 안내

1. **YouTube Data API v3**
   - https://console.cloud.google.com/
   - API 및 서비스 > YouTube Data API v3 활성화
   - 사용자 인증 정보 > API 키 생성

2. **Gemini API (권장)**
   - https://makersuite.google.com/app/apikey
   - 무료 티어: 분당 60회 요청

3. **네이버 검색 API**
   - https://developers.naver.com/
   - 애플리케이션 등록 > 블로그 검색 선택

4. **Instagram (RapidAPI)**
   - https://rapidapi.com/hub
   - "Instagram Scraper" 검색

---

## 실행 방법

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 다이소 카탈로그 구축 (최초 1회)
```bash
cd crawler
python build_daiso_catalog.py
# 또는 테스트
python build_daiso_catalog.py test
```

### 3. 수집 파이프라인 실행
```bash
cd crawler
python pipeline.py
# 또는 특정 매장
python pipeline.py --store=daiso --max-videos=10
```

### 4. 관리자 대시보드
```bash
streamlit run admin/dashboard.py
```

---

## 클라우드 DB 추천

### Supabase (권장)
- PostgreSQL 기반
- 무료 티어: 500MB, 2개 프로젝트
- 실시간 구독 지원
- REST API 자동 생성
- https://supabase.com/

**설정:**
```python
from supabase import create_client

supabase = create_client(
    "https://xxx.supabase.co",
    "your-anon-key"
)

# 상품 저장
supabase.table("products").insert(product_data).execute()
```

### Firebase Firestore
- NoSQL 문서 DB
- 무료 티어: 1GB, 일 50K 읽기
- 실시간 동기화
- https://firebase.google.com/

### 스프레드시트 (간단한 경우)
- Google Sheets API
- 소규모 데이터에 적합
- 공유/편집 쉬움

---

## 자동화 스케줄러

### Windows Task Scheduler
```powershell
# 매일 오전 9시 실행
schtasks /create /tn "꿀템수집" /tr "python C:\path\to\pipeline.py" /sc daily /st 09:00
```

### Linux cron
```bash
# 매일 오전 9시 실행
0 9 * * * cd /path/to/crawler && python pipeline.py >> /var/log/crawler.log 2>&1
```

### GitHub Actions
```yaml
name: Daily Collection
on:
  schedule:
    - cron: '0 0 * * *'  # 매일 UTC 0시
jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: pip install -r requirements.txt
      - run: python crawler/pipeline.py
```

---

## 성능 최적화

### 1. 병렬 처리
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(process_video, videos))
```

### 2. 캐싱
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def search_daiso_catalog(keyword):
    ...
```

### 3. 배치 처리
- 다이소몰 카탈로그: 키워드별 배치 수집
- AI 추출: 영상 배치로 API 호출 최소화
- DB 저장: 트랜잭션 배치 삽입

### 4. Rate Limiting
```python
import time
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=60, period=60)  # 분당 60회
def call_api():
    ...
```

---

## 현재 구현 상태

| 기능 | 상태 | 비고 |
|------|------|------|
| 다이소몰 크롤러 | ✅ 완료 | API 방식, 460개 상품 수집됨 |
| YouTube 크롤러 | ✅ 완료 | 채널/키워드 기반 |
| AI 상품 추출 | ✅ 완료 | Gemini/GPT 지원 |
| 품번 매칭 | ✅ 완료 | 유사도 기반 |
| 통합 파이프라인 | ✅ 완료 | 5단계 자동화 |
| Instagram 크롤러 | ⚠️ 구현됨 | API 키 필요 |
| Threads 크롤러 | ⚠️ 구현됨 | API 제한적 |
| 네이버 블로그 | ⚠️ 구현됨 | API 키 필요 |
| 클라우드 DB | 📋 계획 | Supabase 권장 |
| 자동 스케줄러 | 📋 계획 | GitHub Actions |

---

## 다음 단계

1. **API 키 설정**: YouTube, Gemini API 키 발급
2. **카탈로그 확장**: 더 많은 키워드로 다이소 상품 수집
3. **파이프라인 실행**: 실제 데이터 수집 테스트
4. **클라우드 DB**: Supabase 설정 및 마이그레이션
5. **SNS 수집**: Instagram/네이버 블로그 API 연동
6. **자동화**: 일일 수집 스케줄러 설정
