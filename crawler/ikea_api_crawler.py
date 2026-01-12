# -*- coding: utf-8 -*-
"""
IKEA Korea API 크롤러
- 공식 API를 사용하여 정확한 가격/리뷰 데이터 수집
- 하드코딩 대신 실제 사이트 데이터 사용
"""
import requests
import sqlite3
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# DB 경로 설정
DB_PATH = '../data/products.db'

# IKEA Korea API 설정
IKEA_API_BASE = "https://sik.search.blue.cdtapps.com/kr/ko/search"
IKEA_PRODUCT_API = "https://www.ikea.com/kr/ko/products"

# 인기 검색 카테고리
IKEA_CATEGORIES = [
    "책상", "의자", "수납장", "선반", "옷장",
    "소파", "테이블", "침대", "조명", "거울",
    "러그", "커튼", "쿠션", "이불", "베개",
    "주방용품", "식기", "냄비", "프라이팬", "밀폐용기",
    "수납박스", "정리함", "바구니", "행거", "신발장",
    "화분", "조화", "액자", "시계", "휴지통",
]


@dataclass
class IkeaProduct:
    """IKEA 상품 데이터"""
    product_no: str
    name: str
    name_ko: str
    price: int
    original_price: Optional[int]
    image_url: str
    product_url: str
    category: str
    rating: Optional[float]
    review_count: int
    is_new: bool = False
    is_sale: bool = False


