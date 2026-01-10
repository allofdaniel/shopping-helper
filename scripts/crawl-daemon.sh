#!/bin/bash
# 꿀템장바구니 - 자동 수집 데몬
# 서버에서 주기적으로 YouTube 영상 수집
#
# 사용법:
#   ./crawl-daemon.sh              # 기본 실행 (1시간 간격, 모든 매장)
#   ./crawl-daemon.sh --store daiso # 특정 매장만
#   ./crawl-daemon.sh --once        # 한 번만 실행

set -e

# 환경 설정
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CRAWLER_DIR="$PROJECT_DIR/crawler"
LOG_DIR="$PROJECT_DIR/logs"
VENV_DIR="$PROJECT_DIR/venv"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 가상환경 활성화
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

# 기본값
INTERVAL=3600  # 1시간
STORE=""
ONCE=false
MAX_VIDEOS=30
MAX_PER_CHANNEL=15

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --store)
            STORE="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --once)
            ONCE=true
            shift
            ;;
        --max-videos)
            MAX_VIDEOS="$2"
            shift 2
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            exit 1
            ;;
    esac
done

# 로그 파일
TIMESTAMP=$(date +%Y%m%d)
LOG_FILE="$LOG_DIR/crawl-$TIMESTAMP.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

run_crawl() {
    log "=== 크롤링 시작 ==="

    cd "$CRAWLER_DIR"

    if [ -n "$STORE" ]; then
        log "매장: $STORE"
        python unlimited_pipeline.py --store "$STORE" --max-videos "$MAX_VIDEOS" --max-per-channel "$MAX_PER_CHANNEL" 2>&1 | tee -a "$LOG_FILE"
    else
        log "모든 매장 수집"
        python unlimited_pipeline.py --all --max-videos "$MAX_VIDEOS" --max-per-channel "$MAX_PER_CHANNEL" 2>&1 | tee -a "$LOG_FILE"
    fi

    log "=== 크롤링 완료 ==="
}

# 메인 실행
log "꿀템장바구니 크롤러 데몬 시작"
log "실행 간격: ${INTERVAL}초"

if [ "$ONCE" = true ]; then
    run_crawl
else
    while true; do
        run_crawl
        log "다음 실행까지 ${INTERVAL}초 대기..."
        sleep "$INTERVAL"
    done
fi
