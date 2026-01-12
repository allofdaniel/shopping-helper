# -*- coding: utf-8 -*-
"""
S3 업로더
수집된 데이터를 AWS S3에 업로드합니다.
"""
import os
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from config import DATA_DIR, DB_PATH


class S3Uploader:
    """S3 데이터 업로더"""

    def __init__(self, bucket_name: str = None, prefix: str = "shopping-helper"):
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3가 필요합니다: pip install boto3")

        self.bucket_name = bucket_name or os.getenv("S3_BUCKET", "notam-korea-data")
        self.prefix = prefix

        # AWS 클라이언트 (credentials는 ~/.aws/credentials에서 자동 로드)
        self.s3 = boto3.client('s3')

    def upload_database(self, local_path: Path = None) -> str:
        """
        SQLite 데이터베이스를 S3에 업로드

        Returns:
            S3 URI (s3://bucket/key)
        """
        local_path = local_path or DB_PATH

        if not local_path.exists():
            print(f"[!] DB 파일 없음: {local_path}")
            return None

        # 타임스탬프 파일명
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{self.prefix}/db/products_{timestamp}.db"
        s3_key_latest = f"{self.prefix}/db/products_latest.db"

        try:
            # 업로드 (타임스탬프 버전)
            self.s3.upload_file(str(local_path), self.bucket_name, s3_key)
            print(f"[OK] 업로드됨: s3://{self.bucket_name}/{s3_key}")

            # 최신 버전 덮어쓰기
            self.s3.upload_file(str(local_path), self.bucket_name, s3_key_latest)
            print(f"[OK] 최신: s3://{self.bucket_name}/{s3_key_latest}")

            return f"s3://{self.bucket_name}/{s3_key}"

        except ClientError as e:
            print(f"[!] S3 업로드 오류: {e}")
            return None

    def upload_json_export(self) -> str:
        """
        DB 데이터를 JSON으로 내보내고 S3에 업로드
        (프론트엔드용 정적 파일)
        """
        # DB에서 데이터 추출
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 상품 데이터 (인기순)
        cursor.execute("""
            SELECT p.*, v.title as video_title, v.channel_title, v.thumbnail_url, v.view_count as video_view_count
            FROM products p
            LEFT JOIN videos v ON p.video_id = v.video_id
            WHERE p.is_hidden = 0
            ORDER BY p.source_view_count DESC
            LIMIT 2000
        """)

        products = []
        for row in cursor.fetchall():
            product = dict(row)
            # keywords JSON 파싱
            if product.get('keywords'):
                try:
                    product['keywords'] = json.loads(product['keywords'])
                except (json.JSONDecodeError, TypeError):
                    product['keywords'] = []
            else:
                product['keywords'] = []
            products.append(product)

        # 통계 계산
        stats = {
            "total_products": len(products),
            "by_store": {},
            "by_category": {}
        }
        for p in products:
            store = p.get('store_key', 'unknown')
            stats["by_store"][store] = stats["by_store"].get(store, 0) + 1

            cat = p.get('category', '')
            if cat:
                stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        conn.close()

        # JSON 저장
        json_dir = DATA_DIR / "export" / "json"
        json_dir.mkdir(parents=True, exist_ok=True)

        # 상품 JSON
        products_json_path = json_dir / "products_latest.json"
        with open(products_json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "total": len(products),
                "products": products
            }, f, ensure_ascii=False)

        # 통계 JSON
        stats_json_path = json_dir / "stats_latest.json"
        with open(stats_json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                **stats
            }, f, ensure_ascii=False)

        # S3 업로드 (CORS 허용)
        try:
            # 상품 JSON 업로드
            self.s3.upload_file(
                str(products_json_path),
                self.bucket_name,
                f"{self.prefix}/json/products_latest.json",
                ExtraArgs={
                    'ContentType': 'application/json',
                    'CacheControl': 'max-age=300',  # 5분 캐시
                }
            )
            print(f"[OK] 상품 JSON 업로드됨")

            # 통계 JSON 업로드
            self.s3.upload_file(
                str(stats_json_path),
                self.bucket_name,
                f"{self.prefix}/json/stats_latest.json",
                ExtraArgs={
                    'ContentType': 'application/json',
                    'CacheControl': 'max-age=300',
                }
            )
            print(f"[OK] 통계 JSON 업로드됨")

            return f"s3://{self.bucket_name}/{self.prefix}/json/products_latest.json"

        except ClientError as e:
            print(f"[!] JSON 업로드 오류: {e}")
            return None

    def upload_all(self) -> dict:
        """모든 데이터 업로드"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "database": None,
            "json_export": None
        }

        print("\n=== S3 업로드 시작 ===\n")

        # DB 업로드
        results["database"] = self.upload_database()

        # JSON 내보내기 업로드
        results["json_export"] = self.upload_json_export()

        print("\n=== S3 업로드 완료 ===")
        return results

    def download_latest_db(self, local_path: Path = None) -> bool:
        """S3에서 최신 DB 다운로드"""
        local_path = local_path or DB_PATH

        s3_key = f"{self.prefix}/db/products_latest.db"

        try:
            self.s3.download_file(self.bucket_name, s3_key, str(local_path))
            print(f"[OK] 다운로드됨: {local_path}")
            return True

        except ClientError as e:
            print(f"[!] 다운로드 오류: {e}")
            return False


def main():
    """테스트"""
    print("=== S3 업로더 테스트 ===\n")

    if not BOTO3_AVAILABLE:
        print("boto3가 필요합니다: pip install boto3")
        return

    try:
        uploader = S3Uploader()
        results = uploader.upload_all()
        print(f"\n결과: {json.dumps(results, indent=2)}")

    except Exception as e:
        print(f"오류: {e}")


if __name__ == "__main__":
    main()
