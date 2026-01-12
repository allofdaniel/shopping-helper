# -*- coding: utf-8 -*-
"""
IKEA 상품 상세페이지 크롤러
- Playwright를 사용하여 각 상품 페이지에서 정확한 데이터 추출
- 한글 상품명, 이미지 URL, 카테고리, 평점, 리뷰 수 수집
"""
import sqlite3
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

# DB 경로 설정
DB_PATH = '../data/products.db'


def extract_product_data(page):
    """상품 상세페이지에서 데이터 추출"""
    return page.evaluate('''() => {
        // 1. 상품명 (페이지 타이틀에서)
        const fullName = document.title.replace(' - IKEA', '').trim();

        // 2. 브랜드명 (H1에서)
        const h1 = document.querySelector('h1');
        const brandName = h1?.firstChild?.textContent?.trim() || '';

        // 3. 가격
        let price = 0;
        const priceMatch = document.body.innerText.match(/￦\\s*([\\d,]+)/);
        if (priceMatch) price = parseInt(priceMatch[1].replace(/,/g, ''));

        // 4. 평점 & 리뷰 (aria-label에서)
        const ratingSpan = document.querySelector('[aria-label*="별점"]');
        const ariaLabel = ratingSpan?.getAttribute('aria-label') || '';
        const ratingMatch = ariaLabel.match(/([\\d.]+)\\s*\\/\\s*5/);
        const reviewMatch = ariaLabel.match(/리뷰:\\s*(\\d+)/);
        const rating = ratingMatch ? parseFloat(ratingMatch[1]) : null;
        const reviewCount = reviewMatch ? parseInt(reviewMatch[1]) : 0;

        // 5. 제품 번호 (URL에서)
        const urlMatch = window.location.href.match(/-[s]?(\\d+)\\/?$/);
        const productNo = urlMatch ? urlMatch[1] : '';

        // 6. 이미지 URL
        const brandFirst = brandName.split('/')[0].trim().split(' ')[0];
        const productImg = document.querySelector(`img[alt*="${brandFirst}"]`);
        const imageUrl = productImg?.src || '';

        // 7. 카테고리
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


def crawl_ikea_details():
    """IKEA 상품 상세페이지 크롤링"""
    print("=== IKEA 상세페이지 크롤링 시작 ===\n")

    # DB에서 상품 URL 목록 가져오기
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT product_no, product_url FROM ikea_catalog WHERE product_url IS NOT NULL AND product_url != ""')
    products = cur.fetchall()

    print(f"크롤링할 상품: {len(products)}개\n")

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
                print(f"[{i}/{len(products)}] {product_url[:60]}...")

                # 페이지 로드
                page.goto(product_url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)  # 동적 콘텐츠 로드 대기

                # 데이터 추출
                data = extract_product_data(page)

                if data and data['price'] > 0:
                    # DB 업데이트
                    cur.execute('''
                        UPDATE ikea_catalog
                        SET name=?, name_ko=?, price=?, image_url=?, category=?,
                            rating=?, review_count=?, updated_at=datetime('now')
                        WHERE product_no=?
                    ''', (
                        data['brandName'],
                        data['fullName'],
                        data['price'],
                        data['imageUrl'],
                        data['category'],
                        data['rating'],
                        data['reviewCount'],
                        product_no
                    ))
                    conn.commit()
                    updated += 1
                    print(f"  [OK] {data['fullName'][:40]} - {data['price']:,}won (rating: {data['rating']}, reviews: {data['reviewCount']})")
                else:
                    print(f"  [FAIL] Data extraction failed")
                    errors += 1

            except Exception as e:
                print(f"  [ERROR] {e}")
                errors += 1

            # API 부하 방지
            time.sleep(1)

        browser.close()

    # 최종 통계
    print(f"\n=== IKEA 크롤링 완료 ===")
    print(f"업데이트: {updated}개")
    print(f"오류: {errors}개")

    # 데이터 품질 확인
    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE image_url IS NOT NULL AND image_url != ""')
    with_image = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE rating IS NOT NULL')
    with_rating = cur.fetchone()[0]

    cur.execute('SELECT COUNT(DISTINCT category) FROM ikea_catalog WHERE category IS NOT NULL AND category != ""')
    category_count = cur.fetchone()[0]

    print(f"\n--- 데이터 품질 ---")
    print(f"이미지 있음: {with_image}개")
    print(f"평점 있음: {with_rating}개")
    print(f"카테고리 수: {category_count}개")

    conn.close()

    return {'updated': updated, 'errors': errors}


if __name__ == '__main__':
    crawl_ikea_details()
