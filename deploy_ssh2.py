# -*- coding: utf-8 -*-
"""
NAS 배포 스크립트 (paramiko 버전)
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

import paramiko
from scp import SCPClient

# NAS 설정
NAS_HOST = "192.168.50.179"
NAS_PORT = 22
NAS_USER = "allofdaniel"
NAS_PASSWORD = "Pr12pr34!@"
NAS_DOCKER_PATH = "/volume1/docker/shopping-helper"
CONTAINER_NAME = "shopping-helper-crawler"

# 로컬 프로젝트 경로
PROJECT_DIR = Path(__file__).parent
CRAWLER_DIR = PROJECT_DIR / "crawler"
DOCKER_DIR = PROJECT_DIR / "docker"


def create_ssh_client():
    """SSH 클라이언트 생성"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=NAS_HOST,
        port=NAS_PORT,
        username=NAS_USER,
        password=NAS_PASSWORD,
        timeout=30
    )
    return client


def run_ssh_command(client, command, print_output=True):
    """SSH 명령어 실행"""
    print(f"[SSH] {command}")
    stdin, stdout, stderr = client.exec_command(command, timeout=300)

    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if print_output and output:
        print(output)
    if error:
        print(f"[STDERR] {error}")

    return output, error


def create_env_file():
    """환경변수 파일 생성"""
    env_path = CRAWLER_DIR / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    # AWS credentials 추가
    aws_creds = Path.home() / ".aws" / "credentials"
    if aws_creds.exists():
        import configparser
        config = configparser.ConfigParser()
        config.read(aws_creds)
        if 'default' in config:
            env_vars['AWS_ACCESS_KEY_ID'] = config['default'].get('aws_access_key_id', '')
            env_vars['AWS_SECRET_ACCESS_KEY'] = config['default'].get('aws_secret_access_key', '')

    env_vars['AWS_DEFAULT_REGION'] = 'ap-northeast-2'
    env_vars['S3_BUCKET'] = 'notam-korea-data'

    # NAS용 .env 파일 생성
    nas_env_path = DOCKER_DIR / ".env"
    DOCKER_DIR.mkdir(parents=True, exist_ok=True)

    with open(nas_env_path, 'w', encoding='utf-8') as f:
        for key, value in env_vars.items():
            if value:  # 빈 값 제외
                f.write(f"{key}={value}\n")

    print(f"[OK] 환경변수 파일 생성됨")
    return nas_env_path


