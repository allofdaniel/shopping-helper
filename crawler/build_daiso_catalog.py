# -*- coding: utf-8 -*-
"""
다이소몰 상품 카탈로그 구축 스크립트
인기 키워드로 상품을 크롤링하여 DB에 저장합니다.
"""
import sys
import time
from daiso_crawler import DaisoCrawler
from database import Database


# 유튜버들이 자주 추천하는 다이소 상품 카테고리별 키워드
POPULAR_KEYWORDS = [
    # 주방용품
    "배수구망", "수세미", "행주", "실리콘 주걱", "키친타월",
    "밀폐용기", "쟁반", "도마", "가위", "국자", "뒤집개",
    "프라이팬", "냄비", "그릇", "컵", "텀블러", "물병",
    "전자레인지 용기", "싱크대", "식기건조대", "수저통",

    # 수납/정리
    "수납함", "정리함", "바구니", "서랍정리", "옷걸이",
    "압축팩", "진공팩", "리빙박스", "칸막이", "파일박스",
    "다용도함", "소품정리", "화장품정리", "냉장고정리",
    "신발정리", "옷정리", "케이블정리", "책상정리",

    # 청소용품
    "청소솔", "빗자루", "먼지털이", "걸레", "청소용품",
    "락스", "세제", "탈취제", "방향제", "물티슈",
    "창문닦이", "변기솔", "욕실청소", "주방세제",

    # 욕실용품
    "칫솔꽂이", "비누받침", "샤워기", "수건걸이", "욕실용품",
    "치약", "면봉", "화장솜", "세안제", "샴푸", "바디워시",
    "욕실매트", "수건", "목욕타올",

    # 세탁용품
    "빨래바구니", "세탁망", "옷핀", "빨래건조대", "다리미",
    "섬유유연제", "세탁세제",

    # 생활용품
    "테이프", "가위", "포장지", "볼펜", "노트",
    "충전기", "케이블", "이어폰", "거울", "시계",
    "우산", "슬리퍼", "양초", "조명", "전구",

    # 화장품/뷰티
    "화장품", "메이크업", "브러시", "거울", "파우치",
    "헤어밴드", "머리끈", "빗", "헤어클립",

    # 계절상품
    "손난로", "보온", "쿨링", "선풍기", "제습제",

    # 인테리어/DIY
    "액자", "화분", "조화", "스티커", "시트지",
    "후크", "걸이", "정리대", "선반",
]


def build_catalog(keywords: list = None, max_pages_per_keyword: int = 2):
    """다이소 카탈로그 구축"""
    if keywords is None:
        keywords = POPULAR_KEYWORDS

    crawler = DaisoCrawler()
    db = Database()

    all_products = []
    seen_ids = set()

    total_keywords = len(keywords)

    print(f"=== Building Daiso Catalog ===")
    print(f"Keywords: {total_keywords}")
    print(f"Pages per keyword: {max_pages_per_keyword}")
    print()

    for i, keyword in enumerate(keywords, 1):
        try:
            print(f"[{i}/{total_keywords}] {keyword}...", end=" ", flush=True)
        except UnicodeEncodeError:
            print(f"[{i}/{total_keywords}] (keyword)...", end=" ", flush=True)

        try:
            products = crawler.search_all(keyword, max_pages=max_pages_per_keyword)

            new_count = 0
            for p in products:
                if p.product_no not in seen_ids:
                    seen_ids.add(p.product_no)
                    all_products.append(p)
                    new_count += 1

            print(f"found {len(products)}, new: {new_count}")

        except Exception as e:
            print(f"error: {e}")

        # Rate limiting
        time.sleep(0.5)

    print()
    print(f"Total unique products: {len(all_products)}")

    # DB 저장
    print("Saving to database...", end=" ", flush=True)
    saved = 0
    for p in all_products:
        if db.insert_daiso_product(p.to_dict()):
            saved += 1

    print(f"done! ({saved} saved)")
    print(f"Total in catalog: {db.get_daiso_catalog_count()}")

    # 카테고리 통계
    print("\n=== Category Stats ===")
    categories = db.get_daiso_categories()
    for cat in categories[:10]:
        try:
            print(f"  {cat['category_large']} > {cat['category_middle']}: {cat['count']}")
        except UnicodeEncodeError:
            print(f"  (category): {cat['count']}")

    db.close()
    return len(all_products)


def quick_test():
    """빠른 테스트 (5개 키워드만)"""
    test_keywords = ["배수구망", "수세미", "수납함", "청소솔", "거울"]
    return build_catalog(test_keywords, max_pages_per_keyword=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        quick_test()
    else:
        build_catalog()
