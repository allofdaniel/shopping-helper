# -*- coding: utf-8 -*-
"""
편의점 전체 카탈로그 크롤러
- CU, GS25, 이마트24 상품 수집
- Playwright로 웹 페이지 크롤링
"""
import sqlite3
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

DB_PATH = '../data/products.db'

# CU 카테고리 (BGF Retail)
CU_CATEGORIES = [
    {"name": "도시락/김밥", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=4&depth3=1"},
    {"name": "샌드위치/햄버거", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=4&depth3=2"},
    {"name": "주먹밥/즉석밥", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=4&depth3=3"},
    {"name": "베이커리", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=5&depth3="},
    {"name": "라면/즉석", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=6&depth3="},
    {"name": "음료", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=7&depth3="},
    {"name": "과자/간식", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=8&depth3="},
    {"name": "아이스크림", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=9&depth3="},
    {"name": "유제품", "url": "https://cu.bgfretail.com/product/product.do?category=product&depth2=10&depth3="},
]

# CU 행사 페이지
CU_EVENTS = [
    {"name": "1+1", "url": "https://cu.bgfretail.com/event/plus.do?category=event&depth2=1&depth3="},
    {"name": "2+1", "url": "https://cu.bgfretail.com/event/plus.do?category=event&depth2=2&depth3="},
]

# GS25 카테고리
GS25_CATEGORIES = [
    {"name": "간편식사", "url": "https://gs25.gsretail.com/gscvs/ko/products/youus-freshfood"},
    {"name": "즉석조리", "url": "https://gs25.gsretail.com/gscvs/ko/products/youus-different-service"},
    {"name": "과자/빵", "url": "https://gs25.gsretail.com/gscvs/ko/products/youus-bread-snack"},
    {"name": "음료", "url": "https://gs25.gsretail.com/gscvs/ko/products/youus-drink"},
    {"name": "아이스크림", "url": "https://gs25.gsretail.com/gscvs/ko/products/youus-ice-cream"},
]

# GS25 행사
GS25_EVENTS = [
    {"name": "1+1", "url": "https://gs25.gsretail.com/gscvs/ko/products/event-goods-1plus1"},
    {"name": "2+1", "url": "https://gs25.gsretail.com/gscvs/ko/products/event-goods-2plus1"},
]


def extract_cu_products(page):
    """CU 페이지에서 상품 추출"""
    return page.evaluate('''() => {
        const products = [];

        // 상품 리스트
        const items = document.querySelectorAll('.prod_list li, .prod_wrap .prod_item, .prodListWrap li');

        items.forEach(item => {
            try {
                // 상품명
                const nameEl = item.querySelector('.name, .prod_name, .tit');
                const name = nameEl ? nameEl.textContent.trim() : '';

                // 가격
                let price = 0;
                const priceEl = item.querySelector('.price, .cost');
                if (priceEl) {
                    const priceText = priceEl.textContent.replace(/[^0-9]/g, '');
                    price = parseInt(priceText) || 0;
                }

                // 이미지
                const imgEl = item.querySelector('img');
                let imageUrl = '';
                if (imgEl) {
                    imageUrl = imgEl.src || imgEl.getAttribute('data-src') || '';
                }

                // 링크
                const linkEl = item.querySelector('a');
                let productUrl = linkEl ? linkEl.href : '';

                // 상품코드 (URL에서 추출)
                let productCode = '';
                if (productUrl) {
                    const match = productUrl.match(/goodsCode=([^&]+)/);
                    productCode = match ? match[1] : 'cu_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
                }

                // 행사 타입
                let eventType = null;
                const flagEl = item.querySelector('.badge, .flag, .event_tag');
                if (flagEl) {
                    const flagText = flagEl.textContent.trim();
                    if (flagText.includes('1+1')) eventType = '1+1';
                    else if (flagText.includes('2+1')) eventType = '2+1';
                    else if (flagText.includes('덤')) eventType = '덤증정';
                }

                // PB 여부
                const isPb = item.classList.contains('pb') ||
                             item.querySelector('.pb') !== null ||
                             (name && (name.includes('HEYROO') || name.includes('GET')));

                if (name && name.length > 1) {
                    products.push({
                        productCode: productCode || 'cu_' + Date.now(),
                        name,
                        price,
                        imageUrl,
                        productUrl,
                        eventType,
                        isPb
                    });
                }
            } catch (e) {}
        });

        return products;
    }''')


def extract_gs25_products(page):
    """GS25 페이지에서 상품 추출"""
    return page.evaluate('''() => {
        const products = [];

        // 상품 리스트
        const items = document.querySelectorAll('.prod_box, .prod_item, .prodListWrap li');

        items.forEach(item => {
            try {
                // 상품명
                const nameEl = item.querySelector('.tit, .name, .prd_name');
                const name = nameEl ? nameEl.textContent.trim() : '';

                // 가격
                let price = 0;
                const priceEl = item.querySelector('.cost, .price');
                if (priceEl) {
                    const priceText = priceEl.textContent.replace(/[^0-9]/g, '');
                    price = parseInt(priceText) || 0;
                }

                // 이미지
                const imgEl = item.querySelector('img');
                let imageUrl = '';
                if (imgEl) {
                    imageUrl = imgEl.src || imgEl.getAttribute('data-src') || '';
                }

                // 행사 타입
                let eventType = null;
                const flagEl = item.querySelector('.flag, .badge');
                if (flagEl) {
                    const flagText = flagEl.textContent.trim();
                    if (flagText.includes('1+1')) eventType = '1+1';
                    else if (flagText.includes('2+1')) eventType = '2+1';
                }

                if (name && name.length > 1) {
                    products.push({
                        productCode: 'gs_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
                        name,
                        price,
                        imageUrl,
                        productUrl: '',
                        eventType,
                        isPb: false
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
        CREATE TABLE IF NOT EXISTS convenience_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE,
            name TEXT,
            price INTEGER,
            image_url TEXT,
            product_url TEXT,
            store TEXT,
            category TEXT,
            event_type TEXT,
            is_pb INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


def crawl_convenience():
    """편의점 크롤링"""
    print("=" * 60)
    print("CONVENIENCE STORE CATALOG CRAWL")
    print("=" * 60)

    create_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM convenience_catalog')
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

        # CU 크롤링
        print("Crawling CU...")
        print("-" * 60)

        for i, cat in enumerate(CU_CATEGORIES + CU_EVENTS, 1):
            try:
                print(f"[CU {i}/{len(CU_CATEGORIES) + len(CU_EVENTS)}] {cat['name']}...", end=" ")

                page.goto(cat['url'], wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(3000)

                # 스크롤
                for _ in range(3):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(1000)

                # 더보기 버튼 클릭 시도
                try:
                    more_btn = page.locator('.more_btn, .btn_more, [class*="more"]').first
                    if more_btn.is_visible():
                        for _ in range(3):
                            more_btn.click()
                            page.wait_for_timeout(1500)
                except Exception:
                    pass  # 더보기 버튼이 없거나 클릭 불가한 경우 무시

                products = extract_cu_products(page)

                for prod in products:
                    key = f"cu_{prod['productCode']}"
                    if key not in all_products:
                        prod['store'] = 'CU'
                        prod['category'] = cat['name']
                        all_products[key] = prod

                print(f"found {len(products)} (total: {len(all_products)})")

            except Exception as e:
                print(f"ERROR: {str(e)[:40]}")

            time.sleep(1)

        # GS25 크롤링
        print()
        print("Crawling GS25...")
        print("-" * 60)

        for i, cat in enumerate(GS25_CATEGORIES + GS25_EVENTS, 1):
            try:
                print(f"[GS25 {i}/{len(GS25_CATEGORIES) + len(GS25_EVENTS)}] {cat['name']}...", end=" ")

                page.goto(cat['url'], wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(3000)

                # 스크롤
                for _ in range(5):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(1000)

                products = extract_gs25_products(page)

                for prod in products:
                    key = f"gs_{prod['productCode']}"
                    if key not in all_products:
                        prod['store'] = 'GS25'
                        prod['category'] = cat['name']
                        all_products[key] = prod

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
            cur.execute('SELECT id FROM convenience_catalog WHERE product_code = ?', (prod['productCode'],))
            existing = cur.fetchone()

            if existing:
                cur.execute('''
                    UPDATE convenience_catalog
                    SET name=?, price=?, image_url=?, product_url=?, store=?,
                        category=?, event_type=?, is_pb=?, updated_at=datetime('now')
                    WHERE product_code=?
                ''', (
                    prod['name'], prod['price'], prod['imageUrl'], prod['productUrl'],
                    prod['store'], prod['category'], prod.get('eventType'),
                    1 if prod.get('isPb') else 0,
                    prod['productCode']
                ))
                total_updated += 1
            else:
                cur.execute('''
                    INSERT INTO convenience_catalog
                    (product_code, name, price, image_url, product_url, store,
                     category, event_type, is_pb, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    prod['productCode'], prod['name'], prod['price'], prod['imageUrl'],
                    prod['productUrl'], prod['store'], prod['category'],
                    prod.get('eventType'), 1 if prod.get('isPb') else 0
                ))
                total_added += 1

        except Exception as e:
            print(f"  DB Error: {e}")

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM convenience_catalog')
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
    crawl_convenience()
