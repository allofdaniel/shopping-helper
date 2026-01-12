# -*- coding: utf-8 -*-
"""
데이터 무결성 검증 스크립트
- 모든 테이블의 데이터 품질 검사
- 문제 발견 시 자동 수정 또는 알림
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Tuple

DB_PATH = '../data/products.db'


class DataValidator:
    """데이터 무결성 검증기"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.issues = []
        self.stats = {}

    def validate_all(self) -> Dict:
        """모든 테이블 검증"""
        print("=" * 60)
        print("DATA INTEGRITY VALIDATION")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # 테이블 목록 확인
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]

        results = {}

        if 'ikea_catalog' in tables:
            results['ikea'] = self._validate_ikea(cur)

        if 'costco_catalog' in tables:
            results['costco'] = self._validate_costco(cur)

        conn.close()

        # 종합 보고서
        self._print_summary(results)

        return results

    def _validate_ikea(self, cur) -> Dict:
        """IKEA 데이터 검증"""
        print("\n--- IKEA CATALOG ---")
        issues = []

        # 1. 총 상품 수
        cur.execute('SELECT COUNT(*) FROM ikea_catalog')
        total = cur.fetchone()[0]
        print(f"Total products: {total}")

        if total == 0:
            issues.append(('critical', 'No products in IKEA catalog'))
            return {'total': 0, 'issues': issues, 'valid': False}

        # 2. 가격 검증
        cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE price <= 0')
        zero_price = cur.fetchone()[0]
        if zero_price > 0:
            pct = 100 * zero_price / total
            issues.append(('error', f'{zero_price} products with price=0 ({pct:.1f}%)'))
            print(f"  [ERROR] Price=0: {zero_price} ({pct:.1f}%)")

        cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE price > 0')
        valid_price = cur.fetchone()[0]
        print(f"  Valid price: {valid_price} ({100*valid_price/total:.1f}%)")

        # 3. 가격 범위 검증
        cur.execute('SELECT MIN(price), MAX(price), AVG(price) FROM ikea_catalog WHERE price > 0')
        price_stats = cur.fetchone()
        if price_stats[0]:
            print(f"  Price range: {price_stats[0]:,} ~ {price_stats[1]:,} (avg: {price_stats[2]:,.0f})")
            if price_stats[0] < 1000:
                issues.append(('warning', f'Unusually low min price: {price_stats[0]}'))
            if price_stats[1] > 50000000:
                issues.append(('warning', f'Unusually high max price: {price_stats[1]}'))

        # 4. 이미지 URL 검증
        cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE image_url IS NOT NULL AND image_url != ""')
        with_image = cur.fetchone()[0]
        pct = 100 * with_image / total
        print(f"  With image: {with_image} ({pct:.1f}%)")
        if pct < 80:
            issues.append(('warning', f'Low image coverage: {pct:.1f}%'))

        # 5. 평점 검증
        cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE rating IS NOT NULL')
        with_rating = cur.fetchone()[0]
        pct = 100 * with_rating / total
        print(f"  With rating: {with_rating} ({pct:.1f}%)")

        cur.execute('SELECT AVG(rating) FROM ikea_catalog WHERE rating IS NOT NULL')
        avg_rating = cur.fetchone()[0]
        if avg_rating:
            print(f"  Avg rating: {avg_rating:.2f}")
            if avg_rating < 3.0 or avg_rating > 5.0:
                issues.append(('warning', f'Unusual average rating: {avg_rating:.2f}'))

        # 6. 리뷰 수 검증
        cur.execute('SELECT SUM(review_count) FROM ikea_catalog')
        total_reviews = cur.fetchone()[0] or 0
        print(f"  Total reviews: {total_reviews:,}")

        # 7. 카테고리 검증
        cur.execute('SELECT COUNT(DISTINCT category) FROM ikea_catalog WHERE category IS NOT NULL AND category != ""')
        cat_count = cur.fetchone()[0]
        print(f"  Categories: {cat_count}")
        if cat_count < 5:
            issues.append(('warning', f'Only {cat_count} categories - may be incomplete'))

        # 8. 상품 URL 검증
        cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE product_url IS NOT NULL AND product_url != ""')
        with_url = cur.fetchone()[0]
        print(f"  With URL: {with_url} ({100*with_url/total:.1f}%)")

        # 9. 중복 검사
        cur.execute('SELECT product_no, COUNT(*) as cnt FROM ikea_catalog GROUP BY product_no HAVING cnt > 1')
        duplicates = cur.fetchall()
        if duplicates:
            issues.append(('error', f'{len(duplicates)} duplicate product numbers'))
            print(f"  [ERROR] Duplicates: {len(duplicates)}")

        # 10. 최근 업데이트 확인
        cur.execute('SELECT MAX(updated_at) FROM ikea_catalog')
        last_update = cur.fetchone()[0]
        if last_update:
            print(f"  Last update: {last_update}")

        valid = len([i for i in issues if i[0] == 'critical' or i[0] == 'error']) == 0

        return {
            'total': total,
            'valid_price': valid_price,
            'with_image': with_image,
            'with_rating': with_rating,
            'categories': cat_count,
            'issues': issues,
            'valid': valid
        }

    def _validate_costco(self, cur) -> Dict:
        """Costco 데이터 검증"""
        print("\n--- COSTCO CATALOG ---")
        issues = []

        # 1. 총 상품 수
        cur.execute('SELECT COUNT(*) FROM costco_catalog')
        total = cur.fetchone()[0]
        print(f"Total products: {total}")

        if total == 0:
            issues.append(('critical', 'No products in Costco catalog'))
            return {'total': 0, 'issues': issues, 'valid': False}

        # 2. 가격 검증
        cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE price <= 0')
        zero_price = cur.fetchone()[0]
        if zero_price > 0:
            pct = 100 * zero_price / total
            issues.append(('error', f'{zero_price} products with price=0 ({pct:.1f}%)'))
            print(f"  [ERROR] Price=0: {zero_price} ({pct:.1f}%)")

        cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE price > 0')
        valid_price = cur.fetchone()[0]
        print(f"  Valid price: {valid_price} ({100*valid_price/total:.1f}%)")

        # 3. 가격 범위
        cur.execute('SELECT MIN(price), MAX(price), AVG(price) FROM costco_catalog WHERE price > 0')
        price_stats = cur.fetchone()
        if price_stats[0]:
            print(f"  Price range: {price_stats[0]:,} ~ {price_stats[1]:,} (avg: {price_stats[2]:,.0f})")

        # 4. 이미지 URL
        cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE image_url IS NOT NULL AND image_url != ""')
        with_image = cur.fetchone()[0]
        pct = 100 * with_image / total
        print(f"  With image: {with_image} ({pct:.1f}%)")

        # 5. 브랜드
        cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE brand IS NOT NULL AND brand != ""')
        with_brand = cur.fetchone()[0]
        pct = 100 * with_brand / total
        print(f"  With brand: {with_brand} ({pct:.1f}%)")
        if pct < 50:
            issues.append(('warning', f'Low brand coverage: {pct:.1f}%'))

        # 6. 평점
        cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE rating IS NOT NULL')
        with_rating = cur.fetchone()[0]
        pct = 100 * with_rating / total
        print(f"  With rating: {with_rating} ({pct:.1f}%)")

        cur.execute('SELECT AVG(rating) FROM costco_catalog WHERE rating IS NOT NULL')
        avg_rating = cur.fetchone()[0]
        if avg_rating:
            print(f"  Avg rating: {avg_rating:.2f}")

        # 7. 리뷰 수
        cur.execute('SELECT SUM(review_count) FROM costco_catalog')
        total_reviews = cur.fetchone()[0] or 0
        print(f"  Total reviews: {total_reviews:,}")

        # 8. 카테고리
        cur.execute('SELECT COUNT(DISTINCT category) FROM costco_catalog WHERE category IS NOT NULL')
        cat_count = cur.fetchone()[0]
        print(f"  Categories: {cat_count}")

        # 9. 중복 검사
        cur.execute('SELECT product_no, COUNT(*) as cnt FROM costco_catalog GROUP BY product_no HAVING cnt > 1')
        duplicates = cur.fetchall()
        if duplicates:
            issues.append(('error', f'{len(duplicates)} duplicate product numbers'))

        # 10. 최근 업데이트
        cur.execute('SELECT MAX(updated_at) FROM costco_catalog')
        last_update = cur.fetchone()[0]
        if last_update:
            print(f"  Last update: {last_update}")

        valid = len([i for i in issues if i[0] == 'critical' or i[0] == 'error']) == 0

        return {
            'total': total,
            'valid_price': valid_price,
            'with_image': with_image,
            'with_brand': with_brand,
            'with_rating': with_rating,
            'categories': cat_count,
            'issues': issues,
            'valid': valid
        }

    def _print_summary(self, results: Dict):
        """종합 보고서 출력"""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        all_issues = []
        all_valid = True

        for source, data in results.items():
            status = "[OK]" if data.get('valid', False) else "[FAIL]"
            print(f"{source.upper()}: {status} - {data.get('total', 0)} products")

            if not data.get('valid', False):
                all_valid = False

            for issue in data.get('issues', []):
                all_issues.append((source, issue[0], issue[1]))

        if all_issues:
            print("\n--- ISSUES ---")
            for source, level, msg in all_issues:
                level_icon = {
                    'critical': '[CRITICAL]',
                    'error': '[ERROR]',
                    'warning': '[WARNING]'
                }.get(level, '[INFO]')
                print(f"  {level_icon} {source}: {msg}")

        print("\n" + "=" * 60)
        if all_valid:
            print("RESULT: ALL VALIDATIONS PASSED")
        else:
            print("RESULT: ISSUES FOUND - ACTION REQUIRED")
        print("=" * 60)

        return all_valid


