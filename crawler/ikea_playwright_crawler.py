# -*- coding: utf-8 -*-
"""
IKEA Korea Playwright 크롤러
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


class IkeaPlaywrightCrawler:
    """IKEA Korea Playwright 크롤러"""

    BASE_URL = "https://www.ikea.com/kr/ko"
    SEARCH_URL = "https://www.ikea.com/kr/ko/search/"

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

    async def search_products(self, query: str, limit: int = 50) -> List[IkeaProduct]:
        """상품 검색"""
        if not self.page:
            await self._init_browser()

        products = []

        try:
            encoded_query = urllib.parse.quote(query)
            search_url = f"{self.SEARCH_URL}?q={encoded_query}"

            print(f"[IKEA] '{query}' 검색 중...")
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # IKEA 로딩 느림

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
            print(f"[IKEA] '{query}' 검색 완료: {len(products)}개 상품")

        except Exception as e:
            print(f"[IKEA] 검색 실패 ({query}): {e}")

        return products

    async def _parse_search_results(self, category: str, limit: int) -> List[IkeaProduct]:
        """검색 결과 파싱 - 정확한 셀렉터 사용"""
        products = []

        try:
            # 상품 목록 로딩 대기
            await self.page.wait_for_selector('[class*="plp-product-list"], [class*="search"]', timeout=15000)
        except Exception:
            print("[IKEA] 상품 목록 로딩 타임아웃")
            return products

        try:
            # JavaScript로 상품 데이터 추출
            product_data = await self.page.evaluate('''() => {
                const results = [];

                // 상품 카드 선택 (다양한 셀렉터 시도)
                const productCards = document.querySelectorAll('[class*="pip-product-compact"], [data-testid="plp-product-card"]');

                productCards.forEach(card => {
                    try {
                        // 상품 URL에서 ID 추출
                        const link = card.querySelector('a[href*="/p/"]');
                        if (!link) return;

                        const href = link.getAttribute('href') || '';
                        // URL 패턴: /p/linnmon-adils-table-white-s09246408/
                        const idMatch = href.match(/-s?(\\d{8})\\/?$/);
                        if (!idMatch) return;

                        const productId = idMatch[1];

                        // 상품명 추출 (브랜드 + 설명)
                        const brandEl = card.querySelector('[class*="pip-header-section__title"]');
                        const descEl = card.querySelector('[class*="pip-header-section__description"], [class*="description-text"]');

                        const brand = brandEl ? brandEl.textContent.trim() : '';
                        const description = descEl ? descEl.textContent.trim() : '';
                        const fullName = `${brand} ${description}`.trim();

                        // 가격 추출 - 숨겨진 "가격 ￦ 49900" 텍스트에서 추출
                        let price = 0;
                        let originalPrice = null;

                        // 현재 가격
                        const priceContainer = card.querySelector('[class*="pip-temp-price"], [class*="pip-price"]');
                        if (priceContainer) {
                            const priceText = priceContainer.textContent || '';
                            // "가격 ￦ 49900" 패턴
                            const priceMatch = priceText.match(/가격[^\\d]*(\\d+)/);
                            if (priceMatch) {
                                price = parseInt(priceMatch[1]);
                            } else {
                                // "￦49,900" 패턴
                                const altMatch = priceText.match(/₩?￦?([\\d,]+)/);
                                if (altMatch) {
                                    price = parseInt(altMatch[1].replace(/,/g, ''));
                                }
                            }
                        }

                        // 원래 가격 (할인 상품)
                        const wasPriceEl = card.querySelector('[class*="was-price"], [class*="정가"]');
                        if (wasPriceEl) {
                            const wasPriceText = wasPriceEl.textContent || '';
                            const wasMatch = wasPriceText.match(/정가[^\\d]*(\\d+)/);
                            if (wasMatch) {
                                originalPrice = parseInt(wasMatch[1]);
                            }
                        }

                        // 이미지 URL
                        const img = card.querySelector('img');
                        let imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '';

                        // 상품 URL
                        let productUrl = href;
                        if (productUrl.startsWith('/')) {
                            productUrl = 'https://www.ikea.com' + productUrl;
                        }

                        // 평점 및 리뷰 수 - "검토: 4.4 밖으로 5 별. 총 리뷰 수: (1470)" 패턴
                        let rating = null;
                        let reviewCount = 0;

                        const ratingBtn = card.querySelector('button[class*="rating"], [class*="review"]');
                        if (ratingBtn) {
                            const ratingText = ratingBtn.textContent || '';
                            // "검토: 4.4 밖으로 5 별" 패턴
                            const ratingMatch = ratingText.match(/검토:\\s*([\\d.]+)/);
                            if (ratingMatch) {
                                rating = parseFloat(ratingMatch[1]);
                            }
                            // "총 리뷰 수: (1470)" 패턴
                            const reviewMatch = ratingText.match(/\\((\\d+)\\)/);
                            if (reviewMatch) {
                                reviewCount = parseInt(reviewMatch[1]);
                            }
                        }

                        // 신상품/할인 플래그
                        const isNew = card.textContent.includes('신제품');
                        const isSale = originalPrice !== null && originalPrice > price;

                        if (fullName && productId && price > 0) {
                            results.push({
                                productId,
                                brand,
                                fullName,
                                price,
                                originalPrice,
                                imgSrc,
                                productUrl,
                                rating,
                                reviewCount,
                                isNew,
                                isSale
                            });
                        }
                    } catch (e) {}
                });

                return results;
            }''')

            if not product_data:
                print("[IKEA] 상품을 찾지 못함, 스크롤 후 재시도...")
                # 스크롤 후 재시도
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await asyncio.sleep(2)
                return await self._parse_search_results(category, limit)

            seen_ids = set()
            for item in product_data:
                try:
                    product_id = item.get('productId', '')
                    if not product_id or product_id in seen_ids:
                        continue
                    seen_ids.add(product_id)

                    name = item.get('fullName', '')
                    if not name:
                        continue

                    product = IkeaProduct(
                        product_no=product_id,
                        name=item.get('brand', ''),
                        name_ko=name,
                        price=item.get('price', 0),
                        original_price=item.get('originalPrice'),
                        image_url=item.get('imgSrc', ''),
                        product_url=item.get('productUrl', ''),
                        category=category,
                        rating=item.get('rating'),
                        review_count=item.get('reviewCount', 0),
                        is_new=item.get('isNew', False),
                        is_sale=item.get('isSale', False),
                    )
                    products.append(product)

                    if len(products) >= limit:
                        break

                except Exception:
                    continue

        except Exception as e:
            print(f"[IKEA] 파싱 실패: {e}")

        return products

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


def create_ikea_catalog_table():
    """IKEA 카탈로그 테이블 생성/업데이트"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 테이블 존재 여부 확인
    tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    if 'ikea_catalog' not in tables:
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
        print("[DB] ikea_catalog 테이블 생성됨")
    else:
        # 기존 컬럼 확인
        cur.execute("PRAGMA table_info(ikea_catalog)")
        columns = {row[1] for row in cur.fetchall()}

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


