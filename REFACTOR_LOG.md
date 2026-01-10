# 꿀템장바구니 크롤러 리팩토링 로그

## 작업 시작일: 2025-12-28

---

## 1. 현재 시스템 문제점 분석

### 1.1 핵심 문제
영상 내용과 추출된 추천 제품이 일치하지 않음

### 1.2 원인 분석 (9가지 치명적 이슈)

| 이슈 | 파일 | 라인 | 심각도 | 영향 |
|------|------|------|--------|------|
| 폴백 자막이 너무 짧음 | pipeline.py | 108-114 | Critical | <100자 텍스트로 AI 실패 |
| 자막 검증 없음 | pipeline.py | 102-114 | High | 빈 설명 우회 |
| AI 컨텍스트 필터링 없음 | product_extractor.py | 85-91 | High | 환각/부정적 추출 |
| 취약한 JSON 파싱 | product_extractor.py | 131-157 | Medium | 엣지 케이스 실패 |
| 매칭 임계값=20 너무 낮음 | product_matcher.py | 169 | Critical | 오탐 매칭 |
| 가격 범위 검증 없음 | product_matcher.py | 146-151 | High | 같은 가격 다른 상품 |
| 중복 제약조건 없음 | database.py | 55-84 | High | 데이터 중복 |
| 유니크 인덱스 없음 | database.py | INSERT | High | 동일 항목 다중 입력 |
| 불충분한 불용어 | product_matcher.py | 111 | Medium | 변형 철자 오매칭 |

### 1.3 데이터 흐름 분석

```
현재 흐름 (문제 있음):
YouTube 영상 → 자막 추출 (실패 시 제목+설명 사용) → AI 추출 → 매칭 → DB 저장
                    ↓
            50자 미만 텍스트도 처리
                    ↓
            AI가 추측으로 상품 생성 (환각)
                    ↓
            낮은 임계값(20점)으로 오매칭
                    ↓
            영상과 무관한 상품이 연결됨
```

---

## 2. TDD 기반 재설계 계획

### 2.1 새로운 아키텍처

```
Phase 1: 영상 수집 & 검증
  └─ YouTube API로 영상 메타데이터 수집
  └─ 자막 추출 (자동/수동)
  └─ [NEW] 자막 품질 검증 (최소 300자, 상품 언급 확인)

Phase 2: 상품 추출 (AI)
  └─ [NEW] 개선된 프롬프트 (맥락 이해, 부정 리뷰 필터)
  └─ [NEW] 신뢰도 점수 반환
  └─ [NEW] 중복 제거

Phase 3: 상품 매칭
  └─ [NEW] 높은 임계값 (40점 이상)
  └─ [NEW] 다단계 검증 (이름 + 가격 + 카테고리)
  └─ [NEW] 신뢰도 낮으면 수동 검토 플래그

Phase 4: 저장 & 검증
  └─ [NEW] UNIQUE 제약조건 (video_id, name, price)
  └─ [NEW] 품질 메트릭 로깅
```

### 2.2 테스트 우선 개발 (TDD)

1. **단위 테스트**: 각 컴포넌트 독립 테스트
2. **통합 테스트**: 파이프라인 전체 흐름 테스트
3. **E2E 테스트**: 실제 영상으로 정확도 검증

---

## 3. 구현 진행 상황

### 3.1 Phase 1: 테스트 프레임워크 구축 ✅
- [x] pytest 설정 (`pytest.ini`)
- [x] 테스트 데이터 준비 (`tests/conftest.py`)
- [x] 모킹 유틸리티

### 3.2 Phase 2: 자막 품질 검증 ✅
- [x] `TranscriptValidator` 클래스 (`transcript_validator.py`)
- [x] 최소 길이 검증 (300자)
- [x] 상품 언급 키워드 확인
- [x] 가격 언급 감지
- [x] 부정 리뷰 감지
- [x] 매장 관련성 검증
- [x] 품질 점수 계산
- [x] 테스트 작성 (16개 테스트)