class IkeaAPICrawler:
    """IKEA Korea API 크롤러"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        })

    def search_products(self, query: str, limit: int = 50) -> List[IkeaProduct]:
        """상품 검색"""
        products = []

        try:
            # IKEA Search API 호출
            params = {
                'q': query,
                'size': min(limit, 100),
                'c': 'sr',  # search results
                'v': '20231101',
            }

            response = self.session.get(IKEA_API_BASE, params=params, timeout=30)

            if response.status_code != 200:
                print(f"[IKEA API] 검색 실패: {response.status_code}")
                return products

            data = response.json()

            # 상품 데이터 파싱
            search_results = data.get('searchResultPage', {})
            product_list = search_results.get('products', {}).get('main', {}).get('items', [])

            for item in product_list:
                try:
                    product = self._parse_product(item, query)
                    if product and product.price > 0:
                        products.append(product)
                except Exception as e:
                    print(f"[IKEA] 상품 파싱 실패: {e}")
                    continue

            print(f"[IKEA] '{query}' 검색: {len(products)}개 상품 발견")

        except Exception as e:
            print(f"[IKEA API] 오류: {e}")

        return products

    def _parse_product(self, item: Dict, category: str) -> Optional[IkeaProduct]:
        """API 응답에서 상품 정보 파싱"""
        try:
            product_data = item.get('product', {})

            # 기본 정보
            product_id = product_data.get('itemNo', '')
            if not product_id:
                return None

            name = product_data.get('name', '')
            type_name = product_data.get('typeName', '')
            full_name = f"{name} {type_name}".strip()

            # 가격 정보
            price_info = product_data.get('salesPrice', {})
            price = 0
            original_price = None

            # 현재 가격
            current_price = price_info.get('numeral', 0)
            if current_price:
                price = int(current_price)

            # 원래 가격 (할인 상품인 경우)
            was_price_info = product_data.get('wasPrice', {})
            if was_price_info:
                orig = was_price_info.get('numeral', 0)
                if orig and orig > price:
                    original_price = int(orig)

            # 이미지 URL
            main_image = product_data.get('mainImageUrl', '')
            if main_image and not main_image.startswith('http'):
                main_image = f"https://www.ikea.com{main_image}"

            # 상품 URL
            pip_url = product_data.get('pipUrl', '')
            if pip_url and not pip_url.startswith('http'):
                pip_url = f"https://www.ikea.com{pip_url}"

            # 리뷰 정보
            rating_info = product_data.get('rating', {})
            rating = rating_info.get('average', None)
            review_count = rating_info.get('count', 0)

            if rating:
                rating = round(float(rating), 1)

            # 신상품/할인 플래그
            is_new = product_data.get('isNew', False)
            is_sale = original_price is not None and original_price > price

            return IkeaProduct(
                product_no=product_id,
                name=name,
                name_ko=full_name,
                price=price,
                original_price=original_price,
                image_url=main_image,
                product_url=pip_url,
                category=category,
                rating=rating,
                review_count=review_count,
                is_new=is_new,
                is_sale=is_sale,
            )

        except Exception as e:
            print(f"[IKEA] 파싱 오류: {e}")
            return None


def create_ikea_catalog_table():
    """IKEA 카탈로그 테이블 생성 (rating/review_count 포함)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 기존 테이블 스키마 확인 및 업데이트
    cur.execute("PRAGMA table_info(ikea_catalog)")
    columns = {row[1] for row in cur.fetchall()}

    if 'ikea_catalog' not in [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        # 테이블이 없으면 새로 생성
        cur.execute('''
            CREATE TABLE ikea_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_no TEXT UNIQUE,
                name TEXT NOT NULL,
                name_ko TEXT,
                price INTEGER NOT NULL,
                original_price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                rating REAL,
                review_count INTEGER DEFAULT 0,
                is_new INTEGER DEFAULT 0,
                is_sale INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # 누락된 컬럼 추가
        needed_columns = {
            'rating': 'REAL',
            'review_count': 'INTEGER DEFAULT 0',
            'original_price': 'INTEGER',
            'is_new': 'INTEGER DEFAULT 0',
            'is_sale': 'INTEGER DEFAULT 0',
            'name_ko': 'TEXT',
        }

        for col_name, col_type in needed_columns.items():
            if col_name not in columns:
                try:
                    cur.execute(f'ALTER TABLE ikea_catalog ADD COLUMN {col_name} {col_type}')
                    print(f"[DB] ikea_catalog에 {col_name} 컬럼 추가됨")
                except sqlite3.OperationalError:
                    pass

    conn.commit()
    conn.close()


def run_ikea_catalog_crawl(categories: List[str] = None, limit_per_category: int = 50):
    """IKEA 카탈로그 크롤링 실행"""
    print("=== IKEA 카탈로그 크롤링 시작 ===\n")

    create_ikea_catalog_table()

    crawler = IkeaAPICrawler()

    if categories is None:
        categories = IKEA_CATEGORIES

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 기존 수 확인
    cur.execute('SELECT COUNT(*) FROM ikea_catalog')
    before_count = cur.fetchone()[0]
    print(f"기존 카탈로그: {before_count}개\n")

    total_added = 0
    total_updated = 0
    total_errors = 0

    for i, category in enumerate(categories, 1):
        print(f"[{i}/{len(categories)}] '{category}' 검색 중...")

        try:
            products = crawler.search_products(category, limit=limit_per_category)

            for product in products:
                try:
                    # 기존 상품 확인
                    cur.execute('SELECT id, price FROM ikea_catalog WHERE product_no = ?',
                               (product.product_no,))
                    existing = cur.fetchone()

                    if existing:
                        # 업데이트
                        cur.execute('''
                            UPDATE ikea_catalog
                            SET name=?, name_ko=?, price=?, original_price=?,
                                image_url=?, product_url=?, category=?,
                                rating=?, review_count=?, is_new=?, is_sale=?,
                                updated_at=datetime('now')
                            WHERE product_no=?
                        ''', (
                            product.name, product.name_ko, product.price,
                            product.original_price, product.image_url,
                            product.product_url, product.category,
                            product.rating, product.review_count,
                            1 if product.is_new else 0,
                            1 if product.is_sale else 0,
                            product.product_no
                        ))
                        total_updated += 1
                    else:
                        # 신규 추가
                        cur.execute('''
                            INSERT INTO ikea_catalog
                            (product_no, name, name_ko, price, original_price,
                             image_url, product_url, category, rating, review_count,
                             is_new, is_sale, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        ''', (
                            product.product_no, product.name, product.name_ko,
                            product.price, product.original_price,
                            product.image_url, product.product_url, product.category,
                            product.rating, product.review_count,
                            1 if product.is_new else 0,
                            1 if product.is_sale else 0,
                        ))
                        total_added += 1

                except Exception as e:
                    total_errors += 1
                    print(f"  [오류] {product.name}: {e}")

            conn.commit()

        except Exception as e:
            total_errors += 1
            print(f"  [오류] 카테고리 '{category}' 크롤링 실패: {e}")

        # API 부하 방지
        time.sleep(1)

    # 최종 통계
    cur.execute('SELECT COUNT(*) FROM ikea_catalog')
    after_count = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE price > 0')
    valid_count = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE rating IS NOT NULL')
    rated_count = cur.fetchone()[0]

    print(f"\n=== IKEA 크롤링 완료 ===")
    print(f"신규 추가: {total_added}개")
    print(f"업데이트: {total_updated}개")
    print(f"오류: {total_errors}개")
    print(f"최종 카탈로그: {after_count}개")
    print(f"가격 있음: {valid_count}개")
    print(f"평점 있음: {rated_count}개")

    conn.close()

    return {
        'added': total_added,
        'updated': total_updated,
        'errors': total_errors,
        'total': after_count,
    }


def verify_ikea_data():
    """IKEA 데이터 검증"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== IKEA 데이터 검증 ===")

    # 가격 분포
    cur.execute('SELECT MIN(price), MAX(price), AVG(price) FROM ikea_catalog WHERE price > 0')
    price_stats = cur.fetchone()
    print(f"가격 범위: {price_stats[0]:,}원 ~ {price_stats[1]:,}원 (평균: {price_stats[2]:,.0f}원)")

    # 가격=0 개수
    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE price = 0')
    zero_price = cur.fetchone()[0]
    print(f"가격=0 상품: {zero_price}개")

    # 평점 통계
    cur.execute('SELECT COUNT(*), AVG(rating) FROM ikea_catalog WHERE rating IS NOT NULL')
    rating_stats = cur.fetchone()
    print(f"평점 있는 상품: {rating_stats[0]}개 (평균: {rating_stats[1]:.2f})")

    # 리뷰 통계
    cur.execute('SELECT SUM(review_count) FROM ikea_catalog')
    total_reviews = cur.fetchone()[0] or 0
    print(f"총 리뷰 수: {total_reviews:,}개")

    # 샘플 출력
    print("\n--- 샘플 상품 (가격 높은 순) ---")
    cur.execute('''
        SELECT name_ko, price, rating, review_count
        FROM ikea_catalog
        WHERE price > 0
        ORDER BY price DESC
        LIMIT 5
    ''')
    for row in cur.fetchall():
        rating_str = f"{row[2]:.1f}" if row[2] else "N/A"
        print(f"  {row[0][:40]}: {row[1]:,}원 (평점: {rating_str}, 리뷰: {row[3]})")

    conn.close()


if __name__ == '__main__':
    # 크롤링 실행
    result = run_ikea_catalog_crawl(limit_per_category=30)

    # 데이터 검증
    verify_ikea_data()
