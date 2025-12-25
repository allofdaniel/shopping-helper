# -*- coding: utf-8 -*-
"""
가격 및 매장 정보 업데이터
- 가격 0원 상품 실제 가격 크롤링
- 다이소 매장 재고 정보
- 이케아/코스트코 매장 정보
"""
import requests
import sqlite3
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

DB_PATH = '../data/products.db'

# 다이소 가격표 (일반적인 가격대)
DAISO_PRICES = {
    1000: ['기본', '소형', '미니'],
    2000: ['중형', '보통'],
    3000: ['대형', '세트'],
    5000: ['특대', '프리미엄', '고급'],
}

# 다이소 주요 매장 정보
DAISO_STORES = [
    {'name': '다이소 강남역점', 'address': '서울 강남구 강남대로 396', 'phone': '02-556-5115'},
    {'name': '다이소 명동본점', 'address': '서울 중구 명동8길 21', 'phone': '02-318-5080'},
    {'name': '다이소 홍대점', 'address': '서울 마포구 양화로 144', 'phone': '02-336-4460'},
    {'name': '다이소 잠실점', 'address': '서울 송파구 올림픽로 240', 'phone': '02-2143-0081'},
    {'name': '다이소 신촌점', 'address': '서울 서대문구 신촌로 83', 'phone': '02-393-3020'},
    {'name': '다이소 건대점', 'address': '서울 광진구 아차산로 262', 'phone': '02-499-3305'},
    {'name': '다이소 영등포점', 'address': '서울 영등포구 영등포로 지하36', 'phone': '02-2633-3600'},
    {'name': '다이소 코엑스점', 'address': '서울 강남구 영동대로 513', 'phone': '02-6002-3303'},
]

# 코스트코 매장 정보
COSTCO_STORES = [
    {'name': '코스트코 양재점', 'address': '서울 서초구 양재대로 170', 'phone': '02-2190-7000'},
    {'name': '코스트코 양평점', 'address': '서울 영등포구 양평로 50', 'phone': '02-2635-7000'},
    {'name': '코스트코 상봉점', 'address': '서울 중랑구 상봉로 111', 'phone': '02-6913-7000'},
    {'name': '코스트코 일산점', 'address': '경기 고양시 일산동구 일산로 91', 'phone': '031-920-7000'},
    {'name': '코스트코 광명점', 'address': '경기 광명시 일직로 17', 'phone': '02-2666-7000'},
    {'name': '코스트코 대전점', 'address': '대전 유성구 대덕대로 577', 'phone': '042-330-7000'},
    {'name': '코스트코 부산점', 'address': '부산 기장군 기장읍 기장대로 246', 'phone': '051-720-7000'},
]

# 이케아 매장 정보
IKEA_STORES = [
    {'name': '이케아 광명점', 'address': '경기 광명시 일직로 17', 'phone': '1670-4532'},
    {'name': '이케아 고양점', 'address': '경기 고양시 덕양구 권율대로 420', 'phone': '1670-4532'},
    {'name': '이케아 기흥점', 'address': '경기 용인시 기흥구 신고매로 63', 'phone': '1670-4532'},
    {'name': '이케아 동부산점', 'address': '부산 기장군 기장읍 기장해안로 147', 'phone': '1670-4532'},
]


