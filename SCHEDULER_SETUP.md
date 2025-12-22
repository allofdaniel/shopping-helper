# 자동 수집 스케줄러 설정 가이드

## 개요
꿀템장바구니 자동 수집 스케줄러는 YouTube 영상을 자동으로 수집하고 상품을 추출합니다.

## 실행 방법

### 1. 수동 실행
```bash
cd crawler
python scheduler.py --force
```

### 2. 특정 매장만 실행
```bash
python scheduler.py --store daiso --force
python scheduler.py --store costco --force
```

### 3. 데몬 모드 (계속 실행)
```bash
python scheduler.py --daemon
```

## Windows 작업 스케줄러 설정

### 방법 1: GUI로 설정

1. **작업 스케줄러 열기**
   - Win + R → `taskschd.msc` 입력

2. **새 작업 만들기**
   - 오른쪽 "작업 만들기" 클릭
   - 이름: `꿀템장바구니 자동수집`
   - "가장 높은 수준의 권한으로 실행" 체크

3. **트리거 설정**
   - 새로 만들기 → "매일" 선택
   - 시작 시간: 오전 9:00
   - 매 1시간마다 반복 (원하는 주기)

4. **동작 설정**
   - 새로 만들기
   - 프로그램: `C:\...\offline-shopping-helper\run_scheduler.bat`

### 방법 2: PowerShell로 설정

```powershell
# 작업 생성
$action = New-ScheduledTaskAction -Execute "C:\...\offline-shopping-helper\run_scheduler.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "꿀템장바구니_자동수집" -Action $action -Trigger $trigger -Settings $settings
```

## 스케줄러 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--store` | 특정 매장만 수집 | `--store daiso` |
| `--daemon` | 계속 실행 모드 | `--daemon` |
| `--force` | 시간 체크 무시 | `--force` |
| `--max-videos` | 매장당 최대 영상 수 | `--max-videos 30` |

## 로그 확인

수집 로그는 `data/logs/` 폴더에 저장됩니다:
- `scheduler_YYYYMMDD.log`: 일별 실행 로그
- `scheduler_batch.log`: 배치 파일 실행 기록

## 상태 확인

```bash
# 마지막 실행 상태 확인
type data\scheduler_status.json
```

## 권장 설정

| 환경 | 주기 | 매장당 영상 수 |
|------|------|---------------|
| 개발/테스트 | 수동 | 10개 |
| 일반 사용 | 매 6시간 | 20개 |
| 적극 수집 | 매 1시간 | 30개 |

## 주의사항

1. **API 제한**: YouTube API 일일 할당량 주의
2. **Gemini API**: 무료 티어는 분당 60회 제한
3. **네트워크**: 안정적인 인터넷 연결 필요
