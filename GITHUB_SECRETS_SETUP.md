# GitHub Actions Secrets 설정 가이드

## NAS 자동 배포를 위한 Secrets 설정

GitHub 저장소 Settings > Secrets and variables > Actions에서 다음 Secrets를 추가하세요:

### 1. NAS 관련
```
NAS_HOST: 192.168.50.179
NAS_USER: allofdaniel
NAS_SSH_PRIVATE_KEY: (SSH 키 생성 필요)
```

### 2. API Keys
```
YOUTUBE_API_KEY: AIzaSy... (YouTube Data API 키)
GEMINI_API_KEY: AIzaSy... (Google Gemini API 키)
```

### 3. AWS Credentials
```
AWS_ACCESS_KEY_ID: AKIA...
AWS_SECRET_ACCESS_KEY: (AWS 시크릿 키)
```

## SSH 키 생성 방법

1. 로컬에서 SSH 키 생성:
```bash
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/nas_deploy_key
```

2. 공개키를 NAS에 등록:
```bash
ssh-copy-id -i ~/.ssh/nas_deploy_key.pub allofdaniel@192.168.50.179
```

3. 개인키를 GitHub Secret에 등록:
   - `NAS_SSH_PRIVATE_KEY` 값으로 `~/.ssh/nas_deploy_key` 내용 전체 복사

## 수동 배포 (로컬)

SSH 키 대신 비밀번호 인증 사용 시:
```bash
python deploy_ssh2.py deploy
```

## 워크플로우 트리거

- `main` 브랜치에 push 시 자동 실행
- GitHub Actions 탭에서 수동 실행 가능 (workflow_dispatch)

## S3 버킷 CORS 설정

S3 버킷에서 프론트엔드가 데이터를 읽으려면 CORS 설정 필요:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET"],
        "AllowedOrigins": [
            "http://localhost:3000",
            "https://*.vercel.app",
            "https://your-domain.com"
        ],
        "ExposeHeaders": []
    }
]
```

S3 콘솔 > 버킷 > Permissions > CORS configuration에 설정