def deploy():
    """NAS에 배포"""
    print("\n" + "="*50)
    print("꿀템장바구니 크롤러 NAS 배포")
    print("="*50 + "\n")

    # 1. 환경변수 파일 생성
    print("[Step 1] 환경변수 파일 생성...")
    create_env_file()

    # 2. SSH 연결
    print("\n[Step 2] NAS 연결 중...")
    try:
        client = create_ssh_client()
        print("[OK] SSH 연결 성공")
    except Exception as e:
        print(f"[!] SSH 연결 실패: {e}")
        return False

    try:
        # 3. 디렉토리 생성
        print("\n[Step 3] NAS 디렉토리 준비...")
        run_ssh_command(client, f"mkdir -p {NAS_DOCKER_PATH}/crawler")
        run_ssh_command(client, f"mkdir -p {NAS_DOCKER_PATH}/data")
        run_ssh_command(client, f"mkdir -p {NAS_DOCKER_PATH}/logs")

        # 4. 기존 컨테이너 중지
        print("\n[Step 4] 기존 컨테이너 중지...")
        run_ssh_command(client, f"/usr/local/bin/docker stop {CONTAINER_NAME} 2>/dev/null || true")
        run_ssh_command(client, f"/usr/local/bin/docker rm {CONTAINER_NAME} 2>/dev/null || true")

        # 5. 파일 전송
        print("\n[Step 5] 파일 전송...")
        scp = SCPClient(client.get_transport())

        # crawler 폴더 내 파일들
        crawler_files = list(CRAWLER_DIR.glob("*.py"))
        for f in crawler_files:
            print(f"  -> {f.name}")
            scp.put(str(f), f"{NAS_DOCKER_PATH}/crawler/{f.name}")

        # Dockerfile
        dockerfile = DOCKER_DIR / "Dockerfile"
        if dockerfile.exists():
            print(f"  -> Dockerfile")
            scp.put(str(dockerfile), f"{NAS_DOCKER_PATH}/Dockerfile")

        # .env
        envfile = DOCKER_DIR / ".env"
        if envfile.exists():
            print(f"  -> .env")
            scp.put(str(envfile), f"{NAS_DOCKER_PATH}/.env")

        # requirements.txt
        reqfile = PROJECT_DIR / "requirements.txt"
        if reqfile.exists():
            print(f"  -> requirements.txt")
            scp.put(str(reqfile), f"{NAS_DOCKER_PATH}/requirements.txt")

        scp.close()
        print("[OK] 파일 전송 완료")

        # 6. Docker 빌드
        print("\n[Step 6] Docker 이미지 빌드...")
        output, error = run_ssh_command(
            client,
            f"cd {NAS_DOCKER_PATH} && /usr/local/bin/docker build -t shopping-helper .",
            print_output=True
        )

        # 7. 컨테이너 실행
        print("\n[Step 7] 컨테이너 실행...")
        docker_run_cmd = f"""
/usr/local/bin/docker run -d \\
  --name {CONTAINER_NAME} \\
  --restart unless-stopped \\
  -e TZ=Asia/Seoul \\
  --env-file {NAS_DOCKER_PATH}/.env \\
  -v {NAS_DOCKER_PATH}/data:/app/data \\
  -v {NAS_DOCKER_PATH}/logs:/app/data/logs \\
  shopping-helper
"""
        run_ssh_command(client, docker_run_cmd)

        # 8. 상태 확인
        print("\n[Step 8] 상태 확인...")
        time.sleep(3)
        output, _ = run_ssh_command(
            client,
            f"/usr/local/bin/docker ps --filter name={CONTAINER_NAME} --format '{{{{.Status}}}}'",
            print_output=False
        )

        if "Up" in output:
            print(f"\n{'='*50}")
            print("[OK] 배포 성공!")
            print(f"{'='*50}")
            print(f"컨테이너: {CONTAINER_NAME}")
            print(f"상태: {output.strip()}")
            print(f"\n로그 확인 명령어:")
            print(f"  python deploy_ssh2.py logs")
            return True
        else:
            print(f"\n[!] 컨테이너가 시작되지 않았습니다")
            run_ssh_command(client, f"/usr/local/bin/docker logs {CONTAINER_NAME} 2>&1 | tail -30")
            return False

    finally:
        client.close()


def check_logs():
    """로그 확인"""
    client = create_ssh_client()
    try:
        run_ssh_command(client, f"/usr/local/bin/docker logs {CONTAINER_NAME} 2>&1 | tail -50")
    finally:
        client.close()


def check_status():
    """상태 확인"""
    client = create_ssh_client()
    try:
        print("\n=== 컨테이너 상태 ===")
        run_ssh_command(client, f"/usr/local/bin/docker ps -a --filter name={CONTAINER_NAME}")
    finally:
        client.close()


def restart():
    """재시작"""
    client = create_ssh_client()
    try:
        run_ssh_command(client, f"/usr/local/bin/docker restart {CONTAINER_NAME}")
        print(f"[OK] {CONTAINER_NAME} 재시작됨")
    finally:
        client.close()


def run_crawler():
    """크롤러 수동 실행"""
    client = create_ssh_client()
    try:
        print("크롤러 실행 중...")
        run_ssh_command(
            client,
            f"/usr/local/bin/docker exec {CONTAINER_NAME} python crawler/scheduler.py --force --max-videos 10"
        )
        print("\nS3 업로드 중...")
        run_ssh_command(
            client,
            f"/usr/local/bin/docker exec {CONTAINER_NAME} python crawler/s3_uploader.py"
        )
    finally:
        client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='NAS 배포 스크립트')
    parser.add_argument('action', choices=['deploy', 'status', 'logs', 'restart', 'run'],
                        nargs='?', default='deploy',
                        help='실행할 작업')

    args = parser.parse_args()

    try:
        if args.action == 'deploy':
            deploy()
        elif args.action == 'status':
            check_status()
        elif args.action == 'logs':
            check_logs()
        elif args.action == 'restart':
            restart()
        elif args.action == 'run':
            run_crawler()
    except Exception as e:
        print(f"[!] 오류: {e}")
        import traceback
        traceback.print_exc()
