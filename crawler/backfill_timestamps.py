# -*- coding: utf-8 -*-
"""
기존 상품 타임스탬프 백필 스크립트
1단계: 이미 타임스탬프 자막이 있는 영상 → 상품 재분석
2단계: 자막이 없거나 타임스탬프 없는 자막 → YouTube API 재추출 후 재분석
"""
import sqlite3
import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(__file__))
from smart_extractor import extract_recommendation_context, extract_keywords, parse_timestamp

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def update_product_timestamp(conn, product_id, timestamp_sec, timestamp_text):
    conn.execute(
        'UPDATE products SET timestamp_sec=?, timestamp_text=? WHERE id=?',
        (timestamp_sec, timestamp_text, product_id)
    )

def phase1_reanalyze_existing():
    """이미 타임스탬프 자막이 있는 영상의 상품 재분석"""
    conn = get_conn()

    # 타임스탬프 없는 상품 + 타임스탬프 자막이 있는 영상
    rows = conn.execute('''
        SELECT p.id, p.name, p.video_id, v.transcript
        FROM products p
        JOIN videos v ON p.video_id = v.video_id
        WHERE (p.timestamp_sec IS NULL OR p.timestamp_sec = 0)
        AND v.transcript LIKE '%[%:%]%'
    ''').fetchall()

    updated = 0
    for row in rows:
        transcript = row['transcript']
        product_name = row['name']
        keywords = extract_keywords(product_name)

        result = extract_recommendation_context(transcript, product_name, keywords)
        if result['timestamp_sec'] and result['timestamp_sec'] > 0:
            update_product_timestamp(conn, row['id'], result['timestamp_sec'], result['timestamp_text'])
            updated += 1

    conn.commit()
    conn.close()
    print(f"[Phase 1] 기존 타임스탬프 자막에서 {updated}/{len(rows)}개 상품 업데이트")
    return updated

