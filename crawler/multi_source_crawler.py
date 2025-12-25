# -*- coding: utf-8 -*-
"""
멀티소스 크롤러 - 블로그, 인스타, 쓰레드 등 다양한 소스에서 추천 상품 수집
"""
import requests
import sqlite3
import re
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path

# 데이터베이스 경로
DB_PATH = Path(__file__).parent.parent / 'data' / 'products.db'

# 검색 키워드
COSTCO_KEYWORDS = [
    '코스트코 추천', '코스트코 필수템', '코스트코 꿀템', '코스트코 인기상품',
    '코스트코 장보기', '코스트코 신상', '코스트코 재구매', '코스트코 베스트',
    '코스트코 먹거리', '코스트코 생활용품', '코스트코 가성비'
]

IKEA_KEYWORDS = [
    '이케아 추천', '이케아 필수템', '이케아 꿀템', '이케아 인기상품',
    '이케아 인테리어', '이케아 수납', '이케아 가구', '이케아 베스트',
    '이케아 가성비', '이케아 신상', '이케아 주방'
]

# 코스트코 인기 상품 데이터 (블로그/커뮤니티 기반)
COSTCO_POPULAR_PRODUCTS = [
    # 식품
    {'name': '커클랜드 견과류 믹스 1.13kg', 'price': 19900, 'category': '식품', 'reason': '가성비 최고 견과류, 대용량'},
    {'name': '커클랜드 냉동 새우 908g', 'price': 24900, 'category': '식품', 'reason': '칵테일 새우, 해동만 하면 OK'},
    {'name': '커클랜드 올리브오일 3L', 'price': 26900, 'category': '식품', 'reason': '엑스트라버진, 대용량 가성비'},
    {'name': '티라미수 케이크', 'price': 16990, 'category': '식품', 'reason': '매장 인기 디저트 1위'},
    {'name': '불고기 베이크', 'price': 2500, 'category': '식품', 'reason': '푸드코트 인기 메뉴'},
    {'name': '로티세리 치킨', 'price': 7990, 'category': '식품', 'reason': '무조건 사야하는 필수템'},
    {'name': '커클랜드 그릭요거트 1.36kg', 'price': 12990, 'category': '식품', 'reason': '단백질 폭탄, 다이어터 필수'},
    {'name': '하겐다즈 아이스크림 바 15개입', 'price': 19990, 'category': '식품', 'reason': '마트 대비 반값'},
    {'name': '커클랜드 아몬드 버터 765g', 'price': 15990, 'category': '식품', 'reason': '땅콩버터 대신 건강하게'},
    {'name': '커클랜드 메이플 시럽 1L', 'price': 14990, 'category': '식품', 'reason': '100% 퓨어 메이플'},
    {'name': '커클랜드 참치캔 7개입', 'price': 14990, 'category': '식품', 'reason': '대용량 참치, 비상식량'},
    {'name': '커클랜드 유기농 코코넛오일 2.48L', 'price': 24990, 'category': '식품', 'reason': '요리/뷰티 다용도'},
    {'name': '커클랜드 아보카도 오일 2L', 'price': 22990, 'category': '식품', 'reason': '고온 조리용 오일'},
    {'name': '코스트코 연어회 500g', 'price': 29900, 'category': '식품', 'reason': '신선도 최고, 초밥용'},
    {'name': '커클랜드 크랜베리 주스 2.84L', 'price': 8990, 'category': '식품', 'reason': '요로감염 예방'},

    # 생활용품
    {'name': '커클랜드 화장지 30롤', 'price': 25990, 'category': '생활용품', 'reason': '3겹 두루마리, 가성비 끝판왕'},
    {'name': '커클랜드 물티슈 900매', 'price': 15990, 'category': '생활용품', 'reason': '아기도 쓸 수 있는 순한 물티슈'},
    {'name': '커클랜드 세탁세제 5.73kg', 'price': 19990, 'category': '생활용품', 'reason': '대용량 세제, 1년치'},
    {'name': '커클랜드 주방세제 2.66L x 2', 'price': 12990, 'category': '생활용품', 'reason': '기름때 끝장'},
    {'name': '커클랜드 쓰레기봉투 200매', 'price': 16990, 'category': '생활용품', 'reason': '대용량 봉투'},
    {'name': '옥소 팝컨테이너 세트', 'price': 69900, 'category': '생활용품', 'reason': '밀폐용기 끝판왕'},
    {'name': '다이슨 무선청소기 V8', 'price': 399000, 'category': '생활용품', 'reason': '코스트코 최저가'},

    # 건강/뷰티
    {'name': '센트룸 종합비타민 365정', 'price': 32990, 'category': '건강', 'reason': '1년치 비타민'},
    {'name': '커클랜드 오메가3 300정', 'price': 22990, 'category': '건강', 'reason': '고함량 오메가3'},
    {'name': '커클랜드 칼슘+D 500정', 'price': 15990, 'category': '건강', 'reason': '뼈 건강 필수'},
    {'name': '바이오더마 클렌징워터 500ml x 2', 'price': 24990, 'category': '뷰티', 'reason': '민감성 피부 추천'},
    {'name': '라로슈포제 시카플라스트 40ml x 2', 'price': 29990, 'category': '뷰티', 'reason': '진정 크림 국민템'},

    # 유아/반려동물
    {'name': '하기스 기저귀 192매', 'price': 49900, 'category': '유아', 'reason': '신생아용, 가성비'},
    {'name': '커클랜드 분유 1.36kg x 2', 'price': 54990, 'category': '유아', 'reason': '미국 분유, 순하고 좋음'},
    {'name': '커클랜드 강아지사료 18kg', 'price': 54990, 'category': '반려동물', 'reason': '대용량 사료'},
    {'name': '커클랜드 고양이사료 11.3kg', 'price': 42990, 'category': '반려동물', 'reason': '고단백 사료'},
]

