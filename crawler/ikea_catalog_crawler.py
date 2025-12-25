# -*- coding: utf-8 -*-
"""
이케아 상품 카탈로그 크롤러
이케아 인기 상품 수집
"""
import requests
import sqlite3
import time
from datetime import datetime

DB_PATH = '../data/products.db'

# 이케아 인기 상품 목록 (유튜브에서 자주 추천되는 상품들)
POPULAR_IKEA_PRODUCTS = [
    # 수납/정리
    {'product_no': 'IKEA001', 'name': 'KALLAX 칼락스 선반유닛', 'price': 69900, 'category': '수납', 'image_url': 'https://www.ikea.com/kr/ko/images/products/kallax-shelving-unit-white__0644757_pe702939_s5.jpg'},
    {'product_no': 'IKEA002', 'name': 'BILLY 빌리 책장', 'price': 59900, 'category': '수납', 'image_url': 'https://www.ikea.com/kr/ko/images/products/billy-bookcase-white__0625599_pe692385_s5.jpg'},
    {'product_no': 'IKEA003', 'name': 'ALEX 알렉스 서랍장', 'price': 99900, 'category': '수납', 'image_url': ''},
    {'product_no': 'IKEA004', 'name': 'SKUBB 스쿱 수납박스 6개', 'price': 12900, 'category': '수납', 'image_url': ''},
    {'product_no': 'IKEA005', 'name': 'DRONA 드뢰나 박스', 'price': 4900, 'category': '수납', 'image_url': ''},
    {'product_no': 'IKEA006', 'name': 'HEMNES 헴네스 서랍장', 'price': 199000, 'category': '수납', 'image_url': ''},
    {'product_no': 'IKEA007', 'name': 'MALM 말름 서랍장', 'price': 149000, 'category': '수납', 'image_url': ''},

    # 주방용품
    {'product_no': 'IKEA010', 'name': 'VARIERA 바리에라 조리대정리대', 'price': 5900, 'category': '주방', 'image_url': ''},
    {'product_no': 'IKEA011', 'name': 'IKEA 365+ 유리 밀폐용기', 'price': 3900, 'category': '주방', 'image_url': ''},
    {'product_no': 'IKEA012', 'name': 'KORKEN 코르켄 유리병', 'price': 2900, 'category': '주방', 'image_url': ''},
    {'product_no': 'IKEA013', 'name': 'OFTAST 오프타스트 접시세트', 'price': 9900, 'category': '주방', 'image_url': ''},
    {'product_no': 'IKEA014', 'name': 'DRAGON 드라곤 수저세트', 'price': 14900, 'category': '주방', 'image_url': ''},
    {'product_no': 'IKEA015', 'name': 'VARDAGEN 바르다겐 프라이팬', 'price': 24900, 'category': '주방', 'image_url': ''},
    {'product_no': 'IKEA016', 'name': 'RINNIG 린니그 식기건조대', 'price': 9900, 'category': '주방', 'image_url': ''},

    # 조명
    {'product_no': 'IKEA020', 'name': 'TERTIAL 테르티알 스탠드', 'price': 12900, 'category': '조명', 'image_url': ''},
    {'product_no': 'IKEA021', 'name': 'FADO 파도 테이블스탠드', 'price': 19900, 'category': '조명', 'image_url': ''},
    {'product_no': 'IKEA022', 'name': 'NYMANE 뉘모네 플로어스탠드', 'price': 39900, 'category': '조명', 'image_url': ''},
    {'product_no': 'IKEA023', 'name': 'LEDARE LED전구', 'price': 4900, 'category': '조명', 'image_url': ''},
    {'product_no': 'IKEA024', 'name': 'RANARP 라나르프 스탠드', 'price': 34900, 'category': '조명', 'image_url': ''},

    # 가구
    {'product_no': 'IKEA030', 'name': 'LACK 라크 사이드테이블', 'price': 9900, 'category': '가구', 'image_url': ''},
    {'product_no': 'IKEA031', 'name': 'POANG 포엥 암체어', 'price': 99900, 'category': '가구', 'image_url': ''},
    {'product_no': 'IKEA032', 'name': 'MALM 말름 침대프레임', 'price': 199000, 'category': '가구', 'image_url': ''},
    {'product_no': 'IKEA033', 'name': 'TARVA 타르바 침대프레임', 'price': 129000, 'category': '가구', 'image_url': ''},
    {'product_no': 'IKEA034', 'name': 'STEFAN 스테판 의자', 'price': 29900, 'category': '가구', 'image_url': ''},
    {'product_no': 'IKEA035', 'name': 'LERHAMN 레르함 테이블', 'price': 79900, 'category': '가구', 'image_url': ''},

    # 욕실용품
    {'product_no': 'IKEA040', 'name': 'GODMORGON 고드모르곤 욕실수납장', 'price': 79900, 'category': '욕실', 'image_url': ''},
    {'product_no': 'IKEA041', 'name': 'TOFTBO 토프트보 욕실매트', 'price': 14900, 'category': '욕실', 'image_url': ''},
    {'product_no': 'IKEA042', 'name': 'VOXNAN 복스난 칫솔꽂이', 'price': 6900, 'category': '욕실', 'image_url': ''},
    {'product_no': 'IKEA043', 'name': 'SAXBORGA 삭스보르가 거울수납장', 'price': 19900, 'category': '욕실', 'image_url': ''},

    # 인테리어 소품
    {'product_no': 'IKEA050', 'name': 'FEJKA 페이카 조화', 'price': 4900, 'category': '인테리어', 'image_url': ''},
    {'product_no': 'IKEA051', 'name': 'RIBBA 리바 액자', 'price': 9900, 'category': '인테리어', 'image_url': ''},
    {'product_no': 'IKEA052', 'name': 'SMYCKA 스뮈카 조화가지', 'price': 3900, 'category': '인테리어', 'image_url': ''},
    {'product_no': 'IKEA053', 'name': 'BILD 빌드 포스터', 'price': 5900, 'category': '인테리어', 'image_url': ''},
    {'product_no': 'IKEA054', 'name': 'KNODD 크노드 휴지통', 'price': 9900, 'category': '인테리어', 'image_url': ''},
    {'product_no': 'IKEA055', 'name': 'SAMLA 삼라 수납박스', 'price': 6900, 'category': '수납', 'image_url': ''},

    # 침구
    {'product_no': 'IKEA060', 'name': 'DVALA 드발라 침대시트', 'price': 9900, 'category': '침구', 'image_url': ''},
    {'product_no': 'IKEA061', 'name': 'BERGPALM 베리팜 이불커버세트', 'price': 24900, 'category': '침구', 'image_url': ''},
    {'product_no': 'IKEA062', 'name': 'GRUSBLAD 그루스블라드 이불', 'price': 19900, 'category': '침구', 'image_url': ''},
    {'product_no': 'IKEA063', 'name': 'JORDROKA 요르드로카 베개', 'price': 7900, 'category': '침구', 'image_url': ''},

    # 수건/텍스타일
    {'product_no': 'IKEA070', 'name': 'VAGSJON 벡셴 수건', 'price': 4900, 'category': '텍스타일', 'image_url': ''},
    {'product_no': 'IKEA071', 'name': 'SALVIKEN 살비켄 수건세트', 'price': 9900, 'category': '텍스타일', 'image_url': ''},
    {'product_no': 'IKEA072', 'name': 'GRACIOSA 그라시오사 식탁매트', 'price': 3900, 'category': '텍스타일', 'image_url': ''},
]


