# -*- coding: utf-8 -*-
"""
카탈로그 기반 상품 매칭 (AI 없이)
다이소 카탈로그 470개와 영상 자막을 키워드 매칭
"""
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# config에서 DB 경로 가져오기
try:
    from config import DB_PATH
except ImportError:
    DB_PATH = Path(__file__).parent.parent / "data" / "products.db"


# 상수 정의
MAX_PRODUCTS_PER_VIDEO = 10
MIN_MATCH_SCORE = 0.25
MAX_KEYWORD_LENGTH = 50
MAX_NAME_LENGTH = 200


def _sanitize_text(text: Optional[str], max_length: int = 10000) -> str:
    """텍스트 정제 및 길이 제한"""
    if not text:
        return ""
    # 제어 문자 제거 및 길이 제한
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(text))
    return cleaned[:max_length]


def extract_keywords(name: Optional[str]) -> List[str]:
    """상품명에서 검색 키워드 추출"""
    if not name:
        return []
    # 입력 검증
    name = _sanitize_text(name, MAX_NAME_LENGTH)
    # 불필요 문자 제거
    clean = re.sub(r'[\[\]\(\)\d+ml\d+g\d+p\d+개입]', ' ', name.lower())
    clean = re.sub(r'\s+', ' ', clean).strip()
    words = [w[:MAX_KEYWORD_LENGTH] for w in clean.split() if 2 <= len(w) <= MAX_KEYWORD_LENGTH]
    return words

def run_catalog_matching() -> int:
    """카탈로그 매칭 실행

    Returns:
        총 상품 수
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 다이소 카탈로그 로드
    cur.execute('SELECT * FROM daiso_catalog')
    catalog = cur.fetchall()
    print(f'다이소 카탈로그: {len(catalog)}개')

    # 2. 자막 있는 영상 (상품 없는 것만)
    cur.execute('''
        SELECT DISTINCT v.* FROM videos v
        LEFT JOIN products p ON v.video_id = p.video_id
        WHERE v.transcript IS NOT NULL
        AND v.transcript != ''
        AND p.id IS NULL
    ''')
    videos = cur.fetchall()
    print(f'상품 추출 대상 영상: {len(videos)}개')

    # 3. 카탈로그 준비 (입력 검증 포함)
    catalog_items = []
    for c in catalog:
        name = _sanitize_text(c['name'], MAX_NAME_LENGTH)
        keywords = extract_keywords(name)
        if not keywords:
            continue
        catalog_items.append({
            'product_no': _sanitize_text(c['product_no'], 50),
            'name': name,
            'price': int(c['price']) if c['price'] else 0,
            'image_url': _sanitize_text(c['image_url'], 500),
            'product_url': _sanitize_text(c['product_url'], 500),
            'category': _sanitize_text(c['category'], 100),
            'keywords': keywords
        })

    # 4. 영상별 상품 매칭
    new_products = []
    for video in videos:
        # 입력 검증
        transcript = _sanitize_text(video['transcript']).lower()
        title = _sanitize_text(video['title'], 500).lower()
        combined = title + ' ' + transcript

        matches = []
        for item in catalog_items:
            if not item['keywords']:
                continue
            # 키워드 매칭
            matched_keywords = [kw for kw in item['keywords'] if kw in combined]
            if len(matched_keywords) >= 1:  # 1개만 매칭되어도 OK
                score = len(matched_keywords) / max(len(item['keywords']), 1)
                # 제목에 매칭되면 보너스
                title_match = any(kw in title for kw in matched_keywords)
                if title_match:
                    score += 0.3
                matches.append((score, item, matched_keywords))

        # 점수 높은 순, 상위 N개
        matches.sort(key=lambda x: x[0], reverse=True)
        for score, item, kws in matches[:MAX_PRODUCTS_PER_VIDEO]:
            if score >= MIN_MATCH_SCORE:
                new_products.append({
                    'video_id': video['video_id'],
                    'name': item['name'],
                    'price': item['price'],
                    'category': item['category'],
                    'store_key': 'daiso',
                    'official_code': item['product_no'],
                    'official_name': item['name'],
                    'official_price': item['price'],
                    'official_image_url': item['image_url'],
                    'official_product_url': item['product_url'],
                    'channel_title': video['channel_title'],
                    'view_count': video['view_count'],
                })

    print(f'\n새로 매칭된 상품: {len(new_products)}개')

    # 5. DB 저장
    added = 0
    for p in new_products:
        # 중복 체크
        cur.execute('SELECT id FROM products WHERE video_id=? AND name=?',
                   (p['video_id'], p['name']))
        if cur.fetchone():
            continue

        cur.execute('''
            INSERT INTO products (video_id, name, price, category, store_key, store_name,
                official_code, official_name, official_price, official_image_url, official_product_url,
                is_matched, is_approved, source_view_count, created_at)
            VALUES (?, ?, ?, ?, ?, '다이소', ?, ?, ?, ?, ?, 1, 1, ?, datetime('now'))
        ''', (p['video_id'], p['name'], p['price'], p['category'], p['store_key'],
              p['official_code'], p['official_name'], p['official_price'],
              p['official_image_url'], p['official_product_url'], p['view_count']))
        added += 1

    conn.commit()

    # 결과
    cur.execute('SELECT COUNT(*) FROM products')
    total = cur.fetchone()[0]
    print(f'추가된 상품: {added}개')
    print(f'총 상품 수: {total}개')

    conn.close()
    return total

if __name__ == '__main__':
    run_catalog_matching()