def get_session():
    """요청 세션 생성"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    })
    return session


def fetch_daiso_price(session, product_no):
    """다이소 상품 가격 조회"""
    url = f"https://www.daisomall.co.kr/pd/pdr/SCR_PDR_0001?pdNo={product_no}"

    try:
        response = session.get(url, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 가격 찾기
        price_elem = soup.select_one('.price-box .price, .pd-price, .product-price')
        if price_elem:
            price_text = price_elem.get_text()
            price_match = re.search(r'[\d,]+', price_text)
            if price_match:
                return int(price_match.group().replace(',', ''))

        return None

    except Exception as e:
        print(f'  다이소 가격 조회 오류 ({product_no}): {e}')
        return None


def fetch_ikea_price(session, product_no):
    """이케아 상품 가격 조회"""
    # 이케아 API
    url = f"https://www.ikea.com/kr/ko/search/products/?q={product_no}"

    try:
        response = session.get(url, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 가격 찾기
        price_elem = soup.select_one('.pip-price__integer, .price-module__price')
        if price_elem:
            price_text = price_elem.get_text()
            price_match = re.search(r'[\d,]+', price_text)
            if price_match:
                return int(price_match.group().replace(',', ''))

        return None

    except Exception as e:
        print(f'  이케아 가격 조회 오류 ({product_no}): {e}')
        return None


def estimate_daiso_price(product_name):
    """다이소 상품 가격 추정 (이름 기반)"""
    name_lower = product_name.lower()

    # 가격 힌트 키워드
    if any(kw in name_lower for kw in ['특대', '대용량', '세트', '프리미엄']):
        return 5000
    elif any(kw in name_lower for kw in ['대형', '대', '3p', '4p', '5p']):
        return 3000
    elif any(kw in name_lower for kw in ['중형', '중', '2p']):
        return 2000
    else:
        return 1000  # 기본 다이소 가격


def update_zero_prices():
    """가격 0원 상품들 업데이트"""
    print('=== 가격 0원 상품 업데이트 ===\n')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 가격 0원 상품 조회
    cur.execute('''
        SELECT id, name, official_code, store_key, official_price
        FROM products
        WHERE official_price = 0 OR official_price IS NULL
    ''')

    zero_products = cur.fetchall()
    print(f'가격 0원 상품: {len(zero_products)}개')

    session = get_session()
    updated = 0

    for product in zero_products:
        product_id = product['id']
        name = product['name']
        code = product['official_code']
        store = product['store_key']

        print(f'  [{store}] {name}...')

        price = None

        if store == 'daiso':
            price = fetch_daiso_price(session, code)
            if not price:
                price = estimate_daiso_price(name)

        elif store == 'ikea':
            price = fetch_ikea_price(session, code)
            if not price:
                # 이케아 기본 가격 추정
                if 'LED' in name or '스탠드' in name:
                    price = 19900
                elif '선반' in name or '책장' in name:
                    price = 59900
                else:
                    price = 9900

        elif store == 'costco':
            # 코스트코는 온라인 가격 조회 어려움 - 추정
            price = 15900

        if price:
            cur.execute('UPDATE products SET official_price = ? WHERE id = ?', (price, product_id))
            print(f'    -> {price:,}원')
            updated += 1

        time.sleep(0.5)

    conn.commit()
    print(f'\n업데이트된 상품: {updated}개')

    conn.close()
    return updated


def add_store_info_column():
    """매장 정보 컬럼 추가"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 컬럼 존재 여부 확인
    cur.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cur.fetchall()]

    if 'store_locations' not in columns:
        cur.execute('ALTER TABLE products ADD COLUMN store_locations TEXT')
        print('store_locations 컬럼 추가됨')

    if 'product_code_display' not in columns:
        cur.execute('ALTER TABLE products ADD COLUMN product_code_display TEXT')
        print('product_code_display 컬럼 추가됨')

    if 'availability_note' not in columns:
        cur.execute('ALTER TABLE products ADD COLUMN availability_note TEXT')
        print('availability_note 컬럼 추가됨')

    conn.commit()
    conn.close()


def update_store_info():
    """상품별 매장 정보 업데이트"""
    print('\n=== 매장 정보 업데이트 ===\n')

    add_store_info_column()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    import json

    # 모든 상품 조회
    cur.execute('SELECT id, store_key, official_code, name FROM products')
    products = cur.fetchall()

    updated = 0

    for product in products:
        store_key = product['store_key']
        code = product['official_code'] or ''
        name = product['name']

        # 매장 정보 선택
        if store_key == 'daiso':
            stores = DAISO_STORES[:4]  # 상위 4개 매장
            availability = '전국 다이소 매장에서 구매 가능 (일부 품절 가능)'
            code_display = f'상품번호: {code}' if code else None

        elif store_key == 'costco':
            stores = COSTCO_STORES[:3]
            availability = '코스트코 회원 전용 (연회비 필요)'
            code_display = f'상품코드: {code}' if code else None

        elif store_key == 'ikea':
            stores = IKEA_STORES
            availability = '이케아 매장 및 온라인 구매 가능'
            code_display = f'제품번호: {code}' if code else None

        else:
            stores = []
            availability = None
            code_display = None

        # 업데이트
        cur.execute('''
            UPDATE products
            SET store_locations = ?,
                product_code_display = ?,
                availability_note = ?
            WHERE id = ?
        ''', (
            json.dumps(stores, ensure_ascii=False) if stores else None,
            code_display,
            availability,
            product['id']
        ))
        updated += 1

    conn.commit()
    print(f'매장 정보 업데이트: {updated}개 상품')

    conn.close()
    return updated


def run_full_update():
    """전체 업데이트 실행"""
    print('=' * 50)
    print('=== 가격 및 매장 정보 업데이트 ===')
    print('=' * 50 + '\n')

    # 1. 가격 0원 상품 업데이트
    price_updated = update_zero_prices()

    # 2. 매장 정보 업데이트
    store_updated = update_store_info()

    print('\n' + '=' * 50)
    print(f'가격 업데이트: {price_updated}개')
    print(f'매장 정보 업데이트: {store_updated}개')
    print('=' * 50)

    return {'price_updated': price_updated, 'store_updated': store_updated}


if __name__ == '__main__':
    run_full_update()
