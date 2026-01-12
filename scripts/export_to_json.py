# -*- coding: utf-8 -*-
"""
SQLite 데이터를 JSON으로 내보내기
Vercel 배포용 정적 데이터 생성
"""
import sqlite3
import json
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'products.db'
OUTPUT_DIR = Path(__file__).parent.parent / 'web' / 'public' / 'data'


def export_table(cur, table_name: str, store_key: str, limit: int = 5000):
    """테이블을 JSON으로 내보내기"""
    try:
        # 테이블 존재 확인
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cur.fetchone():
            print(f"  [SKIP] {table_name} not found")
            return None

        # 컬럼 정보 가져오기
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cur.fetchall()]

        # 데이터 가져오기
        cur.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = cur.fetchall()

        # 딕셔너리로 변환
        products = []
        for row in rows:
            product = {}
            for i, col in enumerate(columns):
                val = row[i]
                # None 처리
                if val is None:
                    val = None
                product[col] = val
            products.append(product)

        # 총 개수
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        total = cur.fetchone()[0]

        return {
            'store': store_key,
            'table': table_name,
            'total': total,
            'exported': len(products),
            'products': products
        }

    except Exception as e:
        print(f"  [ERROR] {table_name}: {e}")
        return None


def main():
    print("=" * 60)
    print("EXPORTING DATABASE TO JSON")
    print("=" * 60)

    # 출력 디렉토리 생성
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 내보낼 테이블 목록
    tables = [
        ('daiso_catalog', 'daiso', '다이소'),
        ('costco_catalog', 'costco', 'Costco'),
        ('ikea_catalog', 'ikea', 'IKEA'),
        ('oliveyoung_catalog', 'oliveyoung', '올리브영'),
        ('traders_catalog', 'traders', '트레이더스'),
        ('convenience_catalog', 'convenience', '편의점'),
    ]

    summary = {}

    for table_name, store_key, store_name in tables:
        print(f"\n{store_name} ({table_name})...")

        data = export_table(cur, table_name, store_key)

        if data:
            # JSON 파일 저장
            output_file = OUTPUT_DIR / f"{store_key}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"  Exported: {data['exported']}/{data['total']} products")
            print(f"  File: {output_file}")

            summary[store_key] = {
                'name': store_name,
                'total': data['total'],
                'exported': data['exported']
            }

    # 요약 파일 저장
    summary_file = OUTPUT_DIR / 'summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'stores': summary,
            'total_products': sum(s['total'] for s in summary.values())
        }, f, ensure_ascii=False, indent=2)

    conn.close()

    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print(f"Total stores: {len(summary)}")
    print(f"Total products: {sum(s['total'] for s in summary.values()):,}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
