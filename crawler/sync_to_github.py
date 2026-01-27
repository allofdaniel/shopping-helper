# -*- coding: utf-8 -*-
"""
GitHub 자동 동기화 스크립트
수집된 데이터를 JSON으로 변환하고 web/public/data/에 저장합니다.
GitHub Actions에서 직접 호출되며, git push는 워크플로우에서 처리합니다.
"""
import os
import sys
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 경로 설정
BASE_DIR = Path(__file__).parent          # crawler/
PROJECT_ROOT = BASE_DIR.parent            # project root
DB_PATH = PROJECT_ROOT / 'data' / 'products.db'
OUTPUT_DIR = PROJECT_ROOT / 'web' / 'public' / 'data'

# 매장 목록 (API route.ts의 STORES와 일치)
STORES = ['daiso', 'costco', 'oliveyoung', 'traders', 'ikea', 'convenience']

# 프론트엔드에 필요한 상품 필드만 추출 (용량 절감)
PRODUCT_FIELDS = [
    'id', 'video_id', 'name', 'price', 'category', 'reason',
    'timestamp_sec', 'timestamp_text', 'keywords', 'store_key', 'store_name',
    'official_code', 'official_name', 'official_price',
    'official_image_url', 'official_product_url',
    'is_matched', 'is_approved', 'source_view_count', 'created_at',
    'recommendation_quote', 'store_locations', 'product_code_display',
    'availability_note', 'rating', 'review_count', 'order_count',
]


def get_db_connection():
    """SQLite 연결 (존재 확인 포함)"""
    if not DB_PATH.exists():
        logger.error(f"DB not found: {DB_PATH}")
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """sqlite3.Row를 dict로 변환 + keywords JSON 파싱"""
    d = dict(row)
    # keywords가 JSON 문자열인 경우 파싱
    if d.get('keywords') and isinstance(d['keywords'], str):
        try:
            d['keywords'] = json.loads(d['keywords'])
        except (json.JSONDecodeError, TypeError):
            d['keywords'] = []
    elif not d.get('keywords'):
        d['keywords'] = []
    return d


def clean_product(product):
    """프론트엔드에 필요한 필드만 추출"""
    cleaned = {}
    for field in PRODUCT_FIELDS:
        if field in product:
            cleaned[field] = product[field]
    return cleaned


def export_store_json(conn, store_key, output_path):
    """매장별 JSON 파일 생성 (API route.ts가 읽는 형식)"""
    cursor = conn.cursor()

    # video 메타데이터 JOIN
    cursor.execute("""
        SELECT p.*, v.title as video_title, v.channel_title,
               v.thumbnail_url, v.view_count as video_view_count
        FROM products p
        LEFT JOIN videos v ON p.video_id = v.video_id
        WHERE p.is_hidden = 0 AND p.store_key = ?
        ORDER BY p.source_view_count DESC
    """, (store_key,))

    products = [clean_product(row_to_dict(row)) for row in cursor.fetchall()]

    # API가 기대하는 형식: { "products": [...] }
    data = {
        "updated_at": datetime.now().isoformat(),
        "total": len(products),
        "products": products,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    return len(products)


def export_all_products(conn, output_path):
    """전체 상품 JSON (youtube_products.json 호환)"""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*, v.title as video_title, v.channel_title,
               v.thumbnail_url, v.view_count as video_view_count
        FROM products p
        LEFT JOIN videos v ON p.video_id = v.video_id
        WHERE p.is_hidden = 0
        ORDER BY p.source_view_count DESC
    """)

    products = [clean_product(row_to_dict(row)) for row in cursor.fetchall()]

    data = {
        "updated_at": datetime.now().isoformat(),
        "total": len(products),
        "products": products,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    return len(products)


def export_videos(conn, output_path):
    """YouTube 영상 JSON"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM videos ORDER BY created_at DESC")
        videos = [dict(row) for row in cursor.fetchall()]

        data = {
            "updated_at": datetime.now().isoformat(),
            "total": len(videos),
            "videos": videos,
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

        return len(videos)
    except Exception as e:
        logger.warning(f"Error exporting videos: {e}")
        return 0


def export_summary(store_counts, total_products, total_videos, output_path):
    """통계 요약 JSON"""
    summary = {
        "updated_at": datetime.now().isoformat(),
        "total_products": total_products,
        "total_videos": total_videos,
        "stores": store_counts,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    """메인 동기화 함수"""
    logger.info("=== Starting Data Export ===")
    logger.info(f"DB: {DB_PATH}")
    logger.info(f"Output: {OUTPUT_DIR}")

    conn = get_db_connection()
    if not conn:
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    store_counts = {}
    total_products = 0

    # 1. 매장별 JSON 파일 생성
    for store in STORES:
        output_file = OUTPUT_DIR / f'{store}.json'
        count = export_store_json(conn, store, output_file)
        store_counts[store] = count
        total_products += count
        logger.info(f"  {store}: {count} products")

    # 2. 전체 상품 JSON (youtube_products.json + products_latest.json)
    all_count = export_all_products(conn, OUTPUT_DIR / 'youtube_products.json')
    export_all_products(conn, OUTPUT_DIR / 'products_latest.json')
    logger.info(f"  all products: {all_count}")

    # 3. YouTube 영상 JSON
    video_count = export_videos(conn, OUTPUT_DIR / 'youtube_videos.json')
    logger.info(f"  videos: {video_count}")

    # 4. 통계 요약
    export_summary(store_counts, total_products, video_count, OUTPUT_DIR / 'summary.json')

    conn.close()

    logger.info(f"=== Export Complete: {total_products} products, {video_count} videos ===")
    return total_products > 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
