#!/bin/bash
# 꿀템장바구니 - 서버 설정 스크립트
# Ubuntu/Debian 서버에서 실행
#
# 사용법:
#   curl -sSL https://raw.githubusercontent.com/allofdaniel/shopping-helper/master/scripts/setup-server.sh | bash
#   또는
#   ./setup-server.sh

set -e

echo "=== 꿀템장바구니 서버 설정 ==="

# 변수
INSTALL_DIR="/root/shopping-helper"
REPO_URL="https://github.com/allofdaniel/shopping-helper.git"

# 1. 시스템 패키지 설치
echo "[1/6] 시스템 패키지 설치..."
apt-get update
apt-get install -y python3 python3-pip python3-venv git ffmpeg

# 2. 프로젝트 클론/업데이트
echo "[2/6] 프로젝트 다운로드..."
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR"
    git pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. 가상환경 설정
echo "[3/6] Python 가상환경 설정..."
python3 -m venv venv
source venv/bin/activate

# 4. 의존성 설치
echo "[4/6] Python 패키지 설치..."
pip install --upgrade pip
pip install -r crawler/requirements.txt

# 5. 환경변수 설정
echo "[5/6] 환경변수 설정..."
if [ ! -f "crawler/.env" ]; then
    cat > crawler/.env << 'EOF'
# AI API (하나 이상 필요)
GEMINI_API_KEY=your_gemini_api_key
# OPENAI_API_KEY=your_openai_api_key

# 알림 (선택)
# DISCORD_WEBHOOK_URL=your_discord_webhook
# SLACK_WEBHOOK_URL=your_slack_webhook

# AWS S3 (선택)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_DEFAULT_REGION=ap-northeast-2
# S3_BUCKET=your-bucket-name
EOF
    echo "  -> crawler/.env 파일 생성됨"
    echo "  -> API 키를 설정해주세요: nano $INSTALL_DIR/crawler/.env"
fi

# 6. systemd 서비스 설치
echo "[6/6] systemd 서비스 설정..."
cp scripts/shopping-crawler.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable shopping-crawler

echo ""
echo "=== 설정 완료 ==="
echo ""
echo "다음 단계:"
echo "1. API 키 설정:"
echo "   nano $INSTALL_DIR/crawler/.env"
echo ""
echo "2. 서비스 시작:"
echo "   systemctl start shopping-crawler"
echo ""
echo "3. 로그 확인:"
echo "   journalctl -u shopping-crawler -f"
echo ""
echo "4. 수동 실행 테스트:"
echo "   cd $INSTALL_DIR/crawler"
echo "   source ../venv/bin/activate"
echo "   python unlimited_pipeline.py --store daiso --max-videos 5"
