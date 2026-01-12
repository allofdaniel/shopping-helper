# -*- coding: utf-8 -*-
"""
Costco Korea API 크롤러
- 공식 API를 사용하여 정확한 가격/리뷰 데이터 수집
"""
import requests
import sqlite3
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

# DB 경로 설정
DB_PATH = '../data/products.db'

# Costco Korea API 설정
COSTCO_SEARCH_API = "https://www.costco.co.kr/rest/v2/korea/products/search"
COSTCO_BASE_URL = "https://www.costco.co.kr"

# 인기 검색 카테고리
COSTCO_CATEGORIES = [
    # 식품
    "고기", "소고기", "돼지고기", "닭고기", "해산물", "연어", "새우",
    "과자", "스낵", "견과류", "초콜릿", "젤리", "쿠키",
    "커피", "음료", "주스", "생수", "탄산", "우유",
    "라면", "즉석밥", "통조림", "소스", "조미료",
    "냉동식품", "피자", "만두", "아이스크림",
    "치즈", "요거트", "버터", "크림치즈",
    # 건강식품
    "비타민", "유산균", "오메가3", "영양제", "프로틴",
    # 생활용품
    "세제", "휴지", "물티슈", "주방세제", "섬유유연제",
    "프라이팬", "냄비", "식기", "텀블러", "보온병",
]


@dataclass
class CostcoProduct:
    """Costco 상품 데이터"""
    product_no: str
    name: str
    price: int
    original_price: Optional[int]
    image_url: str
    product_url: str
    category: str
    brand: str
    rating: Optional[float]
    review_count: int
    is_online_only: bool = False


