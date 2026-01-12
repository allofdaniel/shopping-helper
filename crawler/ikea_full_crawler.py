# -*- coding: utf-8 -*-
"""
IKEA Korea 전체 카탈로그 크롤러
- 모든 카테고리에서 상품 수집
- Playwright로 정확한 데이터 추출
"""
import sqlite3
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

DB_PATH = '../data/products.db'

# IKEA Korea 전체 카테고리 (실제 카테고리 URL에서 추출)
IKEA_CATEGORIES = [
    # 가구
    {"name": "소파", "url": "https://www.ikea.com/kr/ko/cat/sofas-fu003/"},
    {"name": "침대", "url": "https://www.ikea.com/kr/ko/cat/beds-bm003/"},
    {"name": "매트리스", "url": "https://www.ikea.com/kr/ko/cat/mattresses-bm002/"},
    {"name": "옷장", "url": "https://www.ikea.com/kr/ko/cat/wardrobes-19053/"},
    {"name": "서랍장", "url": "https://www.ikea.com/kr/ko/cat/chest-of-drawers-10451/"},
    {"name": "책상", "url": "https://www.ikea.com/kr/ko/cat/desks-computer-desks-20649/"},
    {"name": "의자", "url": "https://www.ikea.com/kr/ko/cat/chairs-fu002/"},
    {"name": "사무용의자", "url": "https://www.ikea.com/kr/ko/cat/office-chairs-20652/"},
    {"name": "책장", "url": "https://www.ikea.com/kr/ko/cat/bookcases-shelving-units-st002/"},
    {"name": "선반", "url": "https://www.ikea.com/kr/ko/cat/shelving-units-st001/"},
    {"name": "수납장", "url": "https://www.ikea.com/kr/ko/cat/cabinets-cupboards-st004/"},
    {"name": "TV장식장", "url": "https://www.ikea.com/kr/ko/cat/tv-media-furniture-10475/"},
    {"name": "식탁", "url": "https://www.ikea.com/kr/ko/cat/dining-tables-21825/"},
    {"name": "식탁의자", "url": "https://www.ikea.com/kr/ko/cat/dining-chairs-25219/"},
    {"name": "거실테이블", "url": "https://www.ikea.com/kr/ko/cat/coffee-side-tables-10705/"},
    # 주방
    {"name": "주방가구", "url": "https://www.ikea.com/kr/ko/cat/kitchen-cabinets-fronts-24254/"},
    {"name": "주방용품", "url": "https://www.ikea.com/kr/ko/cat/kitchen-accessories-ka001/"},
    {"name": "조리도구", "url": "https://www.ikea.com/kr/ko/cat/pots-pans-702865/"},
    {"name": "식기", "url": "https://www.ikea.com/kr/ko/cat/dinnerware-702861/"},
    {"name": "컵/머그", "url": "https://www.ikea.com/kr/ko/cat/cups-mugs-702862/"},
    {"name": "수저/커트러리", "url": "https://www.ikea.com/kr/ko/cat/cutlery-702858/"},
    {"name": "보관용기", "url": "https://www.ikea.com/kr/ko/cat/food-containers-702864/"},
    # 침실/욕실
    {"name": "침구", "url": "https://www.ikea.com/kr/ko/cat/bedding-702897/"},
    {"name": "이불", "url": "https://www.ikea.com/kr/ko/cat/quilts-702895/"},
    {"name": "베개", "url": "https://www.ikea.com/kr/ko/cat/pillows-702893/"},
    {"name": "수건", "url": "https://www.ikea.com/kr/ko/cat/towels-702887/"},
    {"name": "욕실용품", "url": "https://www.ikea.com/kr/ko/cat/bathroom-accessories-702881/"},
    {"name": "거울", "url": "https://www.ikea.com/kr/ko/cat/mirrors-702880/"},
    # 조명
    {"name": "천장조명", "url": "https://www.ikea.com/kr/ko/cat/ceiling-lights-702873/"},
    {"name": "플로어스탠드", "url": "https://www.ikea.com/kr/ko/cat/floor-lamps-702871/"},
    {"name": "테이블조명", "url": "https://www.ikea.com/kr/ko/cat/table-lamps-702870/"},
    {"name": "벽조명", "url": "https://www.ikea.com/kr/ko/cat/wall-lights-702869/"},
    {"name": "LED조명", "url": "https://www.ikea.com/kr/ko/cat/led-light-bulbs-702866/"},
    # 장식
    {"name": "화분/식물", "url": "https://www.ikea.com/kr/ko/cat/plants-pots-stands-702839/"},
    {"name": "캔들/향초", "url": "https://www.ikea.com/kr/ko/cat/candles-702837/"},
    {"name": "액자/그림", "url": "https://www.ikea.com/kr/ko/cat/frames-702831/"},
    {"name": "시계", "url": "https://www.ikea.com/kr/ko/cat/clocks-702829/"},
    {"name": "러그", "url": "https://www.ikea.com/kr/ko/cat/rugs-702817/"},
    {"name": "커튼", "url": "https://www.ikea.com/kr/ko/cat/curtains-702815/"},
    {"name": "쿠션", "url": "https://www.ikea.com/kr/ko/cat/cushions-702812/"},
    {"name": "담요", "url": "https://www.ikea.com/kr/ko/cat/blankets-702810/"},
    # 수납/정리
    {"name": "수납박스", "url": "https://www.ikea.com/kr/ko/cat/storage-boxes-baskets-702852/"},
    {"name": "옷걸이/행거", "url": "https://www.ikea.com/kr/ko/cat/clothes-hangers-702848/"},
    {"name": "신발장", "url": "https://www.ikea.com/kr/ko/cat/shoe-storage-702846/"},
    # 아이방
    {"name": "아이침대", "url": "https://www.ikea.com/kr/ko/cat/childrens-beds-702799/"},
    {"name": "아이책상", "url": "https://www.ikea.com/kr/ko/cat/childrens-desks-24714/"},
    {"name": "아이수납", "url": "https://www.ikea.com/kr/ko/cat/childrens-storage-702797/"},
    {"name": "아이장난감", "url": "https://www.ikea.com/kr/ko/cat/toys-702791/"},
    # 야외
    {"name": "야외가구", "url": "https://www.ikea.com/kr/ko/cat/outdoor-furniture-700384/"},
    {"name": "야외테이블", "url": "https://www.ikea.com/kr/ko/cat/outdoor-dining-tables-702783/"},
    {"name": "야외의자", "url": "https://www.ikea.com/kr/ko/cat/outdoor-chairs-702781/"},
]


