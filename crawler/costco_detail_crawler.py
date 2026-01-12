# -*- coding: utf-8 -*-
"""
Costco Korea 상세페이지 크롤러
- Playwright로 각 상품 페이지 방문
- 브랜드, 평점, 리뷰 등 상세 정보 추출
"""
import sqlite3
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

DB_PATH = '../data/products.db'


def extract_product_detail(page):
    """상품 상세페이지에서 데이터 추출"""
    return page.evaluate('''() => {
        // 1. 상품명
        const titleEl = document.querySelector('h1.product-name, .product-title h1');
        const productName = titleEl?.textContent?.trim() || '';

        // 2. 브랜드 (상품명에서 추출 또는 별도 요소)
        const brandEl = document.querySelector('.product-brand, .brand-name');
        let brand = brandEl?.textContent?.trim() || '';

        // 브랜드가 없으면 상품명 첫 단어 시도
        if (!brand && productName) {
            const words = productName.split(' ');
            if (words.length > 1) {
                brand = words[0];
            }
        }

        // 3. 가격
        let price = 0;
        const priceEl = document.querySelector('.your-price .price-value, .sales-price');
        if (priceEl) {
            const priceText = priceEl.textContent.replace(/[^0-9]/g, '');
            price = parseInt(priceText) || 0;
        }

        // 4. 원래 가격
        let originalPrice = null;
        const origPriceEl = document.querySelector('.list-price .price-value, .was-price');
        if (origPriceEl) {
            const origText = origPriceEl.textContent.replace(/[^0-9]/g, '');
            const orig = parseInt(origText) || 0;
            if (orig > price) {
                originalPrice = orig;
            }
        }

        // 5. 평점 & 리뷰
        let rating = null;
        let reviewCount = 0;

        // BazaarVoice 리뷰 시스템 확인
        const ratingEl = document.querySelector('.bv_avgRating, .bv-rating-ratio-number');
        if (ratingEl) {
            rating = parseFloat(ratingEl.textContent) || null;
        }

        const reviewCountEl = document.querySelector('.bv_numReviews, .bv-content-pagination-pages-current');
        if (reviewCountEl) {
            const match = reviewCountEl.textContent.match(/\\d+/);
            reviewCount = match ? parseInt(match[0]) : 0;
        }

        // 별 아이콘에서 평점 추출 시도
        if (!rating) {
            const starsEl = document.querySelector('[class*="stars"], [data-bv-rating]');
            if (starsEl) {
                const dataRating = starsEl.getAttribute('data-bv-rating');
                if (dataRating) {
                    rating = parseFloat(dataRating);
                }
            }
        }

        // 6. 이미지 URL
        const imgEl = document.querySelector('.product-image img, .gallery-image img');
        const imageUrl = imgEl?.src || '';

        // 7. 카테고리 (breadcrumb)
        const breadcrumbs = document.querySelectorAll('.breadcrumb a, .breadcrumb-item');
        const categories = Array.from(breadcrumbs).map(el => el.textContent?.trim()).filter(Boolean);
        const category = categories.length > 1 ? categories[categories.length - 1] : '';

        // 8. 제품 번호 (URL에서)
        const urlMatch = window.location.href.match(/\\/p\\/(\\d+)/);
        const productNo = urlMatch ? urlMatch[1] : '';

        return {
            productNo,
            productName,
            brand,
            price,
            originalPrice,
            rating,
            reviewCount,
            imageUrl,
            category,
            productUrl: window.location.href
        };
    }''')


def crawl_costco_details():
    """Costco 상품 상세페이지 크롤링"""
    print("=" * 60)
    print("COSTCO DETAIL PAGE CRAWL")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 평점이 없거나 브랜드가 없는 상품 우선
    cur.execute('''
        SELECT product_no, product_url
        FROM costco_catalog
        WHERE product_url IS NOT NULL
        AND product_url != ''
        AND (rating IS NULL OR brand IS NULL OR brand = '')
        LIMIT 200
    ''')
    products = cur.fetchall()

    if not products:
        # 모든 상품 처리
        cur.execute('''
            SELECT product_no, product_url
            FROM costco_catalog
            WHERE product_url IS NOT NULL AND product_url != ''
        ''')
        products = cur.fetchall()

    print(f"Processing: {len(products)} products\n")

    updated = 0
    errors = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='ko-KR'
        )
        page = context.new_page()

        for i, (product_no, product_url) in enumerate(products, 1):
            try:
                if i % 20 == 0 or i == 1:
                    print(f"[{i}/{len(products)}] Processing...")

                page.goto(product_url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)

                data = extract_product_detail(page)

                if data:
                    # 업데이트할 필드 결정
                    update_fields = []
                    update_values = []

                    if data.get('brand'):
                        update_fields.append('brand=?')
                        update_values.append(data['brand'])

                    if data.get('rating'):
                        update_fields.append('rating=?')
                        update_values.append(data['rating'])

                    if data.get('reviewCount'):
                        update_fields.append('review_count=?')
                        update_values.append(data['reviewCount'])

                    if data.get('imageUrl'):
                        update_fields.append('image_url=?')
                        update_values.append(data['imageUrl'])

                    if update_fields:
                        update_fields.append('updated_at=datetime("now")')
                        update_values.append(product_no)

                        query = f'UPDATE costco_catalog SET {", ".join(update_fields)} WHERE product_no=?'
                        cur.execute(query, tuple(update_values))
                        updated += 1

                if i % 50 == 0:
                    conn.commit()

            except Exception as e:
                errors += 1
                if i % 50 == 0:
                    print(f"  Error at {i}: {str(e)[:50]}")

            time.sleep(0.5)

        conn.commit()
        browser.close()

    # 통계
    cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE brand IS NOT NULL AND brand != ""')
    with_brand = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE rating IS NOT NULL')
    with_rating = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM costco_catalog')
    total = cur.fetchone()[0]

    print()
    print("=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)
    print(f"Updated: {updated}")
    print(f"Errors: {errors}")
    print(f"With brand: {with_brand}/{total} ({100*with_brand/total:.1f}%)")
    print(f"With rating: {with_rating}/{total} ({100*with_rating/total:.1f}%)")

    conn.close()

    return {'updated': updated, 'errors': errors}


if __name__ == '__main__':
    crawl_costco_details()
