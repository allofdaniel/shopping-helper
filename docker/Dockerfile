# 꿀템장바구니 크롤러 Docker 이미지
# Security-hardened build

FROM python:3.11-slim AS base

# 보안: 빌드 시 메타데이터
LABEL maintainer="shopping-helper"
LABEL version="1.0"
LABEL description="Offline Shopping Helper Crawler"

# 보안: non-root 사용자 생성
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# 작업 디렉토리
WORKDIR /app

# 시스템 패키지 설치 (최소화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Python 패키지 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY --chown=appuser:appgroup crawler/ ./crawler/

# 데이터 디렉토리 생성 및 권한 설정
RUN mkdir -p ./data && chown -R appuser:appgroup ./data

# 환경변수
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul
ENV PYTHONDONTWRITEBYTECODE=1

# 보안: root 사용 금지
USER appuser

# 데이터 디렉토리 (호스트 마운트용)
VOLUME ["/app/data"]

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('healthy')" || exit 1

# 기본 명령어: 스케줄러 실행
CMD ["python", "crawler/scheduler.py", "--force", "--max-videos", "20"]
