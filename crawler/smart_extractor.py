# -*- coding: utf-8 -*-
"""
스마트 상품 추출기
- 설명란 분석
- 추천 문맥 확인
- 부정적 언급 필터링
- 정확한 추천템만 추출
"""
import sqlite3
import re
from datetime import datetime

DB_PATH = '../data/products.db'

# 추천 키워드 (긍정)
RECOMMEND_KEYWORDS = [
    '추천', '꿀템', '필수템', '강추', '대박', '최고', '인생템', '갓성비',
    '가성비', '존맛', '맛있', '좋아요', '사세요', '꼭 사', '무조건',
    '베스트', 'best', '픽', 'pick', '완전', '진짜 좋', '너무 좋',
    '사야해', '사야돼', '살 것', '살것', '구매각', '득템', '횡재',
    '재구매', '리뷰', '솔직', '실제', '써봤', '먹어봤', '사용해봤'
]

# 부정 키워드 (제외)
NEGATIVE_KEYWORDS = [
    '별로', '비추', '후회', '실망', '안 좋', '않좋', '싫', '최악',
    '돈 아까', '버렸', '환불', '교환', '불량', '짜증', '화나',
    '사지마', '사지 마', '구매 비추', '낭비'
]

# 설명란 추천템 패턴
DESCRIPTION_PATTERNS = [
    r'추천\s*템[:\s]*(.+?)(?:\n|$)',
    r'꿀템[:\s]*(.+?)(?:\n|$)',
    r'구매\s*링크[:\s]*(.+?)(?:\n|$)',
    r'제품\s*정보[:\s]*(.+?)(?:\n|$)',
    r'\d+[\.:\)]\s*([가-힣]+.+?)(?:\n|$)',  # 번호 목록
    r'[★☆●○►▶]\s*(.+?)(?:\n|$)',  # 마커 목록
]


def extract_keywords(name):
    """상품명에서 검색 키워드 추출"""
    clean = re.sub(r'[\[\]\(\)\d+ml\d+g\d+p\d+개입]', ' ', name.lower())
    clean = re.sub(r'\s+', ' ', clean).strip()
    words = [w for w in clean.split() if len(w) >= 2]
    return words