def fix_zero_prices(dry_run: bool = True):
    """가격=0인 상품 수정 시도"""
    print("\n--- FIXING ZERO PRICES ---")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # IKEA
    cur.execute('SELECT COUNT(*) FROM ikea_catalog WHERE price = 0')
    ikea_zero = cur.fetchone()[0]

    # Costco
    cur.execute('SELECT COUNT(*) FROM costco_catalog WHERE price = 0')
    costco_zero = cur.fetchone()[0]

    print(f"IKEA products with price=0: {ikea_zero}")
    print(f"Costco products with price=0: {costco_zero}")

    if not dry_run:
        # 가격=0인 상품 삭제 (정상 수집 불가)
        cur.execute('DELETE FROM ikea_catalog WHERE price = 0')
        cur.execute('DELETE FROM costco_catalog WHERE price = 0')
        conn.commit()
        print(f"Deleted {ikea_zero + costco_zero} products with price=0")

    conn.close()


def remove_duplicates(dry_run: bool = True):
    """중복 상품 제거"""
    print("\n--- REMOVING DUPLICATES ---")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for table in ['ikea_catalog', 'costco_catalog']:
        cur.execute(f'''
            SELECT product_no, COUNT(*) as cnt
            FROM {table}
            GROUP BY product_no
            HAVING cnt > 1
        ''')
        duplicates = cur.fetchall()

        if duplicates:
            print(f"{table}: {len(duplicates)} duplicate product numbers")

            if not dry_run:
                for product_no, count in duplicates:
                    # 가장 최근 것만 남기고 삭제
                    cur.execute(f'''
                        DELETE FROM {table}
                        WHERE product_no = ?
                        AND id NOT IN (
                            SELECT id FROM {table}
                            WHERE product_no = ?
                            ORDER BY updated_at DESC
                            LIMIT 1
                        )
                    ''', (product_no, product_no))

                conn.commit()
                print(f"  Removed duplicates from {table}")
        else:
            print(f"{table}: No duplicates")

    conn.close()


def generate_report() -> str:
    """JSON 형식의 상세 보고서 생성"""
    validator = DataValidator()
    results = validator.validate_all()

    report = {
        'timestamp': datetime.now().isoformat(),
        'results': results
    }

    return json.dumps(report, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    # 검증 실행
    validator = DataValidator()
    results = validator.validate_all()

    # 문제 수정 (dry_run=True로 시뮬레이션)
    # fix_zero_prices(dry_run=True)
    # remove_duplicates(dry_run=True)
