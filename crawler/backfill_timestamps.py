# -*- coding: utf-8 -*-
"""
기존 상품 타임스탬프 백필 스크립트 (v3)

Phase 1: 이미 타임스탬프 자막이 있는 영상 → 상품 재분석
Phase 2: yt-dlp extract_info로 챕터/메타데이터 → 상품 매칭
Phase 3: 비디오 설명에서 타임스탬프 파싱 → 상품 매칭
Phase 4: 비디오 길이 + 상품 순서 기반 타임스탬프 추정
"""
import sqlite3
import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(__file__))
from smart_extractor import extract_recommendation_context, extract_keywords, seconds_to_timestamp

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


def normalize_text(text):
    """텍스트 정규화: 소문자, 공백 정리, 특수문자 제거"""
    text = text.lower().strip()
    text = re.sub(r'[^\w가-힣\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def fuzzy_match_score(product_name, chapter_title):
    """상품명과 챕터 제목의 유사도 점수 (0~1)"""
    pn = normalize_text(product_name)
    ct = normalize_text(chapter_title)

    if not pn or not ct:
        return 0.0

    # 완전 포함
    if pn in ct or ct in pn:
        return 1.0

    # 단어 기반 매칭
    p_words = set(w for w in pn.split() if len(w) >= 2)
    c_words = set(w for w in ct.split() if len(w) >= 2)

    if not p_words or not c_words:
        return 0.0

    # 공통 단어 비율
    common = p_words & c_words
    if common:
        return len(common) / min(len(p_words), len(c_words))

    # 부분 문자열 매칭 (3글자 이상 공통)
    for pw in p_words:
        for cw in c_words:
            if len(pw) >= 3 and len(cw) >= 3:
                if pw[:3] in cw or cw[:3] in pw:
                    return 0.5

    return 0.0


def phase1_reanalyze_existing():
    """Phase 1: 이미 타임스탬프 자막이 있는 영상의 상품 재분석"""
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


def phase2_chapters_from_metadata(delay=1.0):
    """Phase 2: yt-dlp extract_info로 챕터 메타데이터 가져와서 상품 매칭"""
    try:
        import yt_dlp
    except ImportError:
        print("[Phase 2] yt-dlp 패키지가 필요합니다: pip install yt-dlp")
        return 0

    conn = get_conn()

    # 타임스탬프 없는 상품이 있는 비디오 목록
    video_rows = conn.execute('''
        SELECT DISTINCT v.video_id, v.duration
        FROM products p
        JOIN videos v ON p.video_id = v.video_id
        WHERE (p.timestamp_sec IS NULL OR p.timestamp_sec = 0)
    ''').fetchall()

    video_ids = [(r['video_id'], r['duration']) for r in video_rows]
    total = len(video_ids)
    print(f"[Phase 2] {total}개 영상에서 챕터 메타데이터 추출 시작")

    updated_products = 0
    chapters_found = 0
    duration_updated = 0

    ydl_opts = {'skip_download': True, 'quiet': True, 'no_warnings': True}

    for i, (vid, db_duration) in enumerate(video_ids):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    f'https://www.youtube.com/watch?v={vid}',
                    download=False
                )

            chapters = info.get('chapters', [])
            duration = info.get('duration', 0)

            # 비디오 duration 업데이트 (없는 경우)
            if duration and (not db_duration or db_duration == 0):
                conn.execute(
                    'UPDATE videos SET duration=? WHERE video_id=?',
                    (duration, vid)
                )
                duration_updated += 1

            if not chapters:
                if (i + 1) % 50 == 0:
                    print(f"  [{i+1}/{total}] 진행 중...")
                    conn.commit()
                time.sleep(delay)
                continue

            chapters_found += 1

            # 이 영상의 타임스탬프 없는 상품
            products = conn.execute('''
                SELECT id, name FROM products
                WHERE video_id=? AND (timestamp_sec IS NULL OR timestamp_sec = 0)
            ''', (vid,)).fetchall()

            for p in products:
                best_score = 0
                best_chapter = None

                for ch in chapters:
                    score = fuzzy_match_score(p['name'], ch.get('title', ''))
                    if score > best_score:
                        best_score = score
                        best_chapter = ch

                if best_score >= 0.4 and best_chapter:
                    ts_sec = int(best_chapter['start_time'])
                    ts_text = seconds_to_timestamp(ts_sec)
                    update_product_timestamp(conn, p['id'], ts_sec, ts_text)
                    updated_products += 1

            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{total}] 진행 중... (챕터: {chapters_found}, 매칭: {updated_products})")
                conn.commit()

        except Exception as e:
            err_msg = str(e)[:80]
            if 'Sign in' in err_msg or 'bot' in err_msg:
                # bot detection - skip but don't stop
                pass
            elif (i + 1) % 50 == 0:
                print(f"  [{i+1}/{total}] 에러: {err_msg}")

        time.sleep(delay)

    conn.commit()
    conn.close()

    print(f"[Phase 2] 챕터 보유 영상: {chapters_found}/{total}")
    print(f"[Phase 2] duration 업데이트: {duration_updated}")
    print(f"[Phase 2] 챕터에서 매칭된 상품: {updated_products}")
    return updated_products


