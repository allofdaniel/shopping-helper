# -*- coding: utf-8 -*-
"""
IKEA 데이터 저장 스크립트
"""
import sqlite3

# 추출된 IKEA 데이터 (평점 정보 포함)
products = [
    {'productId': '09246408', 'name': 'LINNMON ADILS TABLE', 'price': 49900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/linnmon-adils-table-white-s09246408/', 'rating': 4.4, 'reviewCount': 1470},
    {'productId': '20354284', 'name': 'MICKE CORNER WORKSTATION', 'price': 199000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/micke-corner-workstation-white-20354284/', 'rating': 4.5, 'reviewCount': 664},
    {'productId': '80354276', 'name': 'MICKE DESK', 'price': 99900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/micke-desk-white-80354276/', 'rating': 4.5, 'reviewCount': 5965},
    {'productId': '09223322', 'name': 'MICKE DESK', 'price': 149900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/micke-desk-white-s09223322/', 'rating': 4.6, 'reviewCount': 1615},
    {'productId': '80354281', 'name': 'MICKE DESK', 'price': 69900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/micke-desk-white-80354281/', 'rating': 4.6, 'reviewCount': 3913},
    {'productId': '09416759', 'name': 'LAGKAPTEN ADILS DESK', 'price': 59900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/lagkapten-adils-desk-white-s09416759/', 'rating': 4.5, 'reviewCount': 345},
    {'productId': '70493956', 'name': 'TORALD DESK', 'price': 35000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/torald-desk-white-70493956/', 'rating': 4.5, 'reviewCount': 654},
    {'productId': '20361152', 'name': 'MALM DESK', 'price': 169000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/malm-desk-with-pull-out-panel-white-20361152/', 'rating': 4.6, 'reviewCount': 608},
    {'productId': '40500350', 'name': 'UTESPELARE GAMING DESK', 'price': 199000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/utespelare-gaming-desk-black-40500350/', 'rating': 4.7, 'reviewCount': 603},
    {'productId': '29590154', 'name': 'LINNMON ADILS TABLE', 'price': 39900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/linnmon-adils-table-white-s29590154/', 'rating': 3.0, 'reviewCount': 2},
    {'productId': '40354278', 'name': 'MICKE DESK', 'price': 149000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/micke-desk-white-40354278/', 'rating': 4.5, 'reviewCount': 2212},
    {'productId': '59525845', 'name': 'MITTZON DESK', 'price': 169000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/mittzon-desk-white-s59525845/', 'rating': 4.7, 'reviewCount': 89},
    {'productId': '50361754', 'name': 'MALM DESK', 'price': 199000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/malm-desk-white-50361754/', 'rating': 4.5, 'reviewCount': 904},
    {'productId': '59429561', 'name': 'TROTTEN DESK', 'price': 199000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/trotten-desk-white-s59429561/', 'rating': 4.7, 'reviewCount': 233},
    {'productId': '09416820', 'name': 'LAGKAPTEN ALEX DESK', 'price': 156900, 'originalPrice': 168900, 'productUrl': 'https://www.ikea.com/kr/ko/p/lagkapten-alex-desk-white-s09416820/', 'rating': 4.6, 'reviewCount': 700},
    {'productId': '10476479', 'name': 'BJOERKASEN LAPTOP STAND', 'price': 29900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/bjoerkasen-laptop-stand-beige-10476479/', 'rating': 4.5, 'reviewCount': 1145},
    {'productId': '89526037', 'name': 'MITTZON DESK', 'price': 199000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/mittzon-desk-white-s89526037/', 'rating': 4.6, 'reviewCount': 54},
    {'productId': '09424943', 'name': 'TROTTEN DESK', 'price': 149000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/trotten-desk-white-s09424943/', 'rating': 4.8, 'reviewCount': 410},
    {'productId': '39429557', 'name': 'TROTTEN DESK', 'price': 169000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/trotten-desk-white-s39429557/', 'rating': 4.7, 'reviewCount': 57},
    {'productId': '39417154', 'name': 'LAGKAPTEN ADILS DESK', 'price': 69900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/lagkapten-adils-desk-white-s39417154/', 'rating': 4.3, 'reviewCount': 189},
    {'productId': '60493952', 'name': 'GLADHOEJDEN DESK', 'price': 219000, 'originalPrice': 249000, 'productUrl': 'https://www.ikea.com/kr/ko/p/gladhoejden-desk-sit-stand-white-60493952/', 'rating': 4.3, 'reviewCount': 120},
    {'productId': '00541611', 'name': 'GLADHOEJDEN DESK', 'price': 219000, 'originalPrice': 249000, 'productUrl': 'https://www.ikea.com/kr/ko/p/gladhoejden-desk-sit-stand-light-grey-anthracite-00541611/', 'rating': 4.3, 'reviewCount': 120},
    {'productId': '20527949', 'name': 'MITTZON TABLE', 'price': 269000, 'originalPrice': 299000, 'productUrl': 'https://www.ikea.com/kr/ko/p/mittzon-foldable-table-with-castors-black-20527949/', 'rating': 4.3, 'reviewCount': 25},
    {'productId': '20582441', 'name': 'KALLAX DESK', 'price': 89900, 'originalPrice': 99900, 'productUrl': 'https://www.ikea.com/kr/ko/p/kallax-desk-black-brown-20582441/', 'rating': 4.6, 'reviewCount': 231},
    {'productId': '60527952', 'name': 'MITTZON TABLE', 'price': 269000, 'originalPrice': 299000, 'productUrl': 'https://www.ikea.com/kr/ko/p/mittzon-foldable-table-with-castors-green-60527952/', 'rating': 4.3, 'reviewCount': 25},
    {'productId': '90527955', 'name': 'MITTZON TABLE', 'price': 269000, 'originalPrice': 299000, 'productUrl': 'https://www.ikea.com/kr/ko/p/mittzon-foldable-table-with-castors-white-90527955/', 'rating': 4.3, 'reviewCount': 25},
    {'productId': '29555004', 'name': 'KALLAX LOBERGET DESK', 'price': 139800, 'originalPrice': 149800, 'productUrl': 'https://www.ikea.com/kr/ko/p/kallax-loberget-desk-and-chair-white-s29555004/', 'rating': 4.5, 'reviewCount': 8},
    {'productId': '60278288', 'name': 'LILLASEN DESK', 'price': 134000, 'originalPrice': 149000, 'productUrl': 'https://www.ikea.com/kr/ko/p/lillasen-desk-bamboo-60278288/', 'rating': 4.6, 'reviewCount': 634},
    {'productId': '69437476', 'name': 'PAHL DESK', 'price': 79900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/pahl-desk-white-turquoise-s69437476/', 'rating': 4.4, 'reviewCount': 46},
    {'productId': '19245106', 'name': 'PAHL DESK', 'price': 79900, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/pahl-desk-white-s19245106/', 'rating': 4.5, 'reviewCount': 230},
    {'productId': '20528500', 'name': 'PIPLAERKA DESK', 'price': 119000, 'originalPrice': None, 'productUrl': 'https://www.ikea.com/kr/ko/p/piplaerka-desk-tiltable-20528500/', 'rating': 4.2, 'reviewCount': 30},
]

def save_to_db():
    # DB 연결
    conn = sqlite3.connect('../data/products.db')
    cur = conn.cursor()

    # 기존 데이터 삭제 후 새로 추가
    cur.execute('DELETE FROM ikea_catalog')

    added = 0
    for p in products:
        try:
            cur.execute('''
                INSERT INTO ikea_catalog
                (product_no, name, name_ko, price, original_price, image_url, product_url,
                 category, rating, review_count, is_new, is_sale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p['productId'],
                p['name'],
                p['name'],  # name_ko
                p['price'],
                p['originalPrice'],
                '',  # image_url
                p['productUrl'],
                '책상',  # category
                p['rating'],
                p['reviewCount'],
                0,  # is_new
                1 if p['originalPrice'] else 0,  # is_sale
            ))
            added += 1
        except Exception as e:
            print(f'Error: {e}')

    conn.commit()

    # 통계 확인
    cur.execute('SELECT COUNT(*) FROM ikea_catalog')
    total = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE price > 0')
    valid_price = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE rating IS NOT NULL')
    with_rating = cur.fetchone()[0]

    cur.execute('SELECT AVG(rating) FROM ikea_catalog WHERE rating IS NOT NULL')
    avg_rating = cur.fetchone()[0] or 0

    cur.execute('SELECT SUM(review_count) FROM ikea_catalog')
    total_reviews = cur.fetchone()[0] or 0

    print('=== IKEA 데이터 저장 완료 ===')
    print(f'추가: {added}개')
    print(f'총 상품: {total}개')
    print(f'가격 있음: {valid_price}개')
    print(f'평점 있음: {with_rating}개')
    print(f'평균 평점: {avg_rating:.2f}')
    print(f'총 리뷰: {total_reviews:,}개')

    # 샘플 출력
    print('\n--- 샘플 상품 (리뷰 많은 순) ---')
    cur.execute('SELECT name, price, rating, review_count FROM ikea_catalog ORDER BY review_count DESC LIMIT 5')
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]:,}원 (평점: {row[2]}, 리뷰: {row[3]:,})')

    conn.close()


if __name__ == '__main__':
    save_to_db()
