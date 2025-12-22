# 꿀템장바구니 크롤러 Docker 이미지
FROM python:3.11-slim

# 작업 디렉토리
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY crawler/ ./crawler/

# 데이터 디렉토리 생성
RUN mkdir -p ./data

# 환경변수
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# 데이터 디렉토리
VOLUME ["/app/data"]

# 기본 명령어: 스케줄러 실행
CMD ["python", "crawler/scheduler.py", "--force", "--max-videos", "20"]