class CostcoAPICrawler:
    """Costco Korea API 크롤러"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Referer': 'https://www.costco.co.kr/',
        })

    def search_products(self, query: str, limit: int = 50) -> List[CostcoProduct]:
        """상품 검색"""
        products = []

        try:
            params = {
                'query': query,
                'pageSize': min(limit, 100),
                'currentPage': 0,
                'fields': 'FULL',
                'lang': 'ko',
                'curr': 'KRW',
            }

            response = self.session.get(COSTCO_SEARCH_API, params=params, timeout=30)

            if response.status_code != 200:
                print(f"[Costco API] 검색 실패: {response.status_code}")
                return products

            data = response.json()
            product_list = data.get('products', [])

            for item in product_list:
                try:
                    product = self._parse_product(item, query)
                    if product and product.price > 0:
                        products.append(product)
                except Exception as e:
                    print(f"[Costco] 상품 파싱 실패: {e}")
                    continue

            print(f"[Costco] '{query}' 검색: {len(products)}개 상품 발견")

        except Exception as e:
            print(f"[Costco API] 오류: {e}")

        return products

    def _parse_product(self, item: Dict, category: str) -> Optional[CostcoProduct]:
        """API 응답에서 상품 정보 파싱"""
        try:
            # 기본 정보
            product_code = item.get('code', '')
            if not product_code:
                return None

            name = item.get('name', '')
            brand = item.get('brand', {}).get('name', '') if isinstance(item.get('brand'), dict) else ''

            # 가격 정보
            price = 0
            original_price = None

            price_data = item.get('price', {})
            if price_data:
                # 현재 가격
                current_value = price_data.get('value', 0)
                if current_value:
                    price = int(current_value)

                # 기존 가격 (할인 상품인 경우)
                was_price = price_data.get('wasPrice', {})
                if was_price:
                    orig_value = was_price.get('value', 0)
                    if orig_value and orig_value > price:
                        original_price = int(orig_value)

            # 이미지 URL
            images = item.get('images', [])
            image_url = ''
            if images:
                # 첫 번째 이미지 사용
                first_image = images[0] if isinstance(images[0], dict) else {'url': images[0]}
                image_url = first_image.get('url', '')
                if image_url and not image_url.startswith('http'):
                    image_url = f"{COSTCO_BASE_URL}{image_url}"

            # 상품 URL
            product_url = item.get('url', '')
            if product_url and not product_url.startswith('http'):
                product_url = f"{COSTCO_BASE_URL}{product_url}"

            # 리뷰 정보 (최상위 레벨에서 직접 읽기)
            rating = None
            review_count = 0

            # averageRating과 numberOfReviews는 최상위 레벨에 있음
            avg_rating = item.get('averageRating')
            if avg_rating:
                rating = round(float(avg_rating), 1)
            review_count = item.get('numberOfReviews', 0) or 0

            # 온라인 전용 여부
            is_online_only = item.get('onlineOnly', False)

            return CostcoProduct(
                product_no=product_code,
                name=name,
                price=price,
                original_price=original_price,
                image_url=image_url,
                product_url=product_url,
                category=category,
                brand=brand,
                rating=rating,
                review_count=review_count,
                is_online_only=is_online_only,
            )

        except Exception as e:
            print(f"[Costco] 파싱 오류: {e}")
            return None


def create_costco_catalog_table():
    """Costco 카탈로그 테이블 생성 (rating/review_count 포함)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 기존 테이블 스키마 확인
    cur.execute("PRAGMA table_info(costco_catalog)")
    columns = {row[1] for row in cur.fetchall()}

    tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    if 'costco_catalog' not in tables:
        # 테이블이 없으면 새로 생성
        cur.execute('''
            CREATE TABLE costco_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_no TEXT UNIQUE,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                original_price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                brand TEXT,
                rating REAL,
                review_count INTEGER DEFAULT 0,
                is_online_only INTEGER DEFAULT 0,
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
            'brand': 'TEXT',
            'is_online_only': 'INTEGER DEFAULT 0',
        }

        for col_name, col_type in needed_columns.items():
            if col_name not in columns:
                try:
                    cur.execute(f'ALTER TABLE costco_catalog ADD COLUMN {col_name} {col_type}')
                    print(f"[DB] costco_catalog에 {col_name} 컬럼 추가됨")
                except sqlite3.OperationalError:
                    pass

    conn.commit()
    conn.close()


def run_costco_catalog_crawl(categories: List[str] = None, limit_per_category: int = 50):
    """Costco 카탈로그 크롤링 실행"""
    print("=== Costco 카탈로그 크롤링 시작 ===\n")

    create_costco_catalog_table()

    crawler = CostcoAPICrawler()

    if categories is None:
        categories = COSTCO_CATEGORIES

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 기존 수 확인
    cur.execute('SELECT COUNT(*) FROM costco_catalog')
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
                    cur.execute('SELECT id, price FROM costco_catalog WHERE product_no = ?',
                               (product.product_no,))
                    existing = cur.fetchone()

                    if existing:
                        # 업데이트
                        cur.execute('''
                            UPDATE costco_catalog
                            SET name=?, price=?, original_price=?,
                                image_url=?, product_url=?, category=?, brand=?,
                                rating=?, review_count=?, is_online_only=?,
                                updated_at=datetime('now')
                            WHERE product_no=?
                        ''', (
                            product.name, product.price, product.original_price,
                            product.image_url, product.product_url,
                            product.category, product.brand,
                            product.rating, product.review_count,
                            1 if product.is_online_only else 0,
                            product.product_no
                        ))
                        total_updated += 1
                    else:
                        # 신규 추가
                        cur.execute('''
                            INSERT INTO costco_catalog
                            (product_no, name, price, original_price,
                             image_url, product_url, category, brand,
                             rating, review_count, is_online_only, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        ''', (
                            product.product_no, product.name, product.price,
                            product.original_price, product.image_url,
                            product.product_url, product.category, product.brand,
                            product.rating, product.review_count,
                            1 if product.is_online_only else 0,
                        ))
                        total_added += 1

                except Exception as e:
                    total_errors += 1
                    print(f"  [오류] {product.name[:30]}: {e}")

            conn.commit()

        except Exception as e:
            total_errors += 1
            print(f"  [오류] 카테고리 '{category}' 크롤링 실패: {e}")

        # API 부하 방지
        time.sleep(0.5)

    # 최종 통계
    cur.execute('SELECT COUNT(*) FROM costco_catalog')
    after_count = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE price > 0')
    valid_count = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE rating IS NOT NULL')
    rated_count = cur.fetchone()[0]

    print(f"\n=== Costco 크롤링 완료 ===")
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


def verify_costco_data():
    """Costco 데이터 검증"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Costco 데이터 검증 ===")

    # 가격 분포
    cur.execute('SELECT MIN(price), MAX(price), AVG(price) FROM costco_catalog WHERE price > 0')
    price_stats = cur.fetchone()
    if price_stats[0]:
        print(f"가격 범위: {price_stats[0]:,}원 ~ {price_stats[1]:,}원 (평균: {price_stats[2]:,.0f}원)")

    # 가격=0 개수
    cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE price = 0')
    zero_price = cur.fetchone()[0]
    print(f"가격=0 상품: {zero_price}개")

    # 평점 통계
    cur.execute('SELECT COUNT(*), AVG(rating) FROM costco_catalog WHERE rating IS NOT NULL')
    rating_stats = cur.fetchone()
    if rating_stats[0]:
        avg_rating = rating_stats[1] if rating_stats[1] else 0
        print(f"평점 있는 상품: {rating_stats[0]}개 (평균: {avg_rating:.2f})")

    # 리뷰 통계
    cur.execute('SELECT SUM(review_count) FROM costco_catalog')
    total_reviews = cur.fetchone()[0] or 0
    print(f"총 리뷰 수: {total_reviews:,}개")

    # 브랜드별 통계
    cur.execute('''
        SELECT brand, COUNT(*) as cnt
        FROM costco_catalog
        WHERE brand != '' AND brand IS NOT NULL
        GROUP BY brand
        ORDER BY cnt DESC
        LIMIT 5
    ''')
    print("\n--- 인기 브랜드 ---")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}개")

    # 샘플 출력
    print("\n--- 샘플 상품 (가격 높은 순) ---")
    cur.execute('''
        SELECT name, price, rating, review_count
        FROM costco_catalog
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
    result = run_costco_catalog_crawl(limit_per_category=30)

    # 데이터 검증
    verify_costco_data()
