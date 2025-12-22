# -*- coding: utf-8 -*-
"""
다이소몰 크롤러 디버그 테스트
"""
import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.daisomall.co.kr"
SEARCH_URL = "https://www.daisomall.co.kr/ds/dst/SCR_DST_0015"

def test_search():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    keyword = "배수구망"
    params = {"searchTerm": keyword}

    print(f"Searching for: {keyword}")
    print(f"URL: {SEARCH_URL}?searchTerm={keyword}")

    response = session.get(SEARCH_URL, params=params, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Final URL: {response.url}")
    print(f"Content Length: {len(response.text)}")

    # HTML 파싱
    soup = BeautifulSoup(response.text, "html.parser")

    # 상품 링크 찾기
    product_links = soup.select("a[href*='/pd/pdr/SCR_PDR_0001?pdNo=']")
    print(f"Product links found: {len(product_links)}")

    # 처음 5개 상품 정보 출력
    seen = set()
    count = 0
    for link in product_links:
        if count >= 5:
            break

        href = link.get("href", "")
        pd_match = re.search(r"pdNo=([A-Za-z0-9]+)", href)
        if not pd_match:
            continue

        product_no = pd_match.group(1)
        if product_no in seen:
            continue
        seen.add(product_no)

        # 상품명 추출
        img = link.select_one("img")
        name = img.get("alt", "") if img else link.get_text(strip=True)

        print(f"\n[{product_no}] {name}")
        print(f"  href: {href}")
        count += 1

    # HTML 일부 저장 (디버깅용)
    with open("daiso_search_result.html", "w", encoding="utf-8") as f:
        f.write(response.text[:50000])
    print("\nSaved HTML to daiso_search_result.html")

if __name__ == "__main__":
    test_search()