def extract_products_from_list(page):
    """상품 목록 페이지에서 상품 정보 추출"""
    return page.evaluate('''() => {
        const products = [];
        const items = document.querySelectorAll('[data-testid="plp-product-card"], .plp-fragment-wrapper, .pip-product-compact');

        items.forEach(item => {
            try {
                // 상품 링크 찾기
                const link = item.querySelector('a[href*="/p/"]');
                if (!link) return;

                const productUrl = link.href;
                const urlMatch = productUrl.match(/-[s]?(\\d+)\\/?$/);
                const productNo = urlMatch ? urlMatch[1] : '';
                if (!productNo) return;

                // 상품명
                const nameEl = item.querySelector('.pip-header-section__title--small, .pip-header-section h3, [class*="product-compact__name"]');
                const name = nameEl ? nameEl.textContent.trim() : '';

                // 가격
                const priceEl = item.querySelector('[class*="price__integer"], .pip-temp-price__integer, .pip-price__integer');
                let price = 0;
                if (priceEl) {
                    const priceText = priceEl.textContent.replace(/[^0-9]/g, '');
                    price = parseInt(priceText) || 0;
                }

                // 이미지
                const imgEl = item.querySelector('img[src*="ikea"]');
                const imageUrl = imgEl ? imgEl.src : '';

                if (productNo && price > 0) {
                    products.push({
                        productNo,
                        name,
                        price,
                        imageUrl,
                        productUrl
                    });
                }
            } catch (e) {}
        });

        return products;
    }''')


def extract_product_detail(page):
    """상품 상세페이지에서 정확한 데이터 추출"""
    return page.evaluate('''() => {
        const fullName = document.title.replace(' - IKEA', '').trim();
        const h1 = document.querySelector('h1');
        const brandName = h1?.firstChild?.textContent?.trim() || '';

        let price = 0;
        const priceMatch = document.body.innerText.match(/￦\\s*([\\d,]+)/);
        if (priceMatch) price = parseInt(priceMatch[1].replace(/,/g, ''));

        const ratingSpan = document.querySelector('[aria-label*="별점"]');
        const ariaLabel = ratingSpan?.getAttribute('aria-label') || '';
        const ratingMatch = ariaLabel.match(/([\\d.]+)\\s*\\/\\s*5/);
        const reviewMatch = ariaLabel.match(/리뷰:\\s*(\\d+)/);
        const rating = ratingMatch ? parseFloat(ratingMatch[1]) : null;
        const reviewCount = reviewMatch ? parseInt(reviewMatch[1]) : 0;

        const urlMatch = window.location.href.match(/-[s]?(\\d+)\\/?$/);
        const productNo = urlMatch ? urlMatch[1] : '';

        const brandFirst = brandName.split('/')[0].trim().split(' ')[0];
        const productImg = document.querySelector('img[alt*="' + brandFirst + '"]');
        const imageUrl = productImg?.src || '';

        const breadcrumbNav = document.querySelector('nav[aria-label="Breadcrumb"]');
        const breadcrumbLinks = breadcrumbNav?.querySelectorAll('a') || [];
        const categories = Array.from(breadcrumbLinks).map(a => a.textContent?.trim()).filter(Boolean);
        const category = categories.length > 2 ? categories[categories.length - 2] : (categories[1] || '');

        return {
            productNo,
            fullName,
            brandName,
            price,
            rating,
            reviewCount,
            imageUrl,
            category,
            productUrl: window.location.href
        };
    }''')


