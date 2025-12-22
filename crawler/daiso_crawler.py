"""
다이소몰 상품 크롤러
- 전체 상품 카탈로그 수집
- 상품명으로 검색하여 품번 매칭

검색 API: https://www.daisomall.co.kr/ssn/search/SearchGoods
상품 URL: https://www.daisomall.co.kr/pd/pdr/SCR_PDR_0001?pdNo=품번
"""
import json
import time
import re
from typing import Optional
from urllib.parse import quote
import requests
from dataclasses import dataclass, asdict


@dataclass
class DaisoProduct:
    product_no: str  # 품번 (pdNo)
    name: str
    price: int
    image_url: str
    product_url: str
    category: str = ""
    category_large: str = ""
    category_middle: str = ""
    category_small: str = ""
    rating: float = 0.0
    review_count: int = 0
    order_count: int = 0  # 주문 수
    is_new: bool = False
    is_best: bool = False
    sold_out: bool = False

    def to_dict(self):
        return asdict(self)


class DaisoCrawler:
    BASE_URL = "https://www.daisomall.co.kr"
    SEARCH_API_URL = "https://www.daisomall.co.kr/ssn/search/SearchGoods"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.daisomall.co.kr/",
        })

    def search(self, keyword: str, max_results: int = 20, page: int = 1) -> list[DaisoProduct]:
        """키워드로 상품 검색 (API 직접 호출)"""
        products = []

        try:
            params = {
                "searchTerm": keyword,
                "searchQuery": "",
                "pageNum": page,
                "brndCd": "",
                "cntPerPage": min(max_results, 100),  # 최대 100개
                "userId": "",
                "newPdYn": "",
                "massOrPsblYn": "",
                "pkupOrPsblYn": "",
                "fdrmOrPsblYn": "",
                "quickOrPsblYn": "",
                "searchSort": "",
                "isCategory": "1",
            }

            response = self.session.get(self.SEARCH_API_URL, params=params, timeout=15)
            if response.status_code != 200:
                print(f"Search failed: {response.status_code}")
                return []

            data = response.json()

            # API 응답 구조 파싱
            result_set = data.get("resultSet", {})
            results = result_set.get("result", [])

            if len(results) < 2:
                return []

            # 두 번째 result에 실제 상품 데이터가 있음
            product_result = results[1]
            result_documents = product_result.get("resultDocuments", [])

            for doc in result_documents[:max_results]:
                try:
                    product_no = doc.get("pdNo", "")
                    name = doc.get("pdNm", "") or doc.get("exhPdNm", "")
                    price = int(doc.get("pdPrc", 0))

                    # 이미지 URL
                    img_path = doc.get("pdImgUrl", "")
                    image_url = f"{self.BASE_URL}{img_path}" if img_path else ""

                    # 카테고리
                    category_large = doc.get("exhLargeCtgrNm", "")
                    category_middle = doc.get("exhMiddleCtgrNm", "")
                    category_small = doc.get("exhSmallCtgrNm", "")
                    category = f"{category_large} > {category_middle} > {category_small}"

                    # 평점 및 리뷰
                    rating = float(doc.get("avgStscVal", 0) or 0)
                    review_count = int(doc.get("revwCnt", 0) or 0)
                    order_count = int(doc.get("totOrQy", 0) or 0)

                    # 플래그
                    is_new = doc.get("newPdYn", "") == "Y"
                    is_best = doc.get("BESTYN", "") == "Y"
                    sold_out = doc.get("soldOutYn", "") == "Y"

                    if product_no and name:
                        products.append(DaisoProduct(
                            product_no=product_no,
                            name=name,
                            price=price,
                            image_url=image_url,
                            product_url=f"{self.BASE_URL}/pd/pdr/SCR_PDR_0001?pdNo={product_no}",
                            category=category,
                            category_large=category_large,
                            category_middle=category_middle,
                            category_small=category_small,
                            rating=rating,
                            review_count=review_count,
                            order_count=order_count,
                            is_new=is_new,
                            is_best=is_best,
                            sold_out=sold_out,
                        ))

                except Exception as e:
                    continue

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"Search error: {e}")

        return products

    def search_all(self, keyword: str, max_pages: int = 5) -> list[DaisoProduct]:
        """여러 페이지에 걸쳐 검색 (페이지네이션)"""
        all_products = []
        seen_ids = set()

        for page in range(1, max_pages + 1):
            products = self.search(keyword, max_results=100, page=page)

            if not products:
                break

            for p in products:
                if p.product_no not in seen_ids:
                    seen_ids.add(p.product_no)
                    all_products.append(p)

            time.sleep(0.5)

        return all_products

    def crawl_popular_keywords(self, keywords: list[str] = None) -> list[DaisoProduct]:
        """인기 키워드로 상품 수집"""
        if keywords is None:
            keywords = [
                # 주방용품
                "배수구망", "수세미", "주방장갑", "실리콘 주걱", "키친타월",
                "밀폐용기", "쟁반", "도마", "가위", "국자",
                # 수납정리
                "수납함", "정리함", "바구니", "서랍정리", "옷걸이",
                "압축팩", "진공팩", "리빙박스", "칸막이", "파일박스",
                # 청소용품
                "청소솔", "빗자루", "먼지털이", "걸레", "청소용품",
                "락스", "세제", "탈취제", "방향제", "물티슈",
                # 욕실용품
                "칫솔꽂이", "비누받침", "샤워기", "수건걸이", "욕실용품",
                "치약", "면봉", "화장솜", "세안제", "샴푸",
                # 문구/생활
                "테이프", "가위", "포장지", "볼펜", "노트",
                "충전기", "케이블", "이어폰", "보조배터리", "거울",
            ]

        all_products = []
        seen_ids = set()

        for keyword in keywords:
            try:
                print(f"Crawling: {keyword}...")
            except UnicodeEncodeError:
                print(f"Crawling keyword...")

            products = self.search_all(keyword, max_pages=3)

            for p in products:
                if p.product_no not in seen_ids:
                    seen_ids.add(p.product_no)
                    all_products.append(p)

            time.sleep(1)  # Rate limiting between keywords

        return all_products

    def save_to_database(self, products: list[DaisoProduct]) -> int:
        """크롤링한 상품을 DB에 저장"""
        from database import Database

        db = Database()
        saved_count = 0

        for p in products:
            if db.insert_daiso_product(p.to_dict()):
                saved_count += 1

        db.close()
        return saved_count

    def get_product_detail(self, product_no: str) -> Optional[DaisoProduct]:
        """상품 상세 정보 조회"""
        try:
            url = f"{self.BASE_URL}/pd/pdr/SCR_PDR_0001?pdNo={product_no}"
            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # 상품명
            name_elem = soup.select_one("h1, .product-name, .pdName")
            name = name_elem.get_text(strip=True) if name_elem else ""

            # 가격
            price_elem = soup.select_one(".price, .pdPrice")
            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price = int(re.sub(r"[^\d]", "", price_text) or 0)

            # 이미지
            img_elem = soup.select_one(".product-image img, .pdImg img")
            img_url = img_elem.get("src", "") if img_elem else ""

            time.sleep(0.5)

            return DaisoProduct(
                product_no=product_no,
                name=name,
                price=price,
                image_url=img_url,
                product_url=url,
            )

        except Exception as e:
            print(f"Detail error: {e}")
            return None

    def search_and_match(self, query: str, threshold: float = 0.5) -> Optional[DaisoProduct]:
        """
        유튜브에서 추출한 상품명으로 다이소몰 검색 후 최적 매칭
        """
        # 검색어 정제
        clean_query = re.sub(r"[^\w\s가-힣]", "", query).strip()
        if len(clean_query) < 2:
            return None

        products = self.search(clean_query, max_results=10)

        if not products:
            # 검색어 단순화하여 재시도
            words = clean_query.split()
            if len(words) > 1:
                products = self.search(words[0], max_results=10)

        if not products:
            return None

        # 유사도 기반 매칭
        best_match = None
        best_score = 0

        for product in products:
            score = self._similarity(clean_query.lower(), product.name.lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = product

        return best_match

    def _similarity(self, s1: str, s2: str) -> float:
        """간단한 유사도 계산"""
        # 단어 기반 Jaccard 유사도
        words1 = set(s1.split())
        words2 = set(s2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        jaccard = len(intersection) / len(union)

        # 포함 관계 보너스
        if s1 in s2 or s2 in s1:
            jaccard = max(jaccard, 0.7)

        return jaccard


def test_search():
    """테스트"""
    crawler = DaisoCrawler()

    test_keywords = [
        "배수구망",
        "수납정리함",
        "키친타월",
        "실리콘 주걱",
    ]

    for keyword in test_keywords:
        print(f"\n=== Searching: {keyword} ===")
        products = crawler.search(keyword, max_results=5)

        if not products:
            print("  No results found")
            continue

        for p in products:
            # Windows 콘솔 인코딩 문제 방지
            try:
                print(f"  [{p.product_no}] {p.name}")
                print(f"    Price: {p.price}won, Rating: {p.rating}, Reviews: {p.review_count}, Orders: {p.order_count}")
                print(f"    Category: {p.category}")
                if p.is_best:
                    print(f"    ** BEST **")
                if p.is_new:
                    print(f"    ** NEW **")
            except UnicodeEncodeError:
                print(f"  [{p.product_no}] (name encoding error)")

        print(f"  Total: {len(products)} products found")


def test_match():
    """유튜브 상품명 매칭 테스트"""
    crawler = DaisoCrawler()

    # 유튜브에서 언급될 수 있는 상품명 예시
    youtube_mentions = [
        "스텐 배수구망",
        "실리콘 주방장갑",
        "다용도 정리함",
        "미니 빗자루",
    ]

    print("\n=== YouTube Product Matching Test ===")
    for mention in youtube_mentions:
        result = crawler.search_and_match(mention)
        if result:
            try:
                print(f"\n'{mention}' -> Matched!")
                print(f"  Product: {result.name}")
                print(f"  Code: {result.product_no}")
                print(f"  Price: {result.price}won")
            except UnicodeEncodeError:
                print(f"\n'{mention}' -> Matched (encoding error)")
        else:
            print(f"\n'{mention}' -> No match")


if __name__ == "__main__":
    print("=== Daiso Mall Crawler Test ===")
    test_search()
    test_match()
