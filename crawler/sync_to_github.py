# -*- coding: utf-8 -*-
"""
GitHub 자동 동기화 스크립트
수집된 데이터를 JSON으로 변환하고 GitHub에 푸시합니다.
"""
import os
import sys
import json
import sqlite3
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'data' / 'products.db'
EXPORT_DIR = BASE_DIR / 'export'
REPO_DIR = BASE_DIR / 'repo'

# GitHub 설정 (환경변수로 전달)
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'allofdaniel/shopping-helper')
GITHUB_BRANCH = os.environ.get('GITHUB_BRANCH', 'master')


def export_to_json():
    """SQLite 데이터를 JSON으로 변환"""
    if not DB_PATH.exists():
        logger.warning(f"DB not found: {DB_PATH}")
        return False

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 매장별 상품 데이터
    stores = ['daiso', 'costco', 'ikea', 'oliveyoung', 'traders', 'convenience']
    summary = {'updated_at': datetime.now().isoformat(), 'stores': {}}

    for store in stores:
        try:
            cursor.execute("""
                SELECT * FROM products WHERE store = ? ORDER BY created_at DESC
            """, (store,))
            products = [dict(row) for row in cursor.fetchall()]

            # JSON 저장
            output_file = EXPORT_DIR / f'{store}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)

            summary['stores'][store] = len(products)
            logger.info(f"Exported {len(products)} products for {store}")
        except Exception as e:
            logger.error(f"Error exporting {store}: {e}")
            summary['stores'][store] = 0

    # YouTube 영상 데이터
    try:
        cursor.execute("SELECT * FROM videos ORDER BY created_at DESC")
        videos = [dict(row) for row in cursor.fetchall()]

        with open(EXPORT_DIR / 'youtube_videos.json', 'w', encoding='utf-8') as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)

        summary['total_videos'] = len(videos)
        logger.info(f"Exported {len(videos)} videos")
    except Exception as e:
        logger.error(f"Error exporting videos: {e}")
        summary['total_videos'] = 0

    # YouTube 기반 상품
    try:
        cursor.execute("SELECT * FROM youtube_products ORDER BY created_at DESC")
        yt_products = [dict(row) for row in cursor.fetchall()]

        with open(EXPORT_DIR / 'youtube_products.json', 'w', encoding='utf-8') as f:
            json.dump(yt_products, f, ensure_ascii=False, indent=2)

        summary['total_youtube_products'] = len(yt_products)
    except Exception as e:
        logger.error(f"Error exporting youtube_products: {e}")
        summary['total_youtube_products'] = 0

    # 요약 저장
    with open(EXPORT_DIR / 'summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    conn.close()
    return True


def push_to_github():
    """GitHub에 푸시"""
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN not set")
        return False

    try:
        # 리포지토리 클론 또는 풀
        if not REPO_DIR.exists():
            logger.info("Cloning repository...")
            subprocess.run([
                'git', 'clone', '--depth', '1',
                f'https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git',
                str(REPO_DIR)
            ], check=True, capture_output=True)
        else:
            logger.info("Pulling latest changes...")
            subprocess.run(['git', 'pull'], cwd=REPO_DIR, check=True, capture_output=True)

        # 데이터 복사
        target_dir = REPO_DIR / 'web' / 'public' / 'data'
        target_dir.mkdir(parents=True, exist_ok=True)

        for json_file in EXPORT_DIR.glob('*.json'):
            target_file = target_dir / json_file.name
            with open(json_file, 'r', encoding='utf-8') as src:
                with open(target_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.info(f"Copied {json_file.name}")

        # Git 커밋 및 푸시
        subprocess.run(['git', 'config', 'user.email', 'bot@shopping-helper.local'], cwd=REPO_DIR, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Shopping Helper Bot'], cwd=REPO_DIR, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=REPO_DIR, check=True)

        # 변경사항 확인
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=REPO_DIR)
        if result.returncode == 0:
            logger.info("No changes to commit")
            return True

        commit_msg = f"data: Auto-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=REPO_DIR, check=True)
        subprocess.run(['git', 'push'], cwd=REPO_DIR, check=True)

        logger.info("Successfully pushed to GitHub!")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def main():
    """메인 동기화 함수"""
    logger.info("=== Starting GitHub Sync ===")

    if export_to_json():
        push_to_github()

    logger.info("=== Sync Complete ===")


if __name__ == '__main__':
    main()
