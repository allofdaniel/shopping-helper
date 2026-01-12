# -*- coding: utf-8 -*-
"""
Costco Korea Playwright 크롤러
- 실제 사이트 데이터 수집 (가격, 평점, 리뷰 수)
- DB 저장 기능 포함
"""
import re
import asyncio
import sqlite3
import urllib.parse
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[!] Playwright 설치 필요: pip install playwright && playwright install chromium")

# DB 경로 설정
DB_PATH = '../data/products.db'

# 검색 카테고리
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


class CostcoPlaywrightCrawler:
    """Costco Korea Playwright 크롤러"""

    BASE_URL = "https://www.costco.co.kr"
    SEARCH_URL = "https://www.costco.co.kr/search"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def _init_browser(self):
        """브라우저 초기화"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되어 있지 않습니다")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ko-KR",
        )

        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        self.page = await self.context.new_page()

    async def _close_browser(self):
        """브라우저 종료"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None

    async def search_products(self, query: str, limit: int = 50) -> List[CostcoProduct]:
        """상품 검색"""
        if not self.page:
            await self._init_browser()

        products = []

        try:
            encoded_query = urllib.parse.quote(query)
            search_url = f"{self.SEARCH_URL}?text={encoded_query}"

            print(f"[Costco] '{query}' 검색 중...")
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(4)

            # 쿠키 동의 팝업 닫기
            try:
                cookie_btn = await self.page.query_selector('#onetrust-accept-btn-handler')
                if cookie_btn:
                    await cookie_btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            # 상품 파싱
            products = await self._parse_search_results(query, limit)
            print(f"[Costco] '{query}' 검색 완료: {len(products)}개 상품")

        except Exception as e:
            print(f"[Costco] 검색 실패 ({query}): {e}")

        return products

    async def _parse_search_results(self, category: str, limit: int) -> List[CostcoProduct]:
        """검색 결과 파싱"""
        products = []

        try:
            # 상품 목록 로딩 대기
            await self.page.wait_for_selector('[class*="product"], li[class*="product"]', timeout=15000)
        except Exception:
            print("[Costco] 상품 목록 로딩 타임아웃")
            return products

        try:
            # JavaScript로 상품 데이터 추출
            product_data = await self.page.evaluate('''() => {
                const results = [];

                // 상품 카드 선택
                const productCards = document.querySelectorAll('li[class*="product"], div[class*="product-item"]');

                productCards.forEach(card => {
                    try {
                        // 상품 URL에서 코드 추출
                        const link = card.querySelector('a[href*="/p/"]');
                        if (!link) return;

                        const href = link.getAttribute('href') || '';
                        // URL 패턴: /p/123456
                        const codeMatch = href.match(/\\/p\\/(\\d+)/);
                        if (!codeMatch) return;

                        const productCode = codeMatch[1];

                        // 상품명 추출
                        const nameEl = card.querySelector('a[href*="/p/"] + a, .product-name, [class*="product-name"]');
                        let name = '';
                        if (nameEl) {
                            name = nameEl.textContent.trim();
                        } else {
                            // 링크 텍스트에서 추출
                            const allLinks = card.querySelectorAll('a[href*="/p/"]');
                            if (allLinks.length > 1) {
                                name = allLinks[1].textContent.trim();
                            } else if (allLinks.length === 1) {
                                name = allLinks[0].textContent.trim();
                            }
                        }

                        // 가격 추출
                        let price = 0;
                        let originalPrice = null;

                        const priceEl = card.querySelector('[class*="price"], .product-price');
                        if (priceEl) {
                            const priceText = priceEl.textContent || '';
                            // "12,900원" 패턴
                            const priceMatch = priceText.match(/([\\d,]+)\\s*원/);
                            if (priceMatch) {
                                price = parseInt(priceMatch[1].replace(/,/g, ''));
                            }
                        }

                        // 원래 가격 (할인 상품)
                        const wasPriceEl = card.querySelector('[class*="was"], [class*="original"], .original-price');
                        if (wasPriceEl) {
                            const wasPriceText = wasPriceEl.textContent || '';
                            const wasMatch = wasPriceText.match(/([\\d,]+)\\s*원/);
                            if (wasMatch) {
                                originalPrice = parseInt(wasMatch[1].replace(/,/g, ''));
                            }
                        }

                        // 브랜드 추출
                        let brand = '';
                        const brandEl = card.querySelector('[class*="brand"]');
                        if (brandEl) {
                            brand = brandEl.textContent.trim();
                        } else if (name) {
                            // 상품명 첫 단어를 브랜드로 추정
                            const parts = name.split(' ');
                            if (parts.length > 1) {
                                brand = parts[0];
                            }
                        }

                        // 이미지 URL
                        const img = card.querySelector('img');
                        let imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '';

                        // 상품 URL
                        let productUrl = href;
                        if (productUrl.startsWith('/')) {
                            productUrl = 'https://www.costco.co.kr' + productUrl;
                        }

                        // 평점 및 리뷰 수
                        let rating = null;
                        let reviewCount = 0;

                        const ratingEl = card.querySelector('[class*="rating"], [class*="star"]');
                        if (ratingEl) {
                            const ratingText = ratingEl.textContent || '';
                            // "4.5 (123)" 패턴
                            const ratingMatch = ratingText.match(/(\\d+\\.?\\d*)\\s*\\((\\d+)\\)/);
                            if (ratingMatch) {
                                rating = parseFloat(ratingMatch[1]);
                                reviewCount = parseInt(ratingMatch[2]);
                            } else {
                                // 별점만 있는 경우
                                const starMatch = ratingText.match(/(\\d+\\.?\\d*)/);
                                if (starMatch) {
                                    rating = parseFloat(starMatch[1]);
                                }
                            }
                        }

                        // 온라인 전용 여부
                        const isOnlineOnly = card.textContent.includes('온라인') || card.textContent.includes('Online');

                        if (name && productCode && price > 0) {
                            results.push({
                                productCode,
                                name,
                                price,
                                originalPrice,
                                brand,
                                imgSrc,
                                productUrl,
                                rating,
                                reviewCount,
                                isOnlineOnly
                            });
                        }
                    } catch (e) {}
                });

                return results;
            }''')

            if not product_data:
                print("[Costco] 상품을 찾지 못함")
                return products

            seen_codes = set()
            for item in product_data:
                try:
                    product_code = item.get('productCode', '')
                    if not product_code or product_code in seen_codes:
                        continue
                    seen_codes.add(product_code)

                    name = item.get('name', '')
                    if not name:
                        continue

                    product = CostcoProduct(
                        product_no=product_code,
                        name=name,
                        price=item.get('price', 0),
                        original_price=item.get('originalPrice'),
                        image_url=item.get('imgSrc', ''),
                        product_url=item.get('productUrl', ''),
                        category=category,
                        brand=item.get('brand', ''),
                        rating=item.get('rating'),
                        review_count=item.get('reviewCount', 0),
                        is_online_only=item.get('isOnlineOnly', False),
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception:
                    continue

        except Exception as e:
            print(f"[Costco] 파싱 실패: {e}")

        return products

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


def create_costco_catalog_table():
    """Costco 카탈로그 테이블 생성/업데이트"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 테이블 존재 여부 확인
    tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    if 'costco_catalog' not in tables:
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
        print("[DB] costco_catalog 테이블 생성됨")
    else:
        # 기존 컬럼 확인
        cur.execute("PRAGMA table_info(costco_catalog)")
        columns = {row[1] for row in cur.fetchall()}

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


async def run_costco_crawl(categories: List[str] = None, limit_per_category: int = 30):
    """Costco 크롤링 실행"""
    print("=== Costco Playwright 크롤링 시작 ===\n")

    create_costco_catalog_table()

    crawler = CostcoPlaywrightCrawler(headless=True)

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

    try:
        for i, category in enumerate(categories, 1):
            print(f"[{i}/{len(categories)}] '{category}' 검색 중...")

            try:
                products = await crawler.search_products(category, limit=limit_per_category)

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
            await asyncio.sleep(2)

    finally:
        await crawler.close()

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
        name = row[0][:40] if row[0] else "Unknown"
        print(f"  {name}: {row[1]:,}원 (평점: {rating_str}, 리뷰: {row[3]})")

    conn.close()


if __name__ == '__main__':
    # 크롤링 실행
    asyncio.run(run_costco_crawl(limit_per_category=20))

    # 데이터 검증
    verify_costco_data()