def parse_timestamp(text):
    """자막에서 타임스탬프 파싱 (예: [00:01:23] 또는 1:23)"""
    # 패턴: [00:01:23] 형식 또는 1:23 형식
    patterns = [
        r'\[(\d{1,2}):(\d{2}):(\d{2})\]',  # [00:01:23]
        r'\[(\d{1,2}):(\d{2})\]',  # [01:23]
        r'(\d{1,2}):(\d{2}):(\d{2})',  # 00:01:23
        r'(\d{1,2}):(\d{2})',  # 1:23
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                return int(groups[0]) * 3600 + int(groups[1]) * 60 + int(groups[2])
            elif len(groups) == 2:
                return int(groups[0]) * 60 + int(groups[1])
    return None


def seconds_to_timestamp(seconds):
    """초를 MM:SS 또는 HH:MM:SS 형식으로 변환"""
    if seconds is None:
        return None
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def extract_recommendation_context(text, product_name, keywords):
    """상품의 추천 문맥, 추천 이유, 타임스탬프 추출"""
    text_lower = text.lower()
    product_lower = product_name.lower()

    # 상품명 또는 키워드 위치 찾기
    pos = -1
    matched_term = None

    # 먼저 상품명으로 찾기
    if len(product_lower) >= 4:
        pos = text_lower.find(product_lower[:4])
        if pos != -1:
            matched_term = product_lower[:4]

    # 키워드로 찾기
    if pos == -1:
        for kw in keywords:
            if kw in text_lower:
                pos = text_lower.find(kw)
                matched_term = kw
                break

    if pos == -1:
        return {'score': 0.0, 'quote': None, 'timestamp_sec': None, 'timestamp_text': None}

    # 주변 텍스트 (앞뒤 150자) - 더 넓게
    start = max(0, pos - 150)
    end = min(len(text), pos + 150)
    context = text[start:end]
    context_lower = context.lower()

    # 추천 점수 계산
    score = 0.0
    found_positive = []

    for kw in RECOMMEND_KEYWORDS:
        if kw in context_lower:
            score += 0.15
            found_positive.append(kw)

    for kw in NEGATIVE_KEYWORDS:
        if kw in context_lower:
            score -= 0.3

    score = min(max(score, 0.0), 1.0)

    # 추천 이유 문장 추출 (상품명/키워드 포함된 문장)
    quote = None
    if score > 0:
        # 문장 단위로 분리
        sentences = re.split(r'[.!?。]\s*', context)
        for sent in sentences:
            sent_lower = sent.lower()
            if matched_term and matched_term in sent_lower:
                # 긍정 키워드가 포함된 문장 우선
                if any(pk in sent_lower for pk in found_positive):
                    quote = sent.strip()
                    break

        # 못 찾았으면 상품명 포함 문장
        if not quote:
            for sent in sentences:
                if matched_term and matched_term in sent.lower():
                    quote = sent.strip()
                    break

        # 그래도 없으면 전체 문맥
        if not quote and len(context.strip()) > 10:
            quote = context.strip()[:200]

    # 타임스탬프 추출 (문맥 앞부분에서)
    timestamp_sec = parse_timestamp(text[max(0, pos-50):pos+20])
    timestamp_text = seconds_to_timestamp(timestamp_sec)

    return {
        'score': score,
        'quote': quote,
        'timestamp_sec': timestamp_sec,
        'timestamp_text': timestamp_text,
        'positive_keywords': found_positive
    }


def check_recommendation_context(text, product_name):
    """상품이 추천 문맥에서 언급되었는지 확인 (하위 호환성)"""
    result = extract_recommendation_context(text, product_name, extract_keywords(product_name))
    return result['score']


def extract_from_description(description):
    """설명란에서 상품 목록 추출"""
    if not description:
        return []

    products = []

    for pattern in DESCRIPTION_PATTERNS:
        matches = re.findall(pattern, description, re.MULTILINE)
        for match in matches:
            # 정제
            clean = re.sub(r'https?://\S+', '', match)  # URL 제거
            clean = re.sub(r'[#@]\S+', '', clean)  # 해시태그 제거
            clean = clean.strip()

            if 3 <= len(clean) <= 50:  # 적절한 길이
                products.append(clean)

    return products


def load_all_catalogs(cur):
    """모든 스토어 카탈로그 로드"""
    all_items = []

    # 다이소
    try:
        cur.execute('SELECT * FROM daiso_catalog')
        for c in cur.fetchall():
            keywords = extract_keywords(c['name'])
            all_items.append({
                'product_no': c['product_no'],
                'name': c['name'],
                'price': c['price'],
                'image_url': c['image_url'],
                'product_url': c['product_url'],
                'category': c['category'],
                'store_key': 'daiso',
                'store_name': '다이소',
                'keywords': keywords
            })
        print(f'다이소 카탈로그: {len([i for i in all_items if i["store_key"]=="daiso"])}개')
    except Exception as e:
        print(f'다이소 카탈로그 로드 실패: {e}')

    # 이케아
    try:
        cur.execute('SELECT * FROM ikea_catalog')
        before = len(all_items)
        for c in cur.fetchall():
            keywords = extract_keywords(c['name'])
            all_items.append({
                'product_no': c['product_no'],
                'name': c['name'],
                'price': c['price'],
                'image_url': c['image_url'],
                'product_url': c['product_url'],
                'category': c['category'],
                'store_key': 'ikea',
                'store_name': '이케아',
                'keywords': keywords
            })
        print(f'이케아 카탈로그: {len(all_items) - before}개')
    except Exception as e:
        print(f'이케아 카탈로그 로드 실패: {e}')

    # 코스트코
    try:
        cur.execute('SELECT * FROM costco_catalog')
        before = len(all_items)
        for c in cur.fetchall():
            keywords = extract_keywords(c['name'])
            all_items.append({
                'product_no': c['product_no'],
                'name': c['name'],
                'price': c['price'],
                'image_url': c['image_url'],
                'product_url': c['product_url'],
                'category': c['category'],
                'store_key': 'costco',
                'store_name': '코스트코',
                'keywords': keywords
            })
        print(f'코스트코 카탈로그: {len(all_items) - before}개')
    except Exception as e:
        print(f'코스트코 카탈로그 로드 실패: {e}')

    return all_items


def run_smart_extraction():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 기존 부정확한 상품 초기화
    cur.execute('DELETE FROM products WHERE is_approved = 1 AND reason IS NULL')
    deleted = cur.rowcount
    print(f'기존 자동 추출 상품 삭제: {deleted}개')

    # 모든 스토어 카탈로그 로드
    catalog_items = load_all_catalogs(cur)
    print(f'전체 카탈로그: {len(catalog_items)}개')

    # 모든 영상 조회
    cur.execute('''
        SELECT * FROM videos
        WHERE (transcript IS NOT NULL AND transcript != '')
           OR (description IS NOT NULL AND description != '')
    ''')
    videos = cur.fetchall()
    print(f'분석 대상 영상: {len(videos)}개')

    new_products = []

    for video in videos:
        transcript = video['transcript'] or ''
        description = video['description'] or ''
        title = video['title'] or ''

        combined_text = f"{title}\n{description}\n{transcript}"

        # 1. 설명란에서 상품 목록 추출
        desc_products = extract_from_description(description)

        # 2. 카탈로그 매칭
        for item in catalog_items:
            if not item['keywords']:
                continue

            # 키워드 매칭
            matched_keywords = [kw for kw in item['keywords'] if kw in combined_text.lower()]

            if len(matched_keywords) >= 2:
                # 추천 문맥 분석 (이유, 타임스탬프 포함)
                rec_result = extract_recommendation_context(combined_text, item['name'], item['keywords'])
                rec_score = rec_result['score']

                # 설명란 언급 보너스
                desc_bonus = 0.2 if any(kw in description.lower() for kw in matched_keywords) else 0

                # 제목 언급 보너스
                title_bonus = 0.3 if any(kw in title.lower() for kw in matched_keywords) else 0

                # 최종 점수
                match_score = len(matched_keywords) / len(item['keywords'])
                final_score = match_score * 0.4 + rec_score * 0.4 + desc_bonus + title_bonus

                # 0.5 이상이면 추천템으로 인정
                if final_score >= 0.5:
                    # 추천 이유 정리
                    quote = rec_result.get('quote', '')
                    if quote:
                        quote = quote[:300]  # 최대 300자

                    # 타임스탬프 정보
                    timestamp_sec = rec_result.get('timestamp_sec')
                    timestamp_text = rec_result.get('timestamp_text', '')

                    # 상세 이유 생성
                    positive_kws = rec_result.get('positive_keywords', [])
                    reason_parts = []
                    if positive_kws:
                        reason_parts.append(f"키워드: {', '.join(positive_kws[:3])}")
                    if timestamp_text:
                        reason_parts.append(f"등장: {timestamp_text}")
                    reason = ' | '.join(reason_parts) if reason_parts else f'매칭:{match_score:.0%}'

                    new_products.append({
                        'video_id': video['video_id'],
                        'name': item['name'],
                        'price': item['price'],
                        'category': item['category'],
                        'store_key': item['store_key'],
                        'store_name': item['store_name'],
                        'official_code': item['product_no'],
                        'official_name': item['name'],
                        'official_price': item['price'],
                        'official_image_url': item['image_url'],
                        'official_product_url': item['product_url'],
                        'channel_title': video['channel_title'],
                        'view_count': video['view_count'],
                        'score': final_score,
                        'reason': reason,
                        'recommendation_quote': quote,
                        'timestamp_sec': timestamp_sec,
                        'timestamp_text': timestamp_text,
                    })

    # 중복 제거 (같은 영상에서 같은 상품)
    seen = set()
    unique_products = []
    for p in new_products:
        key = (p['video_id'], p['name'])
        if key not in seen:
            seen.add(key)
            unique_products.append(p)

    print(f'\n검증된 추천템: {len(unique_products)}개')

    # DB 저장
    added = 0
    for p in unique_products:
        cur.execute('SELECT id FROM products WHERE video_id=? AND name=?',
                   (p['video_id'], p['name']))
        if cur.fetchone():
            continue

        cur.execute('''
            INSERT INTO products (video_id, name, price, category, store_key, store_name,
                official_code, official_name, official_price, official_image_url, official_product_url,
                is_matched, is_approved, source_view_count, reason, recommendation_quote,
                timestamp_sec, timestamp_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?, ?, datetime('now'))
        ''', (p['video_id'], p['name'], p['price'], p['category'], p['store_key'], p['store_name'],
              p['official_code'], p['official_name'], p['official_price'],
              p['official_image_url'], p['official_product_url'], p['view_count'], p['reason'],
              p.get('recommendation_quote'), p.get('timestamp_sec'), p.get('timestamp_text')))
        added += 1

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM products')
    total = cur.fetchone()[0]
    print(f'추가된 상품: {added}개')
    print(f'총 상품 수: {total}개')

    conn.close()
    return total


if __name__ == '__main__':
    run_smart_extraction()
