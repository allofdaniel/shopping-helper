# -*- coding: utf-8 -*-
"""
이마트 트레이더스 전체 카탈로그 크롤러
- Playwright로 상품 목록 크롤링
- 카테고리별 베스트 상품 수집
"""
import sqlite3
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

DB_PATH = '../data/products.db'

# 트레이더스 카테고리 URL
TRADERS_CATEGORIES = [
    # 식품
    {"name": "신선식품", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050894"},
    {"name": "냉장냉동", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050895"},
    {"name": "가공식품", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050896"},
    {"name": "음료/커피", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050897"},
    {"name": "과자/간식", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050898"},
    # 생활용품
    {"name": "생활용품", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050899"},
    {"name": "주방용품", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050900"},
    {"name": "욕실용품", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050901"},
    {"name": "세제/청소", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050902"},
    # 기타
    {"name": "뷰티/건강", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050903"},
    {"name": "유아동", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050904"},
    {"name": "반려동물", "url": "https://traders.ssg.com/disp/category.ssg?dispCtgId=6000050905"},
]

# 검색 키워드로 수집
SEARCH_KEYWORDS = [
    "고기", "소고기", "돼지고기", "닭고기", "삼겹살",
    "우유", "계란", "치즈", "요거트", "버터",
    "과일", "채소", "쌀", "라면", "냉동식품",
    "커피", "생수", "주스", "맥주", "와인",
    "과자", "초콜릿", "견과류", "젤리",
    "세제", "휴지", "물티슈", "샴푸", "치약",
    "프라이팬", "냄비", "식기", "텀블러",
]


def extract_products_from_page(page):
    """페이지에서 상품 정보 추출 (SSG/이마트 구조) - 이미지 alt 텍스트 기반"""
    return page.evaluate('''() => {
        const products = [];
        const seen = new Set();

        // SSG 상품 카드들 - 링크에 itemId가 포함된 요소들 찾기
        const productLinks = document.querySelectorAll('a[href*="itemId="]');

        productLinks.forEach(link => {
            try {
                // itemId 추출
                const urlMatch = link.href.match(/itemId=([0-9]+)/);
                if (!urlMatch) return;
                const productNo = urlMatch[1];

                // 중복 체크
                if (seen.has(productNo)) return;

                // 이미지 alt에서 상품명 추출 (가장 신뢰성 높음)
                const img = link.querySelector('img');
                if (!img || !img.alt || img.alt.length < 2) return;

                const name = img.alt.trim();
                seen.add(productNo);

                // 이미지 URL
                const imageUrl = img.src || img.getAttribute('data-src') || '';

                // 상품 카드 컨테이너 찾기 (li 또는 상위 div)
                let container = link.closest('li') || link.closest('[class*="item"]') || link.parentElement?.parentElement?.parentElement;

                // 가격 추출 - 컨테이너에서 숫자 패턴 찾기
                let price = 0;
                let originalPrice = 0;

                if (container) {
                    // 가격 요소 찾기
                    const priceEls = container.querySelectorAll('[class*="price"], [class*="Price"], em, strong');
                    priceEls.forEach(el => {
                        const text = el.textContent || '';
                        const nums = text.replace(/[^0-9]/g, '');
                        if (nums.length >= 3 && nums.length <= 8) {
                            const num = parseInt(nums);
                            if (num >= 100 && num <= 10000000) {
                                if (price === 0) {
                                    price = num;
                                } else if (num > price) {
                                    originalPrice = num;
                                }
                            }
                        }
                    });

                    // 할인가/정상가 구분
                    if (originalPrice > 0 && originalPrice < price) {
                        [price, originalPrice] = [originalPrice, price];
                    }
                }

                if (originalPrice === 0) originalPrice = price;

                // 브랜드 추출 시도
                let brand = '';
                if (container) {
                    const brandEl = container.querySelector('[class*="brand"], [class*="Brand"]');
                    if (brandEl) brand = brandEl.textContent.trim();
                }

                // 평점/리뷰 추출 시도
                let rating = 0;
                let reviewCount = 0;
                if (container) {
                    const ratingEl = container.querySelector('[class*="star"], [class*="rating"], [class*="score"]');
                    if (ratingEl) {
                        const rMatch = ratingEl.textContent.match(/([0-9.]+)/);
                        if (rMatch) rating = parseFloat(rMatch[1]) || 0;
                    }
                    const reviewEl = container.querySelector('[class*="review"], [class*="count"]');
                    if (reviewEl) {
                        const rvMatch = reviewEl.textContent.match(/([0-9,]+)/);
                        if (rvMatch) reviewCount = parseInt(rvMatch[1].replace(/,/g, '')) || 0;
                    }
                }

                products.push({
                    productNo,
                    name,
                    brand,
                    price,
                    originalPrice,
                    imageUrl,
                    productUrl: link.href,
                    rating,
                    reviewCount,
                    isTraders: true
                });

            } catch (e) {}
        });

        return products;
    }''')


def create_table():
    """테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS traders_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_no TEXT UNIQUE,
            name TEXT,
            brand TEXT,
            price INTEGER,
            original_price INTEGER,
            image_url TEXT,
            product_url TEXT,
            category TEXT,
            unit_info TEXT,
            rating REAL,
            review_count INTEGER,
            is_traders INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


def crawl_traders():
    """트레이더스 크롤링"""
    print("=" * 60)
    print("TRADERS CATALOG CRAWL")
    print("=" * 60)

    create_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM traders_catalog')
    before = cur.fetchone()[0]
    print(f"Existing products: {before}")
    print()

    all_products = {}
    total_added = 0
    total_updated = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='ko-KR'
        )
        page = context.new_page()

        # 키워드 검색으로 수집
        print("Searching by keywords...")
        print("-" * 60)

        for i, keyword in enumerate(SEARCH_KEYWORDS, 1):
            try:
                print(f"[{i}/{len(SEARCH_KEYWORDS)}] '{keyword}'...", end=" ")

                # emart.ssg.com에서 트레이더스 배송 필터로 검색
                search_url = f"https://emart.ssg.com/search.ssg?target=all&query={keyword}"
                page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(3000)

                # 스크롤
                for _ in range(2):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(500)

                products = extract_products_from_page(page)

                for prod in products:
                    if prod['productNo'] and prod['productNo'] not in all_products:
                        prod['category'] = keyword
                        all_products[prod['productNo']] = prod

                print(f"found {len(products)} (total: {len(all_products)})")

            except Exception as e:
                print(f"ERROR: {str(e)[:30]}")

            time.sleep(0.5)

        browser.close()

    print()
    print(f"Total unique products: {len(all_products)}")

    # DB 저장
    print()
    print("Saving to database...")

    for prod in all_products.values():
        try:
            cur.execute('SELECT id FROM traders_catalog WHERE product_no = ?', (prod['productNo'],))
            existing = cur.fetchone()

            if existing:
                cur.execute('''
                    UPDATE traders_catalog
                    SET name=?, brand=?, price=?, original_price=?, image_url=?,
                        product_url=?, category=?, rating=?, review_count=?,
                        is_traders=?, updated_at=datetime('now')
                    WHERE product_no=?
                ''', (
                    prod['name'], prod['brand'], prod['price'], prod['originalPrice'],
                    prod['imageUrl'], prod['productUrl'], prod['category'],
                    prod.get('rating', 0), prod.get('reviewCount', 0),
                    1 if prod.get('isTraders') else 0,
                    prod['productNo']
                ))
                total_updated += 1
            else:
                cur.execute('''
                    INSERT INTO traders_catalog
                    (product_no, name, brand, price, original_price, image_url,
                     product_url, category, rating, review_count, is_traders, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    prod['productNo'], prod['name'], prod['brand'], prod['price'],
                    prod['originalPrice'], prod['imageUrl'], prod['productUrl'],
                    prod['category'], prod.get('rating', 0), prod.get('reviewCount', 0),
                    1 if prod.get('isTraders') else 0
                ))
                total_added += 1

        except Exception as e:
            print(f"  DB Error: {e}")

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM traders_catalog')
    after = cur.fetchone()[0]

    print()
    print("=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)
    print(f"Added: {total_added}")
    print(f"Updated: {total_updated}")
    print(f"Total: {after}")

    conn.close()

    return {'added': total_added, 'updated': total_updated, 'total': after}


if __name__ == '__main__':
    crawl_traders()
