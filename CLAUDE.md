# 꿀템장바구니 (Offline Shopping Helper)

YouTube 인플루언서 추천 상품 자동 수집 및 추천 시스템

## Project Structure

```
├── crawler/           # Python 크롤러
│   ├── pipeline.py    # 메인 파이프라인
│   ├── youtube_crawler.py
│   ├── gemini_extractor.py
│   ├── improved_database.py
│   └── config.py      # 매장 설정
├── web/               # Next.js 14 PWA
│   ├── app/           # App Router
│   ├── components/
│   └── public/data/   # JSON 데이터
├── android/           # TWA Android 앱
└── .github/workflows/ # CI/CD
```

## Agent Team Configuration

이 프로젝트는 다음 전문 에이전트를 사용합니다:

| Agent | 역할 | 사용 시점 |
|-------|------|----------|
| `crawler-agent` | 크롤러/데이터 파이프라인 | 크롤링 이슈, 새 매장 추가 |
| `backend-analyzer` | API 분석 | API 라우트 검토 |
| `ui-reviewer` | UI/접근성 검토 | UI 변경 후 |
| `security-analyzer` | 보안 분석 | 보안 민감 코드 |
| `devops-specialist` | CI/CD/배포 | 워크플로우 검토 |
| `qa-tester` | 테스트 | 기능 구현 후 |

## Stores

| Key | Name | Status |
|-----|------|--------|
| daiso | 다이소 | Active |
| costco | 코스트코 | Active |
| ikea | 이케아 | Active |
| oliveyoung | 올리브영 | Active |
| traders | 트레이더스 | Active |
| convenience | 편의점 | Active |
| cu | CU | Active |
| gs25 | GS25 | Active |
| seveneleven | 세븐일레븐 | Active |
| emart24 | 이마트24 | Active |

## Key Commands

```bash
# 크롤러 실행
cd crawler && python pipeline.py daiso

# 웹 개발 서버
cd web && npm run dev

# JSON 동기화
cd crawler && python sync_to_github.py
```

## CI/CD

- **auto-crawl.yml**: 매일 2회 (9am/9pm KST) 자동 크롤링
- **deploy-nas.yml**: NAS Docker 배포
- **backfill-timestamps.yml**: 타임스탬프 백필

## Notes

- AWS S3 Region: `ap-southeast-2`
- Database: SQLite (`data/products.db`)
- API Keys: GitHub Secrets에서 관리
