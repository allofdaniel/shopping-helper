# NAS 배포 가이드

## 수동 배포 방법

### 1. 파일 복사 (WinSCP 또는 파일탐색기)

NAS 공유폴더에 접속:
- 경로: `\\192.168.50.179\docker\shopping-helper`
- 사용자: `allofdaniel`
- 비밀번호: `Pr12pr34!@`

복사할 폴더/파일:
```
offline-shopping-helper/
├── crawler/          -> /volume1/docker/shopping-helper/crawler/
├── docker/Dockerfile -> /volume1/docker/shopping-helper/Dockerfile
├── requirements.txt  -> /volume1/docker/shopping-helper/requirements.txt
└── docker/.env      -> /volume1/docker/shopping-helper/.env
```

### 2. .env 파일 생성

NAS에 `/volume1/docker/shopping-helper/.env` 파일 생성:

```env
YOUTUBE_API_KEY=AIzaSyCQkFFF_5ZwupOThxiHeePYLhrIlJE7iB0
GEMINI_API_KEY=AIzaSyCQkFFF_5ZwupOThxiHeePYLhrIlJE7iB0
AWS_ACCESS_KEY_ID=(~/.aws/credentials에서 복사)
AWS_SECRET_ACCESS_KEY=(~/.aws/credentials에서 복사)
AWS_DEFAULT_REGION=ap-northeast-2
S3_BUCKET=notam-korea-data
```

### 3. SSH 접속 후 Docker 빌드

```bash
# SSH 접속
ssh allofdaniel@192.168.50.179

# 디렉토리 이동
cd /volume1/docker/shopping-helper

# Docker 이미지 빌드
/usr/local/bin/docker build -t shopping-helper .

# 컨테이너 실행
/usr/local/bin/docker run -d \
  --name shopping-helper-crawler \
  --restart unless-stopped \
  -e TZ=Asia/Seoul \
  --env-file .env \
  -v /volume1/docker/shopping-helper/data:/app/data \
  -v /volume1/docker/shopping-helper/logs:/app/data/logs \
  shopping-helper
```

### 4. 주기적 실행 설정 (DSM 작업 스케줄러)

DSM > 제어판 > 작업 스케줄러에서:

1. **생성** > **예약된 작업** > **사용자 정의 스크립트**
2. 일반 탭:
   - 작업: `shopping-helper-crawl`
   - 사용자: `root`
3. 일정 탭:
   - 매일 실행
   - 시작 시간: 00:00
   - 매 6시간마다 반복
4. 작업 설정 탭:
   ```bash
   /usr/local/bin/docker exec shopping-helper-crawler python crawler/scheduler.py --force
   /usr/local/bin/docker exec shopping-helper-crawler python crawler/s3_uploader.py
   ```

## 관리 명령어

```bash
# 상태 확인
ssh allofdaniel@192.168.50.179 '/usr/local/bin/docker ps'

# 로그 확인
ssh allofdaniel@192.168.50.179 '/usr/local/bin/docker logs -f shopping-helper-crawler'

# 컨테이너 재시작
ssh allofdaniel@192.168.50.179 '/usr/local/bin/docker restart shopping-helper-crawler'

# 수동 실행
ssh allofdaniel@192.168.50.179 '/usr/local/bin/docker exec shopping-helper-crawler python crawler/scheduler.py --force'

# S3 업로드
ssh allofdaniel@192.168.50.179 '/usr/local/bin/docker exec shopping-helper-crawler python crawler/s3_uploader.py'
```

## S3 데이터 확인

```bash
# 로컬에서 S3 확인
aws s3 ls s3://notam-korea-data/shopping-helper/

# DB 다운로드
aws s3 cp s3://notam-korea-data/shopping-helper/db/products_latest.db ./products.db
```

## 트러블슈팅

### Docker 빌드 실패
```bash
# 캐시 없이 빌드
/usr/local/bin/docker build --no-cache -t shopping-helper .
```

### 컨테이너 시작 실패
```bash
# 로그 확인
/usr/local/bin/docker logs shopping-helper-crawler

# 환경변수 확인
/usr/local/bin/docker exec shopping-helper-crawler env
```