### 3.3 Phase 3: AI 추출 개선 ✅
- [x] `ImprovedProductExtractor` 클래스 (`improved_product_extractor.py`)
- [x] 개선된 프롬프트 (맥락 이해, 추천 스크립트 인용)
- [x] 신뢰도 점수 추가 (`confidence` 필드)
- [x] 부정 리뷰 필터링 (`is_recommended: false` 제외)
- [x] 중복 제거 (`_remove_duplicates`)
- [x] 테스트 작성 (18개 테스트)

### 3.4 Phase 4: 매칭 로직 개선 ✅
- [x] `ImprovedProductMatcher` 클래스 (`improved_product_matcher.py`)
- [x] 임계값 상향 (20→40)
- [x] 다단계 검증 (이름 + 가격 + 카테고리 + 인기도)
- [x] 한국어 변형 처리 (스텐/스테인레스)
- [x] 확장된 불용어 목록
- [x] 수동 검토 플래그 (`needs_manual_review`)
- [x] 테스트 작성 (16개 테스트)

### 3.5 Phase 5: DB 스키마 개선 ✅
- [x] `ImprovedDatabase` 클래스 (`improved_database.py`)
- [x] UNIQUE 제약조건 추가 (`video_id, name, price`)
- [x] 품질 메트릭 로깅 테이블 (`quality_logs`)
- [x] 중복 삽입 방지 (`INSERT OR IGNORE`)
- [x] 수동 검토 필요 상품 조회

### 3.6 Phase 6: 통합 파이프라인 ✅
- [x] `ImprovedDataPipeline` 클래스 (`improved_pipeline.py`)
- [x] 모든 개선 컴포넌트 통합
- [x] 품질 메트릭 자동 로깅
- [x] 에러 핸들링 개선

---

## 4. 변경 이력

### 2025-12-28 (시작)
- [x] 현재 시스템 분석 완료
- [x] 9가지 핵심 문제점 식별

### 2025-12-28 (TDD 구현)
- [x] pytest 테스트 프레임워크 구축
- [x] TranscriptValidator 구현 및 테스트
- [x] ImprovedProductExtractor 구현 및 테스트
- [x] ImprovedProductMatcher 구현 및 테스트
- [x] ImprovedDatabase 구현
- [x] ImprovedDataPipeline 구현
- [x] **50개 테스트 모두 통과**

---

## 5. 새로 생성된 파일

| 파일명 | 설명 |
|--------|------|
| `crawler/pytest.ini` | pytest 설정 |
| `crawler/tests/conftest.py` | 테스트 픽스처 |
| `crawler/tests/test_transcript_validator.py` | 자막 검증 테스트 |
| `crawler/tests/test_product_extractor.py` | AI 추출 테스트 |
| `crawler/tests/test_product_matcher.py` | 매칭 테스트 |
| `crawler/transcript_validator.py` | 자막 품질 검증기 |
| `crawler/improved_product_extractor.py` | 개선된 AI 추출기 |
| `crawler/improved_product_matcher.py` | 개선된 상품 매칭기 |
| `crawler/improved_database.py` | 개선된 DB (UNIQUE 제약) |
| `crawler/improved_pipeline.py` | 개선된 파이프라인 |

---

## 6. 테스트 결과

```
======================== 50 passed, 1 warning in 1.15s ========================

테스트 분류:
- TranscriptValidator: 16개 테스트 PASS
- ProductExtractor: 18개 테스트 PASS
- ProductMatcher: 16개 테스트 PASS
```

---

## 7. 개선 효과 요약

| 항목 | 기존 | 개선 후 |
|------|------|---------|
| 자막 최소 길이 | 50자 | 300자 |
| 상품 언급 검증 | 없음 | 키워드 기반 |
| 부정 리뷰 필터 | 없음 | AI 레벨 필터링 |
| 매칭 임계값 | 20점 | 40점 |
| 중복 방지 | 없음 | UNIQUE 제약조건 |
| 신뢰도 점수 | 없음 | 0.0~1.0 |
| 수동 검토 플래그 | 없음 | 신뢰도 <0.7 |
| 품질 메트릭 로깅 | 없음 | quality_logs 테이블 |

