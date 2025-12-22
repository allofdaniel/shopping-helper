# -*- coding: utf-8 -*-
"""
NAS 배포 스크립트
꿀템장바구니 크롤러를 Synology NAS에 Docker 컨테이너로 배포합니다.
"""
import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

# NAS 설정
NAS_HOST = "192.168.50.179"
NAS_USER = "allofdaniel"
NAS_PASSWORD = "Pr12pr34!@"
NAS_DOCKER_PATH = "/volume1/docker/shopping-helper"
CONTAINER_NAME = "shopping-helper-crawler"

# 로컬 프로젝트 경로
PROJECT_DIR = Path(__file__).parent
CRAWLER_DIR = PROJECT_DIR / "crawler"
DOCKER_DIR = PROJECT_DIR / "docker"


def run_ssh(command: str, check: bool = True) -> str:
    """SSH 명령어 실행"""
    ssh_cmd = f'ssh {NAS_USER}@{NAS_HOST} "{command}"'
    print(f"[SSH] {command}")

    result = subprocess.run(
        ssh_cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    if check and result.returncode != 0:
        print(f"[!] SSH 오류: {result.stderr}")

    return result.stdout.strip()


def run_scp(local_path: str, remote_path: str) -> bool:
    """SCP 파일 전송"""
    scp_cmd = f'scp -r "{local_path}" {NAS_USER}@{NAS_HOST}:"{remote_path}"'
    print(f"[SCP] {local_path} -> {remote_path}")

    result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[!] SCP 오류: {result.stderr}")
        return False

    return True


def create_env_file():
    """환경변수 파일 생성"""
    # 로컬 .env에서 키 읽기
    env_path = CRAWLER_DIR / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    # AWS credentials 추가 (로컬 ~/.aws/credentials에서)
    aws_creds = Path.home() / ".aws" / "credentials"
    if aws_creds.exists():
        import configparser
        config = configparser.ConfigParser()
        config.read(aws_creds)
        if 'default' in config:
            env_vars['AWS_ACCESS_KEY_ID'] = config['default'].get('aws_access_key_id', '')
            env_vars['AWS_SECRET_ACCESS_KEY'] = config['default'].get('aws_secret_access_key', '')

    # NAS용 .env 파일 생성
    nas_env_path = DOCKER_DIR / ".env"
    with open(nas_env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"[OK] 환경변수 파일 생성됨: {nas_env_path}")
    return nas_env_path


def deploy():
    """NAS에 배포"""
    print("\n" + "="*50)
    print("꿀템장바구니 크롤러 NAS 배포")
    print("="*50 + "\n")

    # 1. 환경변수 파일 생성
    print("[Step 1] 환경변수 파일 생성...")
    create_env_file()

    # 2. NAS에 디렉토리 생성
    print("\n[Step 2] NAS 디렉토리 준비...")
    run_ssh(f"mkdir -p {NAS_DOCKER_PATH}/crawler")
    run_ssh(f"mkdir -p {NAS_DOCKER_PATH}/data")
    run_ssh(f"mkdir -p {NAS_DOCKER_PATH}/logs")

    # 3. 기존 컨테이너 중지
    print("\n[Step 3] 기존 컨테이너 중지...")
    run_ssh(f"/usr/local/bin/docker stop {CONTAINER_NAME} 2>/dev/null || true", check=False)
    run_ssh(f"/usr/local/bin/docker rm {CONTAINER_NAME} 2>/dev/null || true", check=False)

    # 4. 파일 전송
    print("\n[Step 4] 파일 전송...")

    # crawler 폴더
    run_scp(str(CRAWLER_DIR), f"{NAS_DOCKER_PATH}/")

    # docker 설정 파일
    run_scp(str(DOCKER_DIR / "Dockerfile"), f"{NAS_DOCKER_PATH}/")
    run_scp(str(DOCKER_DIR / "docker-compose.yml"), f"{NAS_DOCKER_PATH}/")
    run_scp(str(DOCKER_DIR / ".env"), f"{NAS_DOCKER_PATH}/")

    # requirements.txt
    req_file = PROJECT_DIR / "requirements.txt"
    if not req_file.exists():
        # requirements.txt 생성
        with open(req_file, 'w') as f:
            f.write("""google-generativeai>=0.3.0
google-api-python-client>=2.0.0
youtube-transcript-api==0.6.1
python-dotenv>=1.0.0
requests>=2.31.0
tqdm>=4.65.0
boto3>=1.28.0
""")
    run_scp(str(req_file), f"{NAS_DOCKER_PATH}/")

    # 5. Docker 이미지 빌드 및 실행
    print("\n[Step 5] Docker 컨테이너 빌드 및 시작...")

    # docker-compose 대신 직접 docker run 사용 (Synology 호환성)
    docker_cmd = f"""
cd {NAS_DOCKER_PATH} && \\
/usr/local/bin/docker build -t shopping-helper . && \\
/usr/local/bin/docker run -d \\
    --name {CONTAINER_NAME} \\
    --restart unless-stopped \\
    -e TZ=Asia/Seoul \\
    --env-file .env \\
    -v {NAS_DOCKER_PATH}/data:/app/data \\
    -v {NAS_DOCKER_PATH}/logs:/app/data/logs \\
    shopping-helper
"""

    result = run_ssh(docker_cmd, check=False)
    print(result)

    # 6. 상태 확인
    print("\n[Step 6] 컨테이너 상태 확인...")
    time.sleep(3)
    status = run_ssh(f"/usr/local/bin/docker ps --filter name={CONTAINER_NAME} --format '{{{{.Status}}}}'")

    if status and "Up" in status:
        print(f"\n[OK] 배포 성공!")
        print(f"    컨테이너: {CONTAINER_NAME}")
        print(f"    상태: {status}")
        print(f"\n로그 확인:")
        print(f"    ssh {NAS_USER}@{NAS_HOST} '/usr/local/bin/docker logs -f {CONTAINER_NAME}'")
    else:
        print(f"\n[!] 배포 실패 또는 시작 중...")
        logs = run_ssh(f"/usr/local/bin/docker logs {CONTAINER_NAME} 2>&1 | tail -20", check=False)
        print(f"최근 로그:\n{logs}")

    return status


def check_status():
    """컨테이너 상태 확인"""
    print("\n=== 컨테이너 상태 ===\n")

    status = run_ssh(f"/usr/local/bin/docker ps -a --filter name={CONTAINER_NAME}")
    print(status)

    print("\n=== 최근 로그 ===\n")
    logs = run_ssh(f"/usr/local/bin/docker logs {CONTAINER_NAME} 2>&1 | tail -30", check=False)
    print(logs)


def stop():
    """컨테이너 중지"""
    run_ssh(f"/usr/local/bin/docker stop {CONTAINER_NAME}")
    print(f"[OK] {CONTAINER_NAME} 중지됨")


def restart():
    """컨테이너 재시작"""
    run_ssh(f"/usr/local/bin/docker restart {CONTAINER_NAME}")
    print(f"[OK] {CONTAINER_NAME} 재시작됨")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='NAS 배포 스크립트')
    parser.add_argument('action', choices=['deploy', 'status', 'stop', 'restart', 'logs'],
                        help='실행할 작업')

    args = parser.parse_args()

    if args.action == 'deploy':
        deploy()
    elif args.action == 'status':
        check_status()
    elif args.action == 'stop':
        stop()
    elif args.action == 'restart':
        restart()
    elif args.action == 'logs':
        os.system(f'ssh {NAS_USER}@{NAS_HOST} "/usr/local/bin/docker logs -f {CONTAINER_NAME}"')
