# 꿀템장바구니 - 설정 가이드

## 1. API 키 발급

### YouTube Data API v3 (필수)

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성 또는 선택
3. **API 및 서비스** > **라이브러리** 클릭
4. "YouTube Data API v3" 검색 후 **사용** 클릭
5. **API 및 서비스** > **사용자 인증 정보** 클릭
6. **+ 사용자 인증 정보 만들기** > **API 키** 선택
7. 생성된 API 키 복사

> 💡 **무료 할당량:** 일 10,000 유닛 (영상 검색 약 100회 = 100 유닛)

### Google Gemini API (필수)

1. [Google AI Studio](https://aistudio.google.com/) 접속
2. 좌측 **Get API Key** 클릭
3. **Create API Key** 버튼 클릭
4. 프로젝트 선택 후 키 생성
5. 생성된 API 키 복사

> 💡 **무료 할당량:** 분당 15 요청, 일 1,500 요청

### OpenAI API (대안)

1. [OpenAI Platform](https://platform.openai.com/) 접속
2. **API Keys** > **Create new secret key**
3. 생성된 키 복사

> ⚠️ 유료 서비스 (GPT-4o-mini: 약 $0.15/1M 입력 토큰)

---

## 2. 환경 설정

### 2-1. Python 환경 준비

```bash
# 프로젝트 폴더로 이동
cd "C:\Users\allof\Desktop\code\make money\app-portfolio\apps\offline-shopping-helper"

# 가상환경 생성 (권장)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 패키지 설치
pip install -r crawler/requirements.txt
```

### 2-2. API 키 설정

```bash
# .env 파일 생성
cd crawler
copy .env.example .env
```

`.env` 파일을 편집하여 API 키 입력:

```env
YOUTUBE_API_KEY=AIzaSy...발급받은키
GEMINI_API_KEY=AIzaSy...발급받은키
# OPENAI_API_KEY=sk-...  # Gemini 대신 사용시
```

---

## 3. 실행 방법

### 3-1. 테스트 실행 (API 키 없이)

```bash
cd crawler
python pipeline.py --test
```

샘플 데이터로 파이프라인 동작 확인

### 3-2. 실제 데이터 수집

```bash
cd crawler
python pipeline.py
```

다이소 관련 YouTube 영상 수집 → 자막 추출 → AI 분석 → DB 저장

### 3-3. 관리자 대시보드

```bash
cd admin
streamlit run dashboard.py
```

브라우저에서 `http://localhost:8501` 접속

---

## 4. 파이프라인 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Pipeline Flow                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [1] YouTube 검색                                            │
│      └── "다이소 꿀템", "다이소 추천" 등 키워드 검색           │
│      └── 조회수 순 정렬, 최근 30일 영상                       │
│                                                              │
│  [2] 자막 추출                                               │
│      └── youtube_transcript_api로 한국어 자막 다운로드        │
│      └── 자막 없는 영상은 스킵                               │
│                                                              │
│  [3] AI 분석 (Gemini)                                        │
│      └── 자막에서 상품명, 가격, 추천 이유 추출                │
│      └── JSON 형태로 구조화                                  │
│                                                              │
│  [4] 매장 매칭                                               │
│      └── 다이소몰에서 품번, 공식 이미지 검색                  │
│      └── 매칭 실패 시 영상 썸네일 사용                       │
│                                                              │
│  [5] DB 저장 + 관리자 승인                                   │
│      └── 승인된 상품만 앱에 노출                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 다음 단계

### Phase 1 완료 체크리스트

- [x] YouTube 크롤러 구현
- [x] 자막 추출기 구현
- [x] AI 분석기 구현 (Gemini)
- [x] 매장 상품 매칭 모듈
- [x] SQLite 데이터베이스
- [x] 관리자 대시보드 (Streamlit)

### Phase 2 예정

- [ ] 스케줄러 추가 (매일 자동 수집)
- [ ] Supabase 연동 (클라우드 DB)
- [ ] Flutter 앱 개발
- [ ] 추가 매장 지원 (이케아, 올리브영)

### Phase 3 예정

- [ ] 사용자 찜 기능
- [ ] 매장 위치 연동
- [ ] 재고 조회 연동
- [ ] 푸시 알림 (신규 꿀템)

---

## 6. 트러블슈팅

### YouTube API 할당량 초과

```
googleapiclient.errors.HttpError: quotaExceeded
```

→ 일일 할당량(10,000) 초과. 다음날 자동 초기화

### 자막 추출 실패

```
youtube_transcript_api._errors.TranscriptsDisabled
```

→ 해당 영상에 자막이 없음. 자동으로 스킵됨

### Gemini API 오류

```
google.api_core.exceptions.ResourceExhausted
```

→ 분당 요청 한도 초과. 1분 후 재시도

---

## 7. 폴더 구조

```
offline-shopping-helper/
├── README.md              # 프로젝트 개요
├── SETUP_GUIDE.md         # 이 문서
├── crawler/               # 데이터 수집 모듈
│   ├── config.py          # 설정 및 API 키
│   ├── youtube_crawler.py # YouTube 영상 수집
│   ├── transcript_extractor.py # 자막 추출
│   ├── ai_analyzer.py     # AI 상품 추출
│   ├── store_matcher.py   # 매장 상품 매칭
│   ├── database.py        # DB 모듈
│   ├── pipeline.py        # 통합 파이프라인
│   ├── requirements.txt   # 의존성
│   └── .env               # API 키 (gitignore)
├── admin/                 # 관리자 도구
│   └── dashboard.py       # Streamlit 대시보드
├── data/                  # 수집 데이터
│   └── products.db        # SQLite DB
└── app/                   # Flutter 앱 (추후)
```