def phase3_description_timestamps():
    """Phase 3: 비디오 설명에서 타임스탬프+키워드 매칭"""
    conn = get_conn()

    rows = conn.execute('''
        SELECT p.id, p.name, p.video_id, v.description
        FROM products p
        JOIN videos v ON p.video_id = v.video_id
        WHERE (p.timestamp_sec IS NULL OR p.timestamp_sec = 0)
        AND v.description IS NOT NULL AND v.description != ''
    ''').fetchall()

    updated = 0
    for row in rows:
        desc = row['description']
        product_name = row['name']

        # 설명에서 타임스탬프 라인 추출
        ts_entries = []
        for line in desc.split('\n'):
            line = line.strip()
            # M:SS 또는 H:MM:SS 패턴으로 시작
            match = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?\s+(.+)', line)
            if match:
                groups = match.groups()
                if groups[2]:  # H:MM:SS
                    sec = int(groups[0]) * 3600 + int(groups[1]) * 60 + int(groups[2])
                else:  # M:SS
                    sec = int(groups[0]) * 60 + int(groups[1])
                title = groups[3].strip()
                ts_entries.append((sec, title))

        if not ts_entries:
            continue

        # 상품명과 타임스탬프 엔트리 매칭
        best_score = 0
        best_sec = None

        for sec, title in ts_entries:
            score = fuzzy_match_score(product_name, title)
            if score > best_score:
                best_score = score
                best_sec = sec

        if best_score >= 0.4 and best_sec is not None:
            ts_text = seconds_to_timestamp(best_sec)
            update_product_timestamp(conn, row['id'], best_sec, ts_text)
            updated += 1

    conn.commit()
    conn.close()
    print(f"[Phase 3] 설명 타임스탬프에서 {updated}개 상품 업데이트")
    return updated


