# -*- coding: utf-8 -*-
"""
올리브영 전체 카탈로그 크롤러
- Playwright로 베스트셀러 페이지 직접 크롤링
- 카테고리별 상품 수집
"""
import sqlite3
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

DB_PATH = '../data/products.db'

# 올리브영 베스트 카테고리 URL
OLIVEYOUNG_CATEGORIES = [
    {"name": "스킨케어", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010001"},
    {"name": "마스크팩", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010002"},
    {"name": "클렌징", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010003"},
    {"name": "선케어", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010004"},
    {"name": "립메이크업", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100020001"},
    {"name": "베이스메이크업", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100020002"},
    {"name": "아이메이크업", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100020003"},
    {"name": "헤어케어", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100030001"},
    {"name": "바디케어", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100030002"},
    {"name": "향수/디퓨저", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100040001"},
    {"name": "네일", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100020005"},
    {"name": "맨즈케어", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100050001"},
    {"name": "건강식품", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100060001"},
    {"name": "다이어트", "url": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100060002"},
]

# 올리브영 랭킹 페이지 (더 안정적)
RANKING_URLS = [
    {"name": "전체랭킹", "url": "https://www.oliveyoung.co.kr/store/main/getBestList.do"},
    {"name": "스킨케어", "url": "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=100000100010001"},
    {"name": "메이크업", "url": "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=100000100020001"},
    {"name": "헤어바디", "url": "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=100000100030001"},
    {"name": "향수", "url": "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=100000100040001"},
    {"name": "건강식품", "url": "https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=100000100060001"},
]


def extract_products_from_page(page):
    """페이지에서 상품 정보 추출"""
    return page.evaluate('''() => {
        const products = [];

        // 상품 리스트 찾기 (여러 셀렉터 시도)
        const items = document.querySelectorAll('.prd_info, .prd-info, .prod_info, .cate_prd_list li, .best_list li');

        items.forEach(item => {
            try {
                // 상품명
                const nameEl = item.querySelector('.tx_name, .prd_name, .name a, .prd-name');
                const name = nameEl ? nameEl.textContent.trim() : '';

                // 브랜드
                const brandEl = item.querySelector('.tx_brand, .prd_brand, .brand');
                const brand = brandEl ? brandEl.textContent.trim() : '';

                // 가격
                let price = 0;
                const priceEl = item.querySelector('.tx_cur .tx_num, .prd_price .price, .price-2 span');
                if (priceEl) {
                    price = parseInt(priceEl.textContent.replace(/[^0-9]/g, '')) || 0;
                }

                // 원가
                let originalPrice = price;
                const orgEl = item.querySelector('.tx_org .tx_num, .org_price');
                if (orgEl) {
                    originalPrice = parseInt(orgEl.textContent.replace(/[^0-9]/g, '')) || price;
                }

                // 링크 & 상품번호
                const linkEl = item.querySelector('a[href*="goodsNo"]');
                let productUrl = '';
                let productNo = '';
                if (linkEl) {
                    productUrl = linkEl.href;
                    const match = productUrl.match(/goodsNo=([A-Z0-9]+)/);
                    productNo = match ? match[1] : '';
                }

                // 이미지
                const imgEl = item.querySelector('img');
                let imageUrl = imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '';

                // 평점
                let rating = 0;
                const ratingEl = item.querySelector('.point, .score, .review_point');
                if (ratingEl) {
                    const ratingMatch = ratingEl.textContent.match(/([0-9.]+)/);
                    rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0;
                }

                // 리뷰 수
                let reviewCount = 0;
                const reviewEl = item.querySelector('.review_count, .count, .tx_review');
                if (reviewEl) {
                    const reviewMatch = reviewEl.textContent.match(/([0-9,]+)/);
                    reviewCount = reviewMatch ? parseInt(reviewMatch[1].replace(/,/g, '')) : 0;
                }

                if (name && productNo) {
                    products.push({
                        productNo,
                        name,
                        brand,
                        price,
                        originalPrice,
                        imageUrl,
                        productUrl,
                        rating,
                        reviewCount
                    });
                }
            } catch (e) {}
        });

        return products;
    }''')


def create_table():
    """테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()


def crawl_oliveyoung():
    """올리브영 크롤링"""
    print("=" * 60)
    print("OLIVEYOUNG CATALOG CRAWL")
    print("=" * 60)

    create_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM oliveyoung_catalog')
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

        # 랭킹 페이지 크롤링
        print("Crawling ranking pages...")
        print("-" * 60)

        for i, cat in enumerate(RANKING_URLS, 1):
            try:
                print(f"[{i}/{len(RANKING_URLS)}] {cat['name']}...", end=" ")

                page.goto(cat['url'], wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(3000)

                # 스크롤해서 더 많은 상품 로드
                for _ in range(3):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(1000)

                products = extract_products_from_page(page)

                for prod in products:
                    if prod['productNo'] not in all_products:
                        prod['category'] = cat['name']
                        all_products[prod['productNo']] = prod

                print(f"found {len(products)} (total: {len(all_products)})")

            except Exception as e:
                print(f"ERROR: {str(e)[:40]}")

            time.sleep(1)

        browser.close()

    print()
    print(f"Total unique products: {len(all_products)}")

    # DB 저장
    print()
    print("Saving to database...")

    for prod in all_products.values():
        try:
            cur.execute('SELECT id FROM oliveyoung_catalog WHERE product_no = ?', (prod['productNo'],))
            existing = cur.fetchone()

            if existing:
                cur.execute('''
                    UPDATE oliveyoung_catalog
                    SET name=?, brand=?, price=?, original_price=?, image_url=?,
                        product_url=?, category=?, rating=?, review_count=?,
                        is_sale=?, updated_at=datetime('now')
                    WHERE product_no=?
                ''', (
                    prod['name'], prod['brand'], prod['price'], prod['originalPrice'],
                    prod['imageUrl'], prod['productUrl'], prod['category'],
                    prod['rating'], prod['reviewCount'],
                    1 if prod['originalPrice'] > prod['price'] else 0,
                    prod['productNo']
                ))
                total_updated += 1
            else:
                cur.execute('''
                    INSERT INTO oliveyoung_catalog
                    (product_no, name, brand, price, original_price, image_url,
                     product_url, category, rating, review_count, is_best, is_sale, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, datetime('now'))
                ''', (
                    prod['productNo'], prod['name'], prod['brand'], prod['price'],
                    prod['originalPrice'], prod['imageUrl'], prod['productUrl'],
                    prod['category'], prod['rating'], prod['reviewCount'],
                    1 if prod['originalPrice'] > prod['price'] else 0
                ))
                total_added += 1

        except Exception as e:
            pass

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM oliveyoung_catalog')
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
    crawl_oliveyoung()