async def run_ikea_crawl(categories: List[str] = None, limit_per_category: int = 30):
    """IKEA 크롤링 실행"""
    print("=== IKEA Playwright 크롤링 시작 ===\n")

    create_ikea_catalog_table()

    crawler = IkeaPlaywrightCrawler(headless=True)

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

    try:
        for i, category in enumerate(categories, 1):
            print(f"[{i}/{len(categories)}] '{category}' 검색 중...")

            try:
                products = await crawler.search_products(category, limit=limit_per_category)

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
                        print(f"  [오류] {product.name_ko[:30] if product.name_ko else 'Unknown'}: {e}")

                conn.commit()

            except Exception as e:
                total_errors += 1
                print(f"  [오류] 카테고리 '{category}' 크롤링 실패: {e}")

            # API 부하 방지
            await asyncio.sleep(2)

    finally:
        await crawler.close()

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
    if price_stats[0]:
        print(f"가격 범위: {price_stats[0]:,}원 ~ {price_stats[1]:,}원 (평균: {price_stats[2]:,.0f}원)")

    # 가격=0 개수
    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE price = 0')
    zero_price = cur.fetchone()[0]
    print(f"가격=0 상품: {zero_price}개")

    # 평점 통계
    cur.execute('SELECT COUNT(*), AVG(rating) FROM ikea_catalog WHERE rating IS NOT NULL')
    rating_stats = cur.fetchone()
    if rating_stats[0]:
        avg_rating = rating_stats[1] if rating_stats[1] else 0
        print(f"평점 있는 상품: {rating_stats[0]}개 (평균: {avg_rating:.2f})")

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
        name = row[0][:40] if row[0] else "Unknown"
        print(f"  {name}: {row[1]:,}원 (평점: {rating_str}, 리뷰: {row[3]})")

    conn.close()


if __name__ == '__main__':
    # 크롤링 실행
    asyncio.run(run_ikea_crawl(limit_per_category=20))

    # 데이터 검증
    verify_ikea_data()
