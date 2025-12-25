# -*- coding: utf-8 -*-
"""
이케아 코리아 카탈로그 크롤러
API를 통한 상품 수집
"""
import requests
import sqlite3
import time
from datetime import datetime

DB_PATH = '../data/products.db'

CATEGORIES = [
    ('10364', '침대'),
    ('10368', '옷장/수납'),
    ('10382', '책상/테이블'),
    ('10412', '의자'),
    ('10454', '소파'),
    ('10471', '선반'),
    ('10508', '침구'),
    ('10550', '조명'),
    ('10563', '러그'),
    ('10586', '커튼'),
    ('10636', '욕실'),
    ('10676', '주방'),
    ('10732', '식기'),
    ('10759', '조리도구'),
    ('10810', '수납용품'),
    ('10848', '장식소품'),
    ('10862', '화분'),
    ('10920', '사무용품'),
]

SEARCH_KEYWORDS = [
    '수납', '정리함', '서랍', '선반', '행거',
    '침대', '매트리스', '베개', '이불',
    '책상', '의자', '테이블',
    '조명', '스탠드', '러그', '쿠션',
    '주방', '접시', '컵', '그릇',
    '욕실', '수건', '거울',
]


def create_ikea_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ikea_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_no TEXT UNIQUE,
            name TEXT,
            name_ko TEXT,
            price INTEGER,
            image_url TEXT,
            product_url TEXT,
            category TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()


def crawl_ikea_search(session, query, limit=50):
    url = "https://sik.search.blue.cdtapps.com/kr/ko/search-result-page"
    params = {"q": query, "size": limit, "store": "482", "c": "sr"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.ikea.com",
        "Referer": "https://www.ikea.com/kr/ko/",
    }
    try:
        resp = session.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        products = []
        items = data.get("searchResultPage", {}).get("products", {}).get("main", {}).get("items", [])
        for item in items:
            product = item.get("product", {})
            if not product:
                continue
            price_info = product.get("priceNumeral", 0)
            p = {
                "product_no": product.get("id", ""),
                "name": product.get("name", ""),
                "name_ko": product.get("typeName", "") or product.get("name", ""),
                "price": int(price_info) if price_info else 0,
                "image_url": product.get("mainImageUrl", ""),
                "product_url": product.get("pipUrl", ""),
                "category": query,
            }
            if p["product_no"] and p["name"]:
                products.append(p)
        return products
    except Exception as e:
        print(f"  검색 에러 ({query}): {e}")
        return []


def run_ikea_catalog_crawl():
    conn = sqlite3.connect(DB_PATH)
    create_ikea_table(conn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ikea_catalog")
    before = cur.fetchone()[0]
    print(f"기존 이케아 카탈로그: {before}개")
    session = requests.Session()
    all_products = []
    print("=== 이케아 키워드 검색 ===")
    for keyword in SEARCH_KEYWORDS:
        print(f"  {keyword} 검색...")
        products = crawl_ikea_search(session, keyword)
        all_products.extend(products)
        print(f"    -> {len(products)}개")
        time.sleep(0.5)
    seen = set()
    unique = []
    for p in all_products:
        if p["product_no"] not in seen:
            seen.add(p["product_no"])
            unique.append(p)
    print(f"총 수집: {len(all_products)}개 -> 중복제거: {len(unique)}개")
    added = 0
    for p in unique:
        cur.execute("SELECT id FROM ikea_catalog WHERE product_no = ?", (p["product_no"],))
        if cur.fetchone():
            cur.execute("UPDATE ikea_catalog SET name=?, price=?, image_url=?, category=?, updated_at=datetime('now') WHERE product_no=?",
                (p["name"], p["price"], p["image_url"], p["category"], p["product_no"]))
        else:
            cur.execute("INSERT INTO ikea_catalog (product_no, name, name_ko, price, image_url, product_url, category, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (p["product_no"], p["name"], p["name_ko"], p["price"], p["image_url"], p["product_url"], p["category"]))
            added += 1
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM ikea_catalog")
    after = cur.fetchone()[0]
    print(f"신규 추가: {added}개")
    print(f"최종 이케아 카탈로그: {after}개")
    conn.close()
    return after

if __name__ == "__main__":
    print("=== 이케아 카탈로그 크롤러 ===")
    run_ikea_catalog_crawl()