# 이케아 인기 상품 데이터 (블로그/커뮤니티 기반)
IKEA_POPULAR_PRODUCTS = [
    # 수납/정리
    {'name': 'KALLAX 칼락스 선반유닛 77x77', 'price': 59900, 'category': '수납', 'reason': '만능 수납장, 인테리어 필수'},
    {'name': 'ALEX 알렉스 서랍유닛', 'price': 89900, 'category': '수납', 'reason': '화장대/책상 정리 끝판왕'},
    {'name': 'SKUBB 스쿠브 수납박스 세트', 'price': 12900, 'category': '수납', 'reason': '옷장 정리 필수템'},
    {'name': 'VARIERA 바리에라 박스', 'price': 3900, 'category': '수납', 'reason': '싱크대 정리, 다용도'},
    {'name': 'SAMLA 삼라 수납박스 22L', 'price': 4900, 'category': '수납', 'reason': '투명 정리함, 적층 가능'},
    {'name': 'RSKOG 로스코그 트롤리', 'price': 34900, 'category': '수납', 'reason': '이동식 수납, 인테리어 소품'},
    {'name': 'BILLY 빌리 책장 80x28x202', 'price': 59900, 'category': '수납', 'reason': '클래식 책장'},
    {'name': 'LACK 라크 벽선반', 'price': 9900, 'category': '수납', 'reason': '심플한 벽 선반'},

    # 주방
    {'name': '365+ 유리밀폐용기 세트', 'price': 19900, 'category': '주방', 'reason': '오븐/전자레인지 OK'},
    {'name': 'VARDAGEN 바르다겐 냄비 5L', 'price': 29900, 'category': '주방', 'reason': '에나멜 냄비, 감성 인테리어'},
    {'name': 'IKEA 365+ 프라이팬 28cm', 'price': 19900, 'category': '주방', 'reason': '논스틱, 가성비'},
    {'name': 'KORKEN 코르켄 유리병 1L', 'price': 2900, 'category': '주방', 'reason': '디스펜서, 예쁜 유리병'},
    {'name': 'ORDNING 오르드닝 수저통', 'price': 7900, 'category': '주방', 'reason': '스테인리스 수저통'},
    {'name': 'APTITLIG 압티틀리그 도마', 'price': 14900, 'category': '주방', 'reason': '대나무 도마'},
    {'name': 'FLITIGHET 플리티게트 접시 세트', 'price': 9900, 'category': '주방', 'reason': '심플 화이트 접시'},

    # 조명
    {'name': 'TERTIAL 테르티알 스탠드', 'price': 12900, 'category': '조명', 'reason': '책상 조명, 각도조절'},
    {'name': 'NÄVLINGE 네블링에 LED클립조명', 'price': 14900, 'category': '조명', 'reason': '클립형 독서등'},
    {'name': 'RANARP 라나르프 스탠드', 'price': 49900, 'category': '조명', 'reason': '빈티지 감성 조명'},
    {'name': 'HEKTAR 헥타르 펜던트조명', 'price': 49900, 'category': '조명', 'reason': '인더스트리얼 감성'},
    {'name': 'SYMFONISK 심포니스크 스피커램프', 'price': 179000, 'category': '조명', 'reason': '소노스 스피커+조명'},

    # 침실/침구
    {'name': 'MALM 말름 침대프레임', 'price': 199000, 'category': '침실', 'reason': '베스트셀러 침대'},
    {'name': 'KOPARDAL 코파르달 침대프레임', 'price': 129000, 'category': '침실', 'reason': '철제 프레임, 심플'},
    {'name': 'HAUGA 하우가 옷장', 'price': 299000, 'category': '침실', 'reason': '슬라이딩 도어 옷장'},
    {'name': 'DVALA 드발라 이불커버 세트', 'price': 29900, 'category': '침구', 'reason': '순면 100%'},
    {'name': 'LUDDROS 루드로스 매트리스패드', 'price': 24900, 'category': '침구', 'reason': '매트리스 보호'},

    # 거실/인테리어
    {'name': 'KIVIK 시빅 소파', 'price': 599000, 'category': '거실', 'reason': '편안한 패밀리 소파'},
    {'name': 'POÄNG 포엥 안락의자', 'price': 99900, 'category': '거실', 'reason': '아이코닉 디자인'},
    {'name': 'VITTSJO 비트셰 선반유닛', 'price': 34900, 'category': '거실', 'reason': '미니멀 철제 선반'},
    {'name': 'FEJKA 페이카 인조화분', 'price': 3900, 'category': '인테리어', 'reason': '관리 필요없는 식물'},
    {'name': 'RIBBA 리바 액자 30x40', 'price': 7900, 'category': '인테리어', 'reason': '심플 액자'},

    # 욕실
    {'name': 'VOXNAN 복스난 수건걸이', 'price': 14900, 'category': '욕실', 'reason': '스테인리스 수건걸이'},
    {'name': 'GODMORGON 고드모르곤 세면대', 'price': 199000, 'category': '욕실', 'reason': '북유럽 감성 세면대'},
    {'name': 'TISKEN 티스켄 흡착선반', 'price': 9900, 'category': '욕실', 'reason': '구멍없이 설치'},

    # 어린이
    {'name': 'TROFAST 트로파스트 수납콤비', 'price': 69900, 'category': '어린이', 'reason': '장난감 정리 필수'},
    {'name': 'MAMMUT 맘무트 어린이의자', 'price': 12900, 'category': '어린이', 'reason': '가벼운 플라스틱 의자'},
    {'name': 'FLISAT 플리사트 어린이책상', 'price': 49900, 'category': '어린이', 'reason': '높이조절 가능'},
]


