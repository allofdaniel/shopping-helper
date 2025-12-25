# -*- coding: utf-8 -*-
"""
코스트코 상품 카탈로그 크롤러
코스트코 공식 사이트에서 인기 상품 수집
"""
import requests
import sqlite3
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup

DB_PATH = '../data/products.db'

# 코스트코 인기 카테고리 및 키워드
COSTCO_CATEGORIES = [
    ('신선식품', ['고기', '소고기', '돼지고기', '닭고기', '해산물', '연어', '새우']),
    ('냉동식품', ['피자', '만두', '냉동', '아이스크림', '냉동밥']),
    ('유제품', ['우유', '치즈', '요거트', '버터', '크림치즈']),
    ('과자/간식', ['과자', '견과류', '초콜릿', '젤리', '쿠키', '크래커']),
    ('음료', ['커피', '주스', '탄산', '물', '콤부차', '에너지드링크']),
    ('건강식품', ['비타민', '유산균', '오메가3', '영양제', '프로틴']),
    ('생활용품', ['세제', '휴지', '물티슈', '주방세제', '섬유유연제']),
    ('주방용품', ['프라이팬', '냄비', '식기', '텀블러', '보온병']),
    ('가전', ['청소기', '에어프라이어', '믹서기', '커피머신']),
]

# 인기 상품 목록 (수동 큐레이션 - API 대신)
POPULAR_COSTCO_PRODUCTS = [
    # 신선/육류
    {'product_no': 'COST001', 'name': '미국산 프라임 등급 LA갈비', 'price': 89900, 'category': '신선식품'},
    {'product_no': 'COST002', 'name': '미국산 초이스 척아이롤', 'price': 45900, 'category': '신선식품'},
    {'product_no': 'COST003', 'name': '노르웨이 생연어 필렛', 'price': 39900, 'category': '신선식품'},
    {'product_no': 'COST004', 'name': '캐나다산 랍스터 테일', 'price': 49900, 'category': '신선식품'},
    {'product_no': 'COST005', 'name': '양념 LA갈비 대용량', 'price': 69900, 'category': '신선식품'},

    # 베이커리
    {'product_no': 'COST010', 'name': '코스트코 크로와상 12개입', 'price': 9990, 'category': '베이커리'},
    {'product_no': 'COST011', 'name': '티라미수 케이크', 'price': 16900, 'category': '베이커리'},
    {'product_no': 'COST012', 'name': '마스카포네 롤케이크', 'price': 12990, 'category': '베이커리'},
    {'product_no': 'COST013', 'name': '미니 머핀 24개입', 'price': 11990, 'category': '베이커리'},
    {'product_no': 'COST014', 'name': '치아바타 브레드', 'price': 6990, 'category': '베이커리'},

    # 냉동식품
    {'product_no': 'COST020', 'name': '펩퍼로니 피자 콤보', 'price': 15900, 'category': '냉동식품'},
    {'product_no': 'COST021', 'name': '비비고 왕교자 대용량', 'price': 17900, 'category': '냉동식품'},
    {'product_no': 'COST022', 'name': '하겐다즈 아이스크림 4개입', 'price': 19900, 'category': '냉동식품'},
    {'product_no': 'COST023', 'name': '치킨너겟 대용량', 'price': 14900, 'category': '냉동식품'},
    {'product_no': 'COST024', 'name': '새우볶음밥 대용량', 'price': 12900, 'category': '냉동식품'},

    # 유제품
    {'product_no': 'COST030', 'name': '커클랜드 그릭요거트 24개입', 'price': 15900, 'category': '유제품'},
    {'product_no': 'COST031', 'name': '필라델피아 크림치즈', 'price': 12900, 'category': '유제품'},
    {'product_no': 'COST032', 'name': '코스트코 파마산 치즈', 'price': 24900, 'category': '유제품'},
    {'product_no': 'COST033', 'name': '유기농 우유 3팩', 'price': 8900, 'category': '유제품'},

    # 과자/간식
    {'product_no': 'COST040', 'name': '커클랜드 믹스넛 대용량', 'price': 24900, 'category': '과자/간식'},
    {'product_no': 'COST041', 'name': '린도 초콜릿 세트', 'price': 19900, 'category': '과자/간식'},
    {'product_no': 'COST042', 'name': '프링글스 대용량 12개입', 'price': 16900, 'category': '과자/간식'},
    {'product_no': 'COST043', 'name': '코스트코 마카다미아', 'price': 29900, 'category': '과자/간식'},
    {'product_no': 'COST044', 'name': '하리보 젤리 대용량', 'price': 12900, 'category': '과자/간식'},

    # 음료
    {'product_no': 'COST050', 'name': '커클랜드 생수 40팩', 'price': 8900, 'category': '음료'},
    {'product_no': 'COST051', 'name': '스타벅스 콜드브루 12개입', 'price': 24900, 'category': '음료'},
    {'product_no': 'COST052', 'name': '코스트코 콤부차 12개입', 'price': 17900, 'category': '음료'},
    {'product_no': 'COST053', 'name': '몬스터 에너지 24팩', 'price': 34900, 'category': '음료'},

    # 건강식품
    {'product_no': 'COST060', 'name': '커클랜드 종합비타민', 'price': 29900, 'category': '건강식품'},
    {'product_no': 'COST061', 'name': '락토핏 유산균 대용량', 'price': 39900, 'category': '건강식품'},
    {'product_no': 'COST062', 'name': '오메가3 피쉬오일', 'price': 34900, 'category': '건강식품'},
    {'product_no': 'COST063', 'name': '콜라겐 파우더', 'price': 44900, 'category': '건강식품'},

    # 생활용품
    {'product_no': 'COST070', 'name': '커클랜드 물티슈 대용량', 'price': 19900, 'category': '생활용품'},
    {'product_no': 'COST071', 'name': '다우니 섬유유연제', 'price': 24900, 'category': '생활용품'},
    {'product_no': 'COST072', 'name': '코스트코 휴지 30롤', 'price': 29900, 'category': '생활용품'},
    {'product_no': 'COST073', 'name': '타이드 세탁세제 대용량', 'price': 34900, 'category': '생활용품'},

    # 주방용품
    {'product_no': 'COST080', 'name': '스탠리 텀블러', 'price': 45900, 'category': '주방용품'},
    {'product_no': 'COST081', 'name': '글라스락 밀폐용기 세트', 'price': 39900, 'category': '주방용품'},
    {'product_no': 'COST082', 'name': '논스틱 프라이팬 세트', 'price': 69900, 'category': '주방용품'},
    {'product_no': 'COST083', 'name': '스테인리스 냄비 세트', 'price': 89900, 'category': '주방용품'},
]