def phase4_estimate_from_position():
    """Phase 4: 비디오 길이 + 상품 순서 기반 타임스탬프 추정"""
    conn = get_conn()

    # 타임스탬프 없는 상품이 있는 비디오 (duration 있는 것만)
    video_rows = conn.execute('''
        SELECT DISTINCT v.video_id, v.duration
        FROM products p
        JOIN videos v ON p.video_id = v.video_id
        WHERE (p.timestamp_sec IS NULL OR p.timestamp_sec = 0)
        AND v.duration IS NOT NULL AND v.duration > 0
    ''').fetchall()

    updated = 0
    for vr in video_rows:
        vid = vr['video_id']
        duration = vr['duration']

        # 이 영상의 모든 상품 (순서대로)
        all_products = conn.execute('''
            SELECT id, name, timestamp_sec FROM products
            WHERE video_id=? AND is_hidden=0
            ORDER BY id
        ''', (vid,)).fetchall()

        if not all_products:
            continue

        n = len(all_products)

        # 이미 타임스탬프가 있는 상품들의 위치 참고
        known_timestamps = []
        for idx, p in enumerate(all_products):
            if p['timestamp_sec'] and p['timestamp_sec'] > 0:
                known_timestamps.append((idx, p['timestamp_sec']))

        for idx, p in enumerate(all_products):
            if p['timestamp_sec'] and p['timestamp_sec'] > 0:
                continue

            # 추정: 이미 알려진 타임스탬프가 있으면 보간, 없으면 균등 분배
            if known_timestamps:
                # 가장 가까운 알려진 타임스탬프 기반 보간
                estimated_sec = _interpolate_timestamp(
                    idx, n, duration, known_timestamps
                )
            else:
                # 균등 분배: 처음 10% ~ 마지막 90% 구간
                start_offset = int(duration * 0.05)  # 인트로 5% 건너뜀
                end_offset = int(duration * 0.95)  # 아웃트로 5% 건너뜀
                usable = end_offset - start_offset

                if n == 1:
                    estimated_sec = start_offset + usable // 2
                else:
                    estimated_sec = start_offset + int(usable * idx / (n - 1)) if n > 1 else start_offset

            estimated_sec = max(0, min(estimated_sec, duration - 1))
            ts_text = seconds_to_timestamp(estimated_sec)
            update_product_timestamp(conn, p['id'], estimated_sec, ts_text)
            updated += 1

    conn.commit()
    conn.close()
    print(f"[Phase 4] 위치 기반 추정으로 {updated}개 상품 업데이트")
    return updated


def _interpolate_timestamp(target_idx, total_products, duration, known_timestamps):
    """알려진 타임스탬프를 기반으로 보간 추정"""
    # 앞뒤로 가장 가까운 알려진 값 찾기
    before = None
    after = None

    for idx, ts in known_timestamps:
        if idx <= target_idx:
            if before is None or idx > before[0]:
                before = (idx, ts)
        if idx >= target_idx:
            if after is None or idx < after[0]:
                after = (idx, ts)

    if before and after and before[0] != after[0]:
        # 선형 보간
        ratio = (target_idx - before[0]) / (after[0] - before[0])
        return int(before[1] + ratio * (after[1] - before[1]))
    elif before:
        # 앞의 값만 있으면 뒤로 추정
        avg_gap = before[1] / max(before[0], 1)
        return int(before[1] + avg_gap * (target_idx - before[0]))
    elif after:
        # 뒤의 값만 있으면 앞으로 추정
        avg_gap = after[1] / max(after[0], 1)
        return max(0, int(after[1] - avg_gap * (after[0] - target_idx)))
    else:
        # 균등 분배 폴백
        return int(duration * 0.05 + duration * 0.9 * target_idx / max(total_products - 1, 1))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== 타임스탬프 백필 시작 (v3) ===\n")

    # Phase 1: 이미 있는 자막 활용
    p1 = phase1_reanalyze_existing()

    # Phase 2: yt-dlp 메타데이터에서 챕터 추출
    p2 = phase2_chapters_from_metadata(delay=0.5)

    # Phase 3: 비디오 설명에서 타임스탬프 매칭
    p3 = phase3_description_timestamps()

    # Phase 4: 위치 기반 추정 (남은 상품)
    p4 = phase4_estimate_from_position()

    # 최종 통계
    conn = get_conn()
    total = conn.execute('SELECT COUNT(*) FROM products WHERE is_hidden=0').fetchone()[0]
    with_ts = conn.execute('SELECT COUNT(*) FROM products WHERE is_hidden=0 AND timestamp_sec IS NOT NULL AND timestamp_sec > 0').fetchone()[0]
    conn.close()

    print(f"\n=== 백필 완료 ===")
    print(f"전체 상품 (활성): {total}")
    print(f"타임스탬프 있음: {with_ts} ({with_ts/total*100:.1f}%)")
    print(f"타임스탬프 없음: {total - with_ts} ({(total-with_ts)/total*100:.1f}%)")
    print(f"\n업데이트 내역:")
    print(f"  Phase 1 (자막 재분석): {p1}")
    print(f"  Phase 2 (챕터 매칭): {p2}")
    print(f"  Phase 3 (설명 매칭): {p3}")
    print(f"  Phase 4 (위치 추정): {p4}")
    print(f"  합계: {p1 + p2 + p3 + p4}")


if __name__ == '__main__':
    main()