def create_ikea_catalog_table():
    """이케아 카탈로그 테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS ikea_catalog (
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


def run_ikea_catalog():
    """이케아 카탈로그 저장"""
    print('=== 이케아 카탈로그 수집 ===\n')

    create_ikea_catalog_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 기존 수 확인
    cur.execute('SELECT COUNT(*) FROM ikea_catalog')
    before = cur.fetchone()[0]
    print(f'기존 카탈로그: {before}개')

    added = 0
    updated = 0

    for product in POPULAR_IKEA_PRODUCTS:
        # 이케아 검색 URL
        search_name = product['name'].split()[0]  # 첫 단어 (영문명)
        product_url = f"https://www.ikea.com/kr/ko/search/?q={search_name}"

        cur.execute('SELECT id FROM ikea_catalog WHERE product_no = ?', (product['product_no'],))
        existing = cur.fetchone()

        if existing:
            cur.execute('''
                UPDATE ikea_catalog
                SET name=?, price=?, category=?, product_url=?, image_url=?, updated_at=datetime('now')
                WHERE product_no=?
            ''', (product['name'], product['price'], product['category'], product_url, product.get('image_url', ''), product['product_no']))
            updated += 1
        else:
            cur.execute('''
                INSERT INTO ikea_catalog (product_no, name, price, category, product_url, image_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (product['product_no'], product['name'], product['price'], product['category'], product_url, product.get('image_url', '')))
            added += 1

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM ikea_catalog')
    after = cur.fetchone()[0]

    print(f'신규 추가: {added}개')
    print(f'업데이트: {updated}개')
    print(f'최종 카탈로그: {after}개')

    conn.close()
    return after


if __name__ == '__main__':
    run_ikea_catalog()
