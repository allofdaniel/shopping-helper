FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p /app/data/logs

# 환경 변수
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# 기본 명령어
CMD ["python", "continuous_collector.py", "--mode", "schedule"]