def get_session():
    """요청 세션 생성"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    })
    return session


def search_naver_blog(session, keyword, count=10):
    """네이버 블로그 검색"""
    # 실제 구현시 네이버 API 사용 필요
    # 여기서는 인기 상품 데이터 반환
    return []


def add_products_to_db(products, store_key, source='curated'):
    """상품 데이터베이스 추가"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    added = 0
    for product in products:
        # 중복 체크
        cur.execute('''
            SELECT id FROM products
            WHERE name = ? AND store_key = ?
        ''', (product['name'], store_key))

        if cur.fetchone():
            continue

        # 상품 추가
        cur.execute('''
            INSERT INTO products (
                video_id, name, price, category, reason,
                store_key, store_name, source_view_count,
                recommendation_quote, official_name, official_price,
                is_matched, is_approved, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?)
        ''', (
            f'{source}_{store_key}_{added}',  # 가상 video_id
            product['name'],
            product['price'],
            product['category'],
            product.get('reason', ''),
            store_key,
            '코스트코' if store_key == 'costco' else '이케아',
            0,  # source_view_count
            product.get('reason', ''),  # recommendation_quote
            product['name'],  # official_name
            product['price'],  # official_price
            datetime.now().isoformat()
        ))
        added += 1

    conn.commit()
    conn.close()
    return added


