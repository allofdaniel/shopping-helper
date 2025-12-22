# 꿀템장바구니 (Offline Shopping Helper)

오프라인 매장 꿀템 추천 앱 - 유튜버/인플루언서 추천 상품 데이터 수집 및 큐레이션

## 프로젝트 구조

```
offline-shopping-helper/
├── crawler/              # 데이터 수집 파이프라인
│   ├── youtube_crawler.py    # YouTube 영상 수집
│   ├── transcript_extractor.py # 자막 추출
│   ├── ai_analyzer.py        # AI 상품 정보 추출
│   ├── store_matcher.py      # 매장별 상품 매칭
│   └── config.py             # 설정 및 API 키
├── data/                 # 수집된 데이터
│   └── products.db          # SQLite 데이터베이스
├── admin/                # 관리자 대시보드
│   └── dashboard.py         # 검수용 웹 인터페이스
└── app/                  # Flutter 앱 (추후)
```

## 타겟 매장

1. **다이소 (Daiso)** - 생활용품/가성비
2. **코스트코/트레이더스** - 식품/대용량
3. **이케아 (IKEA)** - 가구/리빙
4. **올리브영** - 뷰티/헬스

## 데이터 파이프라인

```
[YouTube 채널 모니터링]
        ↓
[신규 영상 감지 + 메타데이터 수집]
        ↓
[자막(Script) 추출]
        ↓
[AI 분석 → 상품 리스트 JSON 추출]
        ↓
[매장 API로 품번/공식 이미지 매칭]
        ↓
[관리자 검수]
        ↓
[DB 저장 → 앱 노출]
```

## 설정 방법

### 1. YouTube Data API 키 발급

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. API 및 서비스 > 라이브러리 > "YouTube Data API v3" 검색 후 활성화
4. API 및 서비스 > 사용자 인증 정보 > API 키 생성
5. `.env` 파일에 추가

### 2. 환경 설정

```bash
cd crawler
pip install -r requirements.txt
cp .env.example .env
# .env 파일에 API 키 입력
```

### 3. 실행

```bash
python youtube_crawler.py
```

## 기술 스택

- **언어:** Python 3.9+
- **수집:** YouTube Data API v3, youtube_transcript_api
- **분석:** OpenAI GPT-4o / Google Gemini
- **DB:** SQLite (개발) → Supabase/Firebase (프로덕션)
- **앱:** Flutter (iOS/Android)