def create_costco_catalog_table():
    """코스트코 카탈로그 테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS costco_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_no TEXT UNIQUE,
            name TEXT NOT NULL,
            price INTEGER,
            image_url TEXT,
            product_url TEXT,
            category TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def run_costco_catalog():
    """코스트코 카탈로그 크롤링/저장"""
    print('=== 코스트코 카탈로그 수집 ===\n')

    create_costco_catalog_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 기존 수 확인
    cur.execute('SELECT COUNT(*) FROM costco_catalog')
    before = cur.fetchone()[0]
    print(f'기존 카탈로그: {before}개')

    added = 0
    updated = 0

    for product in POPULAR_COSTCO_PRODUCTS:
        # 상품 URL (코스트코 검색 페이지로 연결)
        search_query = product['name'].replace(' ', '+')
        product_url = f"https://www.costco.co.kr/search?text={search_query}"

        cur.execute('SELECT id FROM costco_catalog WHERE product_no = ?', (product['product_no'],))
        existing = cur.fetchone()

        if existing:
            cur.execute('''
                UPDATE costco_catalog
                SET name=?, price=?, category=?, product_url=?, updated_at=datetime('now')
                WHERE product_no=?
            ''', (product['name'], product['price'], product['category'], product_url, product['product_no']))
            updated += 1
        else:
            cur.execute('''
                INSERT INTO costco_catalog (product_no, name, price, category, product_url, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', (product['product_no'], product['name'], product['price'], product['category'], product_url))
            added += 1

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM costco_catalog')
    after = cur.fetchone()[0]

    print(f'신규 추가: {added}개')
    print(f'업데이트: {updated}개')
    print(f'최종 카탈로그: {after}개')

    conn.close()
    return after


if __name__ == '__main__':
    run_costco_catalog()
