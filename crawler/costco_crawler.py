# -*- coding: utf-8 -*-
"""
코스트코 코리아 카탈로그 크롤러
API를 통한 상품 수집
"""
import requests
import sqlite3
import time
from datetime import datetime

DB_PATH = '../data/products.db'

SEARCH_KEYWORDS = [
    '식품', '과자', '음료', '커피', '라면', '냉동식품',
    '세제', '세탁', '청소', '화장지', '티슈',
    '건강', '비타민', '영양제', '유산균',
    '주방', '냄비', '프라이팬', '식기',
    '수납', '정리함', '바구니',
    '침구', '이불', '베개', '수건',
    '전자', '가전', '배터리',
    '반려동물', '사료', '간식',
]


def create_costco_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS costco_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_no TEXT UNIQUE,
            name TEXT,
            price INTEGER,
            original_price INTEGER,
            image_url TEXT,
            product_url TEXT,
            category TEXT,
            brand TEXT,
            is_online_only INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()


def crawl_costco_search(session, query, limit=48):
    url = "https://www.costco.co.kr/rest/v2/korea/products/search"
    params = {
        "query": query,
        "pageSize": limit,
        "currentPage": 0,
        "sort": "relevance",
        "fields": "FULL",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.costco.co.kr",
        "Referer": "https://www.costco.co.kr/",
    }
    try:
        resp = session.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        products = []
        items = data.get("products", [])
        for item in items:
            price_data = item.get("price", {})
            price = int(price_data.get("value", 0))
            images = item.get("images", [])
            image_url = images[0].get("url", "") if images else ""
            if image_url and not image_url.startswith("http"):
                image_url = "https://www.costco.co.kr" + image_url
            p = {
                "product_no": item.get("code", ""),
                "name": item.get("name", ""),
                "price": price,
                "original_price": price,
                "image_url": image_url,
                "product_url": f"https://www.costco.co.kr/p/{item.get('code', '')}",
                "category": query,
                "brand": item.get("manufacturer", ""),
                "is_online_only": item.get("isOnlineOnly", False),
            }
            if p["product_no"] and p["name"]:
                products.append(p)
        return products
    except Exception as e:
        print(f"  검색 에러 ({query}): {e}")
        return []


def run_costco_catalog_crawl():
    conn = sqlite3.connect(DB_PATH)
    create_costco_table(conn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM costco_catalog")
    before = cur.fetchone()[0]
    print(f"기존 코스트코 카탈로그: {before}개")
    session = requests.Session()
    all_products = []
    print("=== 코스트코 키워드 검색 ===")
    for keyword in SEARCH_KEYWORDS:
        print(f"  {keyword} 검색...")
        products = crawl_costco_search(session, keyword)
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
        cur.execute("SELECT id FROM costco_catalog WHERE product_no = ?", (p["product_no"],))
        if cur.fetchone():
            cur.execute("UPDATE costco_catalog SET name=?, price=?, image_url=?, category=?, updated_at=datetime('now') WHERE product_no=?",
                (p["name"], p["price"], p["image_url"], p["category"], p["product_no"]))
        else:
            cur.execute("INSERT INTO costco_catalog (product_no, name, price, original_price, image_url, product_url, category, brand, is_online_only, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (p["product_no"], p["name"], p["price"], p["original_price"], p["image_url"], p["product_url"], p["category"], p["brand"], 1 if p["is_online_only"] else 0))
            added += 1
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM costco_catalog")
    after = cur.fetchone()[0]
    print(f"신규 추가: {added}개")
    print(f"최종 코스트코 카탈로그: {after}개")
    conn.close()
    return after

if __name__ == "__main__":
    print("=== 코스트코 카탈로그 크롤러 ===")
    run_costco_catalog_crawl()