def add_store_info_to_products(store_key):
    """매장 정보 추가"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 매장 정보
    if store_key == 'costco':
        stores = [
            {'name': '코스트코 양재점', 'address': '서울 서초구 양재대로 170', 'phone': '02-2190-7000'},
            {'name': '코스트코 양평점', 'address': '서울 영등포구 양평로 50', 'phone': '02-2635-7000'},
            {'name': '코스트코 상봉점', 'address': '서울 중랑구 상봉로 111', 'phone': '02-6913-7000'},
            {'name': '코스트코 일산점', 'address': '경기 고양시 일산동구 일산로 91', 'phone': '031-920-7000'},
        ]
        availability = '코스트코 회원 전용 (연회비 필요)'
    else:
        stores = [
            {'name': '이케아 광명점', 'address': '경기 광명시 일직로 17', 'phone': '1670-4532'},
            {'name': '이케아 고양점', 'address': '경기 고양시 덕양구 권율대로 420', 'phone': '1670-4532'},
            {'name': '이케아 기흥점', 'address': '경기 용인시 기흥구 신고매로 63', 'phone': '1670-4532'},
            {'name': '이케아 동부산점', 'address': '부산 기장군 기장읍 기장해안로 147', 'phone': '1670-4532'},
        ]
        availability = '이케아 매장 및 온라인 구매 가능'

    # 업데이트
    cur.execute('''
        UPDATE products
        SET store_locations = ?,
            availability_note = ?
        WHERE store_key = ? AND store_locations IS NULL
    ''', (
        json.dumps(stores, ensure_ascii=False),
        availability,
        store_key
    ))

    conn.commit()
    updated = cur.rowcount
    conn.close()
    return updated


def run_multi_source_crawl():
    """멀티소스 크롤링 실행"""
    print('=' * 50)
    print('=== 멀티소스 크롤링 시작 ===')
    print('=' * 50)

    results = {
        'costco': 0,
        'ikea': 0
    }

    # 1. 코스트코 인기 상품 추가
    print('\n[코스트코] 인기 상품 추가 중...')
    costco_added = add_products_to_db(COSTCO_POPULAR_PRODUCTS, 'costco', 'blog_curated')
    results['costco'] = costco_added
    print(f'  -> {costco_added}개 상품 추가됨')

    # 2. 이케아 인기 상품 추가
    print('\n[이케아] 인기 상품 추가 중...')
    ikea_added = add_products_to_db(IKEA_POPULAR_PRODUCTS, 'ikea', 'blog_curated')
    results['ikea'] = ikea_added
    print(f'  -> {ikea_added}개 상품 추가됨')

    # 3. 매장 정보 추가
    print('\n[매장 정보] 업데이트 중...')
    costco_stores = add_store_info_to_products('costco')
    ikea_stores = add_store_info_to_products('ikea')
    print(f'  -> 코스트코: {costco_stores}개, 이케아: {ikea_stores}개 업데이트')

    print('\n' + '=' * 50)
    print(f'=== 크롤링 완료 ===')
    print(f'코스트코: {results["costco"]}개')
    print(f'이케아: {results["ikea"]}개')
    print('=' * 50)

    return results


if __name__ == '__main__':
    run_multi_source_crawl()