---

## 8. 실제 테스트 결과 ✅

### 8.1 2025-12-28 테스트 실행 결과

```
=== 개선된 파이프라인 테스트 결과 (5개 영상) ===

자막 추출:
- 유효한 자막: 5개 (100% 성공)
- 품질 미달: 0개

상품 추출:
- 추출된 상품: 25개 (평균 5개/영상)
- 신뢰도 점수: 0.90 평균

매칭:
- 매칭 성공: 3/25개 (12%)
- 수동 검토 필요: 25개

소요 시간: 57초
```

### 8.2 이전 대비 개선점

| 항목 | 이전 | 현재 |
|------|------|------|
| 자막 추출 성공률 | 0% | **100%** |
| 품질 검증 | 없음 | **300자 최소 + 상품 언급 검증** |
| AI 신뢰도 | 없음 | **0.90 평균** |
| 수동 검토 플래그 | 없음 | **자동 설정** |

### 8.3 수정 사항 (테스트 중 발견)

1. **youtube-transcript-api v1.2.3 호환성**
   - API가 `get_transcript()` → `api.fetch()` 인스턴스 메서드로 변경됨
   - `youtube_crawler.py` 업데이트 완료

2. **DB 마이그레이션 로직 추가**
   - 기존 DB에 새 컬럼이 없어서 오류 발생
   - `_migrate_existing_tables()` 메서드 추가로 자동 마이그레이션

---

## 9. 다음 단계

### 9.1 품질 개선 (진행 중)
- [x] AI 프롬프트 대폭 개선 (2025-12-28)
- [x] 비추천 상품 필터링 검증 완료
- [x] 다른 매장 상품 제외 검증 완료
- [ ] 실제 영상 테스트 크롤링 (YouTube 쿼터 리셋 후)
- [ ] 다이소 카탈로그 매칭으로 가격 보완

### 9.2 기존 시스템 마이그레이션
- [x] 기존 DB 데이터 초기화 (2025-12-28)
- [ ] 기존 `pipeline.py`를 `improved_pipeline.py`로 교체
- [ ] 새 데이터로 본 크롤링 실행

### 9.3 품질 메트릭 목표
- 자막 추출 성공률: **100% 달성 ✅**
- 상품 추출 정확도: **90% 목표** (AI 프롬프트 개선으로)
- 매칭 정확도: 12% → 70% 목표 (카탈로그 확장 필요)
- 중복 발생률: 0% (UNIQUE 제약조건으로 보장)

---

## 11. AI 프롬프트 개선 (2025-12-28)

### 11.1 추가된 기능

| 기능 | 설명 |
|------|------|
| 매장별 가격 범위 | 다이소: 1,000~10,000원, 이케아: ~500,000원 |
| 매장별 특수 규칙 | 다이소: 올리브영 제외, 이케아: 스웨덴어 상품명 |
| 맥락 이해 강화 | 잘못된 추출 예시 추가 |
| 긍정/부정 키워드 | 명시적 필터링 규칙 |

### 11.2 프롬프트 테스트 결과

```
테스트 자막: 10개 상품 언급 (추천 9개, 비추천 1개, 다른매장 1개)
추출 결과: 9개 (정확히 추천 상품만)

검증:
- 비추천 상품(선풍기) 제외: ✅
- 다른 매장 상품(올리브영 립틴트) 제외: ✅
- 모든 가격 정확히 추출: ✅
- 신뢰도 점수: 0.75~0.95
```

### 11.3 수집 지침서

`COLLECTION_GUIDELINES.md` 작성 완료:
- 영상 선별 기준 (추천 영상 vs 비추천 영상)
- 상품 추출 기준 (긍정적 추천만)
- 매장별 특수 규칙
- 품질 검증 체크리스트

---

## 10. 사용 방법

```bash
# 테스트 실행
cd crawler
python -m pytest tests/ -v

# 개선된 파이프라인 실행
python improved_pipeline.py --test  # 테스트 모드 (3개 영상)
python improved_pipeline.py         # 기본 실행 (10개 영상)
```