def create_table():
    """테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS ikea_catalog (
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
    conn.commit()
    conn.close()


def crawl_ikea_full():
    """IKEA 전체 카탈로그 크롤링"""
    print("=" * 60)
    print("IKEA FULL CATALOG CRAWL")
    print("=" * 60)

    create_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM ikea_catalog')
    before_count = cur.fetchone()[0]
    print(f"Existing products: {before_count}")
    print()

    total_added = 0
    total_updated = 0
    total_errors = 0
    all_products = {}  # product_no -> product data

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='ko-KR'
        )
        page = context.new_page()

        # 1단계: 모든 카테고리에서 상품 목록 수집
        print("Step 1: Collecting product URLs from categories...")
        print("-" * 60)

        for i, cat in enumerate(IKEA_CATEGORIES, 1):
            try:
                print(f"[{i}/{len(IKEA_CATEGORIES)}] {cat['name']}...", end=" ")

                page.goto(cat['url'], wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)

                # 스크롤해서 더 많은 상품 로드
                for _ in range(3):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(1000)

                products = extract_products_from_list(page)

                for prod in products:
                    if prod['productNo'] not in all_products:
                        prod['category'] = cat['name']
                        all_products[prod['productNo']] = prod

                print(f"found {len(products)} products (total unique: {len(all_products)})")

            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                total_errors += 1

            time.sleep(0.5)

        print()
        print(f"Total unique products found: {len(all_products)}")
        print()

        # 2단계: 각 상품 상세페이지 방문하여 정확한 데이터 수집
        print("Step 2: Fetching product details...")
        print("-" * 60)

        product_list = list(all_products.values())

        for i, prod in enumerate(product_list, 1):
            try:
                if i % 10 == 0 or i == 1:
                    print(f"[{i}/{len(product_list)}] Processing...")

                page.goto(prod['productUrl'], wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(1500)

                detail = extract_product_detail(page)

                if detail and detail['price'] > 0:
                    # DB에 저장
                    cur.execute('SELECT id FROM ikea_catalog WHERE product_no = ?', (detail['productNo'],))
                    existing = cur.fetchone()

                    if existing:
                        cur.execute('''
                            UPDATE ikea_catalog
                            SET name=?, name_ko=?, price=?, image_url=?, product_url=?,
                                category=?, rating=?, review_count=?, updated_at=datetime('now')
                            WHERE product_no=?
                        ''', (
                            detail['brandName'], detail['fullName'], detail['price'],
                            detail['imageUrl'], detail['productUrl'],
                            detail['category'] or prod['category'],
                            detail['rating'], detail['reviewCount'],
                            detail['productNo']
                        ))
                        total_updated += 1
                    else:
                        cur.execute('''
                            INSERT INTO ikea_catalog
                            (product_no, name, name_ko, price, image_url, product_url,
                             category, rating, review_count, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        ''', (
                            detail['productNo'], detail['brandName'], detail['fullName'],
                            detail['price'], detail['imageUrl'], detail['productUrl'],
                            detail['category'] or prod['category'],
                            detail['rating'], detail['reviewCount']
                        ))
                        total_added += 1

                    if i % 50 == 0:
                        conn.commit()

            except Exception as e:
                total_errors += 1

            time.sleep(0.3)

        conn.commit()
        browser.close()

    # 최종 통계
    cur.execute('SELECT COUNT(*) FROM ikea_catalog')
    after_count = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE rating IS NOT NULL')
    with_rating = cur.fetchone()[0]

    cur.execute('SELECT COUNT(DISTINCT category) FROM ikea_catalog')
    cat_count = cur.fetchone()[0]

    print()
    print("=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)
    print(f"Added: {total_added}")
    print(f"Updated: {total_updated}")
    print(f"Errors: {total_errors}")
    print(f"Total products: {after_count}")
    print(f"With rating: {with_rating}")
    print(f"Categories: {cat_count}")

    conn.close()

    return {
        'added': total_added,
        'updated': total_updated,
        'errors': total_errors,
        'total': after_count
    }


if __name__ == '__main__':
    crawl_ikea_full()
