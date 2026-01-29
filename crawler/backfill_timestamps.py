# -*- coding: utf-8 -*-
"""
기존 상품 타임스탬프 백필 스크립트
1단계: 이미 타임스탬프 자막이 있는 영상 → 상품 재분석
2단계: yt-dlp로 자막 다운로드 → 타임스탬프 포함 텍스트 변환 → 상품 업데이트
"""
import sqlite3
import sys
import os
import re
import time
import json
import tempfile
import glob
import shutil

sys.path.insert(0, os.path.dirname(__file__))
from smart_extractor import extract_recommendation_context, extract_keywords

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


def parse_json3_to_timestamped_text(json3_path):
    """json3 자막 파일을 [M:SS] 포맷 텍스트로 변환"""
    with open(json3_path, encoding='utf-8') as f:
        data = json.load(f)

    events = data.get('events', [])
    parts = []
    for ev in events:
        start_ms = ev.get('tStartMs', 0)
        segs = ev.get('segs', [])
        text = ''.join(s.get('utf8', '') for s in segs).strip()
        text = text.replace('\n', ' ')
        if text:
            total_sec = start_ms // 1000
            mins = total_sec // 60
            secs = total_sec % 60
            parts.append(f"[{mins}:{secs:02d}] {text}")

    return ' '.join(parts), len(parts)


def parse_vtt_to_timestamped_text(vtt_path):
    """vtt 자막 파일을 [M:SS] 포맷 텍스트로 변환"""
    with open(vtt_path, encoding='utf-8') as f:
        content = f.read()

    parts = []
    # VTT 타임스탬프 패턴: 00:00:05.520 --> 00:00:07.960
    pattern = r'(\d{2}):(\d{2}):(\d{2})\.\d{3}\s*-->'
    blocks = re.split(r'\n\n+', content)

    for block in blocks:
        match = re.search(pattern, block)
        if match:
            h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
            total_sec = h * 3600 + m * 60 + s
            mins = total_sec // 60
            secs = total_sec % 60
            # 타임스탬프 라인 이후의 텍스트 추출
            lines = block.strip().split('\n')
            text_lines = []
            found_timestamp = False
            for line in lines:
                if '-->' in line:
                    found_timestamp = True
                    continue
                if found_timestamp and line.strip():
                    # HTML 태그 제거
                    clean = re.sub(r'<[^>]+>', '', line.strip())
                    if clean:
                        text_lines.append(clean)
            text = ' '.join(text_lines)
            if text:
                parts.append(f"[{mins}:{secs:02d}] {text}")

    return ' '.join(parts), len(parts)


def fetch_subtitle_with_ytdlp(video_id, tmpdir):
    """yt-dlp로 자막 다운로드 후 타임스탬프 텍스트 반환"""
    try:
        import yt_dlp
    except ImportError:
        print("[!] yt-dlp 패키지가 필요합니다: pip install yt-dlp")
        return None

    outtmpl = os.path.join(tmpdir, f'{video_id}')

    # 먼저 json3 형식 시도
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['ko'],
        'subtitlesformat': 'json3',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

        # json3 파일 찾기
        json3_files = glob.glob(os.path.join(tmpdir, f'{video_id}*.json3'))
        if json3_files:
            text, count = parse_json3_to_timestamped_text(json3_files[0])
            # 정리
            for f in json3_files:
                os.remove(f)
            return text if text else None

    except Exception:
        pass

    # json3 실패 시 vtt 형식 시도
    ydl_opts['subtitlesformat'] = 'vtt'
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

        vtt_files = glob.glob(os.path.join(tmpdir, f'{video_id}*.vtt'))
        if vtt_files:
            text, count = parse_vtt_to_timestamped_text(vtt_files[0])
            for f in vtt_files:
                os.remove(f)
            return text if text else None

    except Exception:
        pass

    return None


def phase2_fetch_with_ytdlp(delay=2.0):
    """yt-dlp로 자막 다운로드 후 상품 업데이트"""
    try:
        import yt_dlp
    except ImportError:
        print("[Phase 2] yt-dlp 패키지가 필요합니다: pip install yt-dlp")
        return 0

    conn = get_conn()

    video_rows = conn.execute('''
        SELECT DISTINCT p.video_id
        FROM products p
        JOIN videos v ON p.video_id = v.video_id
        WHERE (p.timestamp_sec IS NULL OR p.timestamp_sec = 0)
        AND (v.transcript IS NULL OR v.transcript = '' OR v.transcript NOT LIKE '%[%:%]%')
    ''').fetchall()

    video_ids = [r['video_id'] for r in video_rows]
    total = len(video_ids)
    print(f"[Phase 2] yt-dlp로 {total}개 영상 자막 다운로드 시작 (간격: {delay}초)")

    tmpdir = tempfile.mkdtemp()
    fetched = 0
    failed = 0
    updated_products = 0

    for i, vid in enumerate(video_ids):
        try:
            transcript_text = fetch_subtitle_with_ytdlp(vid, tmpdir)

            if not transcript_text:
                print(f"  [{i+1}/{total}] {vid}: 자막 없음/실패")
                failed += 1
                time.sleep(delay)
                continue

            # DB에 자막 업데이트
            conn.execute(
                'UPDATE videos SET transcript=? WHERE video_id=?',
                (transcript_text, vid)
            )
            fetched += 1

            # 이 영상의 타임스탬프 없는 상품 업데이트
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

            if fetched % 10 == 0:
                conn.commit()

            print(f"  [{i+1}/{total}] {vid}: OK, 상품 {len(products)}개 처리")

        except Exception as e:
            print(f"  [{i+1}/{total}] {vid}: 에러 - {str(e)[:80]}")
            failed += 1

        time.sleep(delay)

    conn.commit()
    conn.close()
    shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\n[Phase 2 결과]")
    print(f"  자막 추출 성공: {fetched}/{total}")
    print(f"  자막 추출 실패: {failed}/{total}")
    print(f"  상품 타임스탬프 업데이트: {updated_products}")

    return updated_products


def main():
    print("=== 타임스탬프 백필 시작 ===\n")

    # Phase 1: 이미 있는 자막 활용
    p1 = phase1_reanalyze_existing()

    # Phase 2: yt-dlp로 자막 다운로드
    p2 = phase2_fetch_with_ytdlp(delay=2.0)

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