def phase2_fetch_and_update(delay=3.0):
    """YouTube API로 자막 재추출 후 상품 업데이트"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("[Phase 2] youtube-transcript-api 패키지가 필요합니다")
        return 0

    conn = get_conn()

    # 자막이 없거나 타임스탬프 없는 영상의 video_id 목록
    video_rows = conn.execute('''
        SELECT DISTINCT p.video_id
        FROM products p
        JOIN videos v ON p.video_id = v.video_id
        WHERE (p.timestamp_sec IS NULL OR p.timestamp_sec = 0)
        AND (v.transcript IS NULL OR v.transcript = '' OR v.transcript NOT LIKE '%[%:%]%')
    ''').fetchall()

    video_ids = [r['video_id'] for r in video_rows]
    total = len(video_ids)
    print(f"[Phase 2] YouTube API로 {total}개 영상 자막 재추출 시작 (간격: {delay}초)")

    api = YouTubeTranscriptApi()
    fetched = 0
    failed = 0
    updated_products = 0

    for i, vid in enumerate(video_ids):
        try:
            # YouTube API 호출
            transcript_list = api.list(vid)

            # 한국어 우선, 없으면 첫 번째 언어
            selected_lang = None
            for t in transcript_list:
                if t.language_code.startswith('ko'):
                    selected_lang = t.language_code
                    break

            if not selected_lang:
                # 첫 번째 사용 가능한 언어
                for t in transcript_list:
                    selected_lang = t.language_code
                    break

            if not selected_lang:
                print(f"  [{i+1}/{total}] {vid}: 사용 가능한 자막 없음")
                failed += 1
                time.sleep(delay)
                continue

            # 자막 가져오기
            fetched_transcript = api.fetch(vid, languages=[selected_lang])

            # 타임스탬프 포함 텍스트로 변환
            parts = []
            for snippet in fetched_transcript:
                text = snippet.text.strip()
                if not text:
                    continue
                start = getattr(snippet, 'start', None)
                if start is not None:
                    total_sec = int(start)
                    mins = total_sec // 60
                    secs = total_sec % 60
                    parts.append(f"[{mins}:{secs:02d}] {text}")
                else:
                    parts.append(text)

            transcript_text = " ".join(parts)

            if not transcript_text:
                print(f"  [{i+1}/{total}] {vid}: 자막 비어있음")
                failed += 1
                time.sleep(delay)
                continue

            # DB에 자막 업데이트
            conn.execute(
                'UPDATE videos SET transcript=? WHERE video_id=?',
                (transcript_text, vid)
            )
            fetched += 1

            # 이 영상의 모든 타임스탬프 없는 상품 업데이트
            products = conn.execute('''
                SELECT id, name FROM products
                WHERE video_id=? AND (timestamp_sec IS NULL OR timestamp_sec = 0)
            ''', (vid,)).fetchall()

            for p in products:
                keywords = extract_keywords(p['name'])
                result = extract_recommendation_context(transcript_text, p['name'], keywords)
                if result['timestamp_sec'] and result['timestamp_sec'] > 0:
                    update_product_timestamp(conn, p['id'], result['timestamp_sec'], result['timestamp_text'])
                    updated_products += 1

            # 10개마다 중간 커밋
            if fetched % 10 == 0:
                conn.commit()

            print(f"  [{i+1}/{total}] {vid}: 자막 {len(parts)}줄, 상품 {len(products)}개 처리")

        except Exception as e:
            err_msg = str(e)
            if 'blocking' in err_msg.lower() or 'ip' in err_msg.lower():
                print(f"\n[!] YouTube IP 차단 감지 ({i+1}/{total}). 30초 대기 후 재시도...")
                time.sleep(30)
                try:
                    # 재시도
                    fetched_transcript = api.fetch(vid, languages=['ko'])
                    parts = []
                    for snippet in fetched_transcript:
                        text = snippet.text.strip()
                        if not text:
                            continue
                        start = getattr(snippet, 'start', None)
                        if start is not None:
                            total_sec = int(start)
                            mins = total_sec // 60
                            secs = total_sec % 60
                            parts.append(f"[{mins}:{secs:02d}] {text}")
                        else:
                            parts.append(text)
                    transcript_text = " ".join(parts)
                    if transcript_text:
                        conn.execute('UPDATE videos SET transcript=? WHERE video_id=?', (transcript_text, vid))
                        fetched += 1
                        products = conn.execute('''
                            SELECT id, name FROM products
                            WHERE video_id=? AND (timestamp_sec IS NULL OR timestamp_sec = 0)
                        ''', (vid,)).fetchall()
                        for p in products:
                            keywords = extract_keywords(p['name'])
                            result = extract_recommendation_context(transcript_text, p['name'], keywords)
                            if result['timestamp_sec'] and result['timestamp_sec'] > 0:
                                update_product_timestamp(conn, p['id'], result['timestamp_sec'], result['timestamp_text'])
                                updated_products += 1
                        print(f"  [{i+1}/{total}] {vid}: 재시도 성공")
                except Exception as e2:
                    print(f"  [{i+1}/{total}] {vid}: 재시도도 실패 - {str(e2)[:80]}")
                    failed += 1
            else:
                print(f"  [{i+1}/{total}] {vid}: 실패 - {err_msg[:80]}")
                failed += 1

        # 요청 간 지연
        time.sleep(delay)

    conn.commit()
    conn.close()

    print(f"\n[Phase 2 결과]")
    print(f"  자막 추출 성공: {fetched}/{total}")
    print(f"  자막 추출 실패: {failed}/{total}")
    print(f"  상품 타임스탬프 업데이트: {updated_products}")

    return updated_products

def main():
    print("=== 타임스탬프 백필 시작 ===\n")

    # Phase 1: 이미 있는 자막 활용
    p1 = phase1_reanalyze_existing()

    # Phase 2: YouTube API로 재추출
    p2 = phase2_fetch_and_update(delay=3.0)

    # 최종 통계
    conn = get_conn()
    total = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    with_ts = conn.execute('SELECT COUNT(*) FROM products WHERE timestamp_sec IS NOT NULL AND timestamp_sec > 0').fetchone()[0]
    conn.close()

    print(f"\n=== 백필 완료 ===")
    print(f"전체 상품: {total}")
    print(f"타임스탬프 있음: {with_ts} ({with_ts/total*100:.1f}%)")
    print(f"타임스탬프 없음: {total - with_ts} ({(total-with_ts)/total*100:.1f}%)")

if __name__ == '__main__':
    main()
