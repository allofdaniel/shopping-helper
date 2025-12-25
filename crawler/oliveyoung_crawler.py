# -*- coding: utf-8 -*-
"""
올리브영 크롤러
Playwright를 사용한 브라우저 기반 크롤링
(올리브영은 일반 HTTP 요청을 차단함)

설치: pip install playwright && playwright install chromium
"""
import time
from typing import Optional
from dataclasses import dataclass

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class OliveyoungProduct:
    """올리브영 상품 정보"""
    product_code: str
    name: str
    brand: str
    price: int
    original_price: int
    image_url: str
    product_url: str
    category: str
    rating: float
    review_count: int
    is_best: bool
    is_sale: bool

    def to_dict(self) -> dict:
        return {
            "product_no": self.product_code,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "original_price": self.original_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "rating": self.rating,
            "review_count": self.review_count,
            "is_best": self.is_best,
            "is_sale": self.is_sale,
        }


class OliveyoungCrawler:
    """올리브영 크롤러 (Playwright 기반)"""

    BASE_URL = "https://www.oliveyoung.co.kr"
    SEARCH_URL = "https://www.oliveyoung.co.kr/store/search/getSearchMain.do"

    # 주요 카테고리
    CATEGORIES = {
        "skincare": "스킨케어",
        "makeup": "메이크업",
        "bodycare": "바디케어",
        "haircare": "헤어케어",
        "fragrance": "향수",
        "mens": "맨즈케어",
        "health": "건강식품",
        "beauty_device": "뷰티디바이스",
    }

    def __init__(self, headless: bool = True):
        if not PLAYWRIGHT_AVAILABLE:
            print("Playwright 미설치. 설치: pip install playwright && playwright install chromium")
            self.browser = None
            return

        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    def _init_browser(self):
        """브라우저 초기화"""
        if not PLAYWRIGHT_AVAILABLE:
            return False

        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            self.page = self.context.new_page()
            return True
        except Exception as e:
            print(f"브라우저 초기화 실패: {e}")
            return False

    def _close_browser(self):
        """브라우저 종료"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

    def search_products(self, query: str, max_results: int = 20) -> list:
        """상품 검색"""
        if not PLAYWRIGHT_AVAILABLE:
            print("Playwright 필요")
            return []

        products = []

        if not self._init_browser():
            return []

        try:
            # 검색 페이지 접속
            search_url = f"{self.SEARCH_URL}?query={query}"
            self.page.goto(search_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # 상품 목록 추출
            product_elements = self.page.query_selector_all(".prd_info")

            for elem in product_elements[:max_results]:
                try:
                    product = self._parse_product_element(elem)
                    if product:
                        products.append(product)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"올리브영 검색 오류 ({query}): {e}")

        finally:
            self._close_browser()

        return products

    def _parse_product_element(self, elem) -> Optional[OliveyoungProduct]:
        """상품 요소 파싱"""
        try:
            # 상품명
            name_elem = elem.query_selector(".tx_name")
            name = name_elem.inner_text().strip() if name_elem else ""

            # 브랜드
            brand_elem = elem.query_selector(".tx_brand")
            brand = brand_elem.inner_text().strip() if brand_elem else ""

            # 가격
            price_elem = elem.query_selector(".tx_cur .tx_num")
            price_text = price_elem.inner_text().strip() if price_elem else "0"
            price = int(price_text.replace(",", "").replace("원", ""))

            # 원가
            org_price_elem = elem.query_selector(".tx_org .tx_num")
            org_price = price
            if org_price_elem:
                org_text = org_price_elem.inner_text().strip()
                org_price = int(org_text.replace(",", "").replace("원", ""))

            # 링크
            link_elem = elem.query_selector("a")
            product_url = link_elem.get_attribute("href") if link_elem else ""
            if product_url and not product_url.startswith("http"):
                product_url = self.BASE_URL + product_url

            # 품번 추출 (URL에서)
            product_code = ""
            if "goodsNo=" in product_url:
                product_code = product_url.split("goodsNo=")[1].split("&")[0]

            # 이미지
            img_elem = elem.query_selector("img")
            image_url = img_elem.get_attribute("src") if img_elem else ""

            if not name:
                return None

            return OliveyoungProduct(
                product_code=product_code,
                name=name,
                brand=brand,
                price=price,
                original_price=org_price,
                image_url=image_url,
                product_url=product_url,
                category="",
                rating=0.0,
                review_count=0,
                is_best=False,
                is_sale=org_price > price,
            )

        except Exception as e:
            return None

    def search_and_match(self, query: str, threshold: float = 0.3) -> Optional[OliveyoungProduct]:
        """검색 및 최적 매칭"""
        products = self.search_products(query, max_results=10)

        if not products:
            return None

        query_lower = query.lower()
        best_match = None
        best_score = 0

        for product in products:
            name_lower = product.name.lower()
            brand_lower = product.brand.lower()
            full_name = f"{brand_lower} {name_lower}"

            query_words = set(query_lower.split())
            name_words = set(full_name.split())

            if query_words and name_words:
                intersection = query_words & name_words
                union = query_words | name_words
                score = len(intersection) / len(union)
            else:
                score = 0

            if query_lower in full_name:
                score += 0.3

            if score > best_score and score >= threshold:
                best_score = score
                best_match = product

        return best_match


# 올리브영 API 직접 접근이 어려우므로
# 네이버 쇼핑 API로 대체하는 간이 버전
class OliveyoungNaverProxy:
    """네이버 쇼핑을 통한 올리브영 상품 검색 (API 키 필요)"""

    def __init__(self, client_id: str = None, client_secret: str = None):
        import os
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET")
        self.api_available = bool(self.client_id and self.client_secret)

    def search_products(self, query: str, max_results: int = 20) -> list:
        """네이버 쇼핑 API로 올리브영 상품 검색"""
        if not self.api_available:
            print("네이버 API 키 필요 (NAVER_CLIENT_ID, NAVER_CLIENT_SECRET)")
            return []

        import requests

        url = "https://openapi.naver.com/v1/search/shop.json"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        params = {
            "query": f"올리브영 {query}",
            "display": max_results,
            "sort": "sim",
        }

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            products = []
            for item in data.get("items", []):
                products.append({
                    "name": item.get("title", "").replace("<b>", "").replace("</b>", ""),
                    "price": int(item.get("lprice", 0)),
                    "image_url": item.get("image", ""),
                    "product_url": item.get("link", ""),
                    "brand": item.get("brand", ""),
                    "category": item.get("category1", ""),
                })

            return products

        except Exception as e:
            print(f"네이버 API 오류: {e}")
            return []


import sqlite3
import requests

DB_PATH = '../data/products.db'

# 올리브영 베스트셀러/추천 키워드
SEARCH_KEYWORDS = [
    '선크림', '립스틱', '토너', '세럼', '에센스', '크림', '로션',
    '클렌징', '마스크팩', '아이크림', '파운데이션', '쿠션', '컨실러',
    '아이섀도우', '마스카라', '아이라이너', '블러셔', '하이라이터',
    '샴푸', '컨디셔너', '바디워시', '바디로션', '핸드크림',
    '향수', '디퓨저', '립밤', '립틴트', '립글로스',
    '영양제', '비타민', '콜라겐', '유산균', '다이어트',
]


def create_oliveyoung_table(conn):
    """올리브영 카탈로그 테이블 생성"""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS oliveyoung_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_no TEXT UNIQUE,
            name TEXT,
            brand TEXT,
            price INTEGER,
            original_price INTEGER,
            image_url TEXT,
            product_url TEXT,
            category TEXT,
            rating REAL,
            review_count INTEGER,
            is_best INTEGER DEFAULT 0,
            is_sale INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()


def run_oliveyoung_catalog_crawl():
    """올리브영 카탈로그 크롤링 (Playwright 기반)"""
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright 미설치. requests로 대체 시도...")
        return run_oliveyoung_api_crawl()

    conn = sqlite3.connect(DB_PATH)
    create_oliveyoung_table(conn)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM oliveyoung_catalog')
    before = cur.fetchone()[0]
    print(f'기존 올리브영 카탈로그: {before}개')

    crawler = OliveyoungCrawler(headless=True)
    all_products = []

    print('\n=== 올리브영 키워드 검색 ===')
    for keyword in SEARCH_KEYWORDS:
        print(f'  "{keyword}" 검색...')
        try:
            products = crawler.search_products(keyword, max_results=50)
            all_products.extend([p.to_dict() for p in products])
            print(f'    -> {len(products)}개')
        except Exception as e:
            print(f'    에러: {e}')
        time.sleep(1)

    # 중복 제거
    seen = set()
    unique = []
    for p in all_products:
        if p['product_no'] and p['product_no'] not in seen:
            seen.add(p['product_no'])
            unique.append(p)

    print(f'\n총 수집: {len(all_products)}개 -> 중복제거: {len(unique)}개')

    # DB 저장
    added = 0
    for p in unique:
        cur.execute('SELECT id FROM oliveyoung_catalog WHERE product_no = ?', (p['product_no'],))
        if cur.fetchone():
            cur.execute('''
                UPDATE oliveyoung_catalog SET name=?, brand=?, price=?, original_price=?,
                image_url=?, category=?, updated_at=datetime('now')
                WHERE product_no=?
            ''', (p['name'], p['brand'], p['price'], p['original_price'],
                  p['image_url'], p['category'], p['product_no']))
        else:
            cur.execute('''
                INSERT INTO oliveyoung_catalog (product_no, name, brand, price, original_price,
                    image_url, product_url, category, rating, review_count, is_best, is_sale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (p['product_no'], p['name'], p['brand'], p['price'], p['original_price'],
                  p['image_url'], p['product_url'], p['category'], p['rating'],
                  p['review_count'], 1 if p['is_best'] else 0, 1 if p['is_sale'] else 0))
            added += 1

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM oliveyoung_catalog')
    after = cur.fetchone()[0]
    print(f'\n신규 추가: {added}개')
    print(f'최종 올리브영 카탈로그: {after}개')

    conn.close()
    return after


def run_oliveyoung_api_crawl():
    """올리브영 API 직접 호출 시도 (requests 기반)"""
    conn = sqlite3.connect(DB_PATH)
    create_oliveyoung_table(conn)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM oliveyoung_catalog')
    before = cur.fetchone()[0]
    print(f'기존 올리브영 카탈로그: {before}개')

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Referer': 'https://www.oliveyoung.co.kr/',
    })

    all_products = []

    # 베스트셀러 카테고리별 크롤링 시도
    best_categories = [
        ('1000000100010001', '스킨케어'),
        ('1000000100010002', '마스크/팩'),
        ('1000000100010003', '클렌징'),
        ('1000000100020001', '립메이크업'),
        ('1000000100020002', '베이스메이크업'),
        ('1000000100020003', '아이메이크업'),
        ('1000000100030001', '헤어케어'),
        ('1000000100030002', '바디케어'),
        ('1000000100040001', '향수'),
        ('1000000100050001', '건강식품'),
    ]

    print('\n=== 올리브영 베스트 API 크롤링 ===')
    for cat_code, cat_name in best_categories:
        print(f'  {cat_name}...')
        try:
            url = "https://www.oliveyoung.co.kr/store/display/getBestList.do"
            params = {
                'dispCatNo': cat_code,
                'pageIdx': 1,
                'rowsPerPage': 48,
            }
            resp = session.get(url, params=params, timeout=15)

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    items = data.get('bestList', []) or []
                    for item in items:
                        product = {
                            'product_no': item.get('goodsNo', ''),
                            'name': item.get('goodsNm', ''),
                            'brand': item.get('brandNm', ''),
                            'price': int(item.get('finalPrc', 0) or 0),
                            'original_price': int(item.get('prc', 0) or 0),
                            'image_url': item.get('goodsImg', ''),
                            'product_url': f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={item.get('goodsNo', '')}",
                            'category': cat_name,
                            'rating': float(item.get('reviewScore', 0) or 0),
                            'review_count': int(item.get('reviewCnt', 0) or 0),
                            'is_best': True,
                            'is_sale': item.get('saleYn') == 'Y',
                        }
                        if product['product_no'] and product['name']:
                            all_products.append(product)
                    print(f'    -> {len(items)}개')
                except:
                    print(f'    JSON 파싱 실패')
            else:
                print(f'    HTTP {resp.status_code}')
        except Exception as e:
            print(f'    에러: {e}')
        time.sleep(0.5)

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
        cur.execute('SELECT id FROM oliveyoung_catalog WHERE product_no = ?', (p['product_no'],))
        if cur.fetchone():
            cur.execute('''
                UPDATE oliveyoung_catalog SET name=?, brand=?, price=?, original_price=?,
                image_url=?, category=?, rating=?, review_count=?, updated_at=datetime('now')
                WHERE product_no=?
            ''', (p['name'], p['brand'], p['price'], p['original_price'],
                  p['image_url'], p['category'], p['rating'], p['review_count'], p['product_no']))
        else:
            cur.execute('''
                INSERT INTO oliveyoung_catalog (product_no, name, brand, price, original_price,
                    image_url, product_url, category, rating, review_count, is_best, is_sale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (p['product_no'], p['name'], p['brand'], p['price'], p['original_price'],
                  p['image_url'], p['product_url'], p['category'], p['rating'],
                  p['review_count'], 1 if p['is_best'] else 0, 1 if p['is_sale'] else 0))
            added += 1

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM oliveyoung_catalog')
    after = cur.fetchone()[0]
    print(f'\n신규 추가: {added}개')
    print(f'최종 올리브영 카탈로그: {after}개')

    conn.close()
    return after


def main():
    """올리브영 카탈로그 크롤링 실행"""
    print("=== 올리브영 카탈로그 크롤러 ===\n")
    return run_oliveyoung_catalog_crawl()


if __name__ == "__main__":
    main()
