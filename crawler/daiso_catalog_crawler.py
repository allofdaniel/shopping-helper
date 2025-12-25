# -*- coding: utf-8 -*-
"""
다이소몰 전체 카탈로그 크롤러
모든 카테고리에서 상품 수집
"""
import requests
import sqlite3
import time
from datetime import datetime

DB_PATH = '../data/products.db'

# 다이소몰 카테고리 코드
CATEGORIES = [
    # 생활용품
    ('10', '생활용품'),
    ('1001', '수납/정리'),
    ('1002', '욕실용품'),
    ('1003', '세탁용품'),
    ('1004', '청소용품'),
    # 주방
    ('20', '주방용품'),
    ('2001', '주방잡화'),
    ('2002', '식기/컵'),
    ('2003', '조리도구'),
    ('2004', '밀폐/보관'),
    # 뷰티
    ('30', '뷰티/헬스'),
    ('3001', '화장소품'),
    ('3002', '네일아트'),
    ('3003', '헤어용품'),
    ('3004', '바디케어'),
    # 문구
    ('40', '문구/팬시'),
    ('4001', '필기구'),
    ('4002', '노트/메모'),
    ('4003', '사무용품'),
    # 식품
    ('50', '식품'),
    ('5001', '과자/스낵'),
    ('5002', '음료'),
    ('5003', '가공식품'),
    # 인테리어
    ('60', '인테리어'),
    ('6001', '홈데코'),
    ('6002', '조명'),
    ('6003', 'DIY'),
    # 시즌
    ('70', '시즌상품'),
    # 패션
    ('80', '패션잡화'),
    ('8001', '가방/파우치'),
    ('8002', '양말/스타킹'),
    # 전자
    ('90', '디지털/전자'),
    ('9001', '케이블/충전'),
    ('9002', '이어폰/스피커'),
]


def crawl_category(session, category_code, category_name, page=1, per_page=100):
    """카테고리별 상품 크롤링"""
    url = "https://www.daisomall.co.kr/dsm/category/CategoryList"

    params = {
        'lctgCd': category_code[:2],  # 대분류
        'mctgCd': category_code if len(category_code) > 2 else '',  # 중분류
        'sctgCd': '',
        'pageNum': page,
        'cntPerPage': per_page,
        'sortType': '01',  # 인기순
    }

    try:
        response = session.get(url, params=params, timeout=15)
        if response.status_code != 200:
            return []

        data = response.json()
        products = []

        # API 응답 구조에 따라 파싱
        result = data.get('result', {})
        items = result.get('pdList', []) or result.get('list', []) or []

        for item in items:
            product = {
                'product_no': item.get('pdNo', ''),
                'name': item.get('pdNm', '') or item.get('exhPdNm', ''),
                'price': int(item.get('pdPrc', 0) or 0),
                'image_url': '',
                'product_url': f"https://www.daisomall.co.kr/pd/pdr/SCR_PDR_0001?pdNo={item.get('pdNo', '')}",
                'category': category_name,
            }

            # 이미지 URL
            img = item.get('pdImgUrl') or item.get('mainImgPath') or item.get('imgPath', '')
            if img:
                if not img.startswith('http'):
                    img = f"https://www.daisomall.co.kr{img}"
                product['image_url'] = img

            if product['product_no'] and product['name']:
                products.append(product)

        return products

    except Exception as e:
        print(f"  에러 ({category_name}): {e}")
        return []


def crawl_search(session, keyword, page=1, per_page=100):
    """키워드 검색으로 상품 크롤링"""
    url = "https://www.daisomall.co.kr/ssn/search/SearchGoods"

    params = {
        'searchTerm': keyword,
        'pageNum': page,
        'cntPerPage': per_page,
    }

    try:
        response = session.get(url, params=params, timeout=15)
        if response.status_code != 200:
            return []

        data = response.json()
        products = []

        result_set = data.get('resultSet', {})
        results = result_set.get('result', [])

        if len(results) >= 2:
            product_result = results[1]
            items = product_result.get('resultDocuments', [])

            for item in items:
                product = {
                    'product_no': item.get('pdNo', ''),
                    'name': item.get('pdNm', '') or item.get('exhPdNm', ''),
                    'price': int(item.get('pdPrc', 0) or 0),
                    'image_url': '',
                    'product_url': f"https://www.daisomall.co.kr/pd/pdr/SCR_PDR_0001?pdNo={item.get('pdNo', '')}",
                    'category': keyword,
                }

                img = item.get('pdImgUrl') or item.get('mainImgPath', '')
                if img:
                    if not img.startswith('http'):
                        img = f"https://www.daisomall.co.kr{img}"
                    product['image_url'] = img

                if product['product_no'] and product['name']:
                    products.append(product)

        return products

    except Exception as e:
        print(f"  검색 에러 ({keyword}): {e}")
        return []


def run_catalog_crawl():
    """전체 카탈로그 크롤링"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'ko-KR,ko;q=0.9',
    })

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 기존 카탈로그 수
    cur.execute('SELECT COUNT(*) FROM daiso_catalog')
    before = cur.fetchone()[0]
    print(f'기존 카탈로그: {before}개')

    all_products = []

    # 1. 카테고리별 크롤링
    print('\n=== 카테고리별 크롤링 ===')
    for code, name in CATEGORIES:
        print(f'  {name}...')
        products = crawl_category(session, code, name)
        all_products.extend(products)
        print(f'    -> {len(products)}개')
        time.sleep(0.3)

    # 2. 인기 키워드 검색
    print('\n=== 키워드 검색 ===')
    search_keywords = [
        '꿀템', '베스트', '인기', '신상', '추천',
        '정리함', '수납', '밀폐용기', '주방', '화장품',
        '청소', '욕실', '세탁', '문구', '팬시',
        '과자', '음료', '스낵', '인테리어', '조명',
        '가방', '파우치', '양말', '케이블', '충전기',
        '실리콘', '스테인리스', '플라스틱', '유리', '나무',
    ]

    for keyword in search_keywords:
        print(f'  "{keyword}" 검색...')
        products = crawl_search(session, keyword)
        all_products.extend(products)
        print(f'    -> {len(products)}개')
        time.sleep(0.3)

    # 중복 제거
    seen = set()
    unique = []
    for p in all_products:
        if p['product_no'] not in seen:
            seen.add(p['product_no'])
            unique.append(p)

    print(f'\n총 수집: {len(all_products)}개 -> 중복제거: {len(unique)}개')

    # DB 저장
    added = 0
    for p in unique:
        cur.execute('SELECT id FROM daiso_catalog WHERE product_no = ?', (p['product_no'],))
        if cur.fetchone():
            # 업데이트
            cur.execute('''
                UPDATE daiso_catalog SET name=?, price=?, image_url=?, category=?, updated_at=datetime('now')
                WHERE product_no=?
            ''', (p['name'], p['price'], p['image_url'], p['category'], p['product_no']))
        else:
            # 신규
            cur.execute('''
                INSERT INTO daiso_catalog (product_no, name, price, image_url, product_url, category, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (p['product_no'], p['name'], p['price'], p['image_url'], p['product_url'], p['category']))
            added += 1

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM daiso_catalog')
    after = cur.fetchone()[0]
    print(f'\n신규 추가: {added}개')
    print(f'최종 카탈로그: {after}개')

    conn.close()
    return after


if __name__ == '__main__':
    run_catalog_crawl()
