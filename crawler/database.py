"""
꿀템장바구니 - 데이터베이스 모듈
SQLite (개발) / Supabase (프로덕션) 지원
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import DB_PATH, DATA_DIR


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else DB_PATH

        # 데이터 디렉토리 생성
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """데이터베이스 연결"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 딕셔너리 형태 결과

    def _create_tables(self):
        """테이블 생성"""
        cursor = self.conn.cursor()

        # 영상 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                channel_id TEXT,
                channel_title TEXT,
                published_at TEXT,
                thumbnail_url TEXT,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                store_key TEXT,
                store_name TEXT,
                transcript TEXT,
                processed_at TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 상품 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER,
                category TEXT,
                reason TEXT,
                timestamp_sec INTEGER,
                keywords TEXT,
                store_key TEXT,
                store_name TEXT,

                -- 공식 매장 정보
                official_code TEXT,
                official_name TEXT,
                official_price INTEGER,
                official_image_url TEXT,
                official_product_url TEXT,
                is_matched INTEGER DEFAULT 0,

                -- 메타 정보
                is_approved INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                source_view_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            )
        """)

        # 채널 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT,
                subscriber_count INTEGER,
                store_key TEXT,
                is_active INTEGER DEFAULT 1,
                last_checked_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 다이소몰 공식 상품 카탈로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daiso_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                category_large TEXT,
                category_middle TEXT,
                category_small TEXT,
                rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                order_count INTEGER DEFAULT 0,
                is_new INTEGER DEFAULT 0,
                is_best INTEGER DEFAULT 0,
                sold_out INTEGER DEFAULT 0,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 인덱스 생성
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_approved ON products(is_approved)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daiso_catalog_name ON daiso_catalog(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daiso_catalog_category ON daiso_catalog(category_large, category_middle)")

        self.conn.commit()

    # ========== 영상 관련 ==========

    def insert_video(self, video: dict) -> bool:
        """영상 정보 저장 (중복 무시)"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO videos
                (video_id, title, description, channel_id, channel_title, published_at,
                 thumbnail_url, view_count, like_count, store_key, store_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                video.get("video_id"),
                video.get("title"),
                video.get("description", ""),
                video.get("channel_id"),
                video.get("channel_title"),
                video.get("published_at"),
                video.get("thumbnail_url"),
                video.get("view_count", 0),
                video.get("like_count", 0),
                video.get("store_key"),
                video.get("store_name"),
            ))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"영상 저장 오류: {e}")
            return False

    def update_video_transcript(self, video_id: str, transcript: str):
        """자막 저장"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE videos
            SET transcript = ?, processed_at = ?, status = 'transcribed'
            WHERE video_id = ?
        """, (transcript, datetime.now().isoformat(), video_id))
        self.conn.commit()

    def update_video_status(self, video_id: str, status: str):
        """영상 처리 상태 업데이트"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE videos SET status = ? WHERE video_id = ?
        """, (status, video_id))
        self.conn.commit()

    def get_pending_videos(self, limit: int = 10) -> list:
        """처리 대기 중인 영상 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM videos
            WHERE status = 'pending'
            ORDER BY view_count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_video_by_id(self, video_id: str) -> Optional[dict]:
        """영상 ID로 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ========== 상품 관련 ==========

    def insert_product(self, product: dict) -> int:
        """상품 정보 저장"""
        cursor = self.conn.cursor()

        # keywords 리스트를 JSON 문자열로
        keywords = product.get("keywords", [])
        if isinstance(keywords, list):
            import json
            keywords = json.dumps(keywords, ensure_ascii=False)

        official = product.get("official", {})

        cursor.execute("""
            INSERT INTO products
            (video_id, name, price, category, reason, timestamp_sec, keywords,
             store_key, store_name, official_code, official_name, official_price,
             official_image_url, official_product_url, is_matched, source_view_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product.get("video_id"),
            product.get("name"),
            product.get("price"),
            product.get("category"),
            product.get("reason"),
            product.get("timestamp"),
            keywords,
            product.get("store_key"),
            product.get("store_name"),
            official.get("product_code"),
            official.get("official_name"),
            official.get("official_price"),
            official.get("image_url"),
            official.get("product_url"),
            1 if official.get("matched") else 0,
            product.get("source_view_count", 0),
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_products_by_store(self, store_key: str, approved_only: bool = True,
                               limit: int = 100, offset: int = 0) -> list:
        """매장별 상품 조회"""
        cursor = self.conn.cursor()
        query = """
            SELECT p.*, v.title as video_title, v.channel_title, v.view_count as video_view_count
            FROM products p
            JOIN videos v ON p.video_id = v.video_id
            WHERE p.store_key = ?
        """
        if approved_only:
            query += " AND p.is_approved = 1"
        query += " AND p.is_hidden = 0"
        query += " ORDER BY p.source_view_count DESC"
        query += f" LIMIT {limit} OFFSET {offset}"

        cursor.execute(query, (store_key,))
        return [dict(row) for row in cursor.fetchall()]

    def get_pending_products(self, limit: int = 50) -> list:
        """승인 대기 상품 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.*, v.title as video_title, v.channel_title, v.thumbnail_url
            FROM products p
            JOIN videos v ON p.video_id = v.video_id
            WHERE p.is_approved = 0 AND p.is_hidden = 0
            ORDER BY p.source_view_count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def approve_product(self, product_id: int):
        """상품 승인"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE products
            SET is_approved = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), product_id))
        self.conn.commit()

    def hide_product(self, product_id: int):
        """상품 숨김 (비추천 상품 등)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE products
            SET is_hidden = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), product_id))
        self.conn.commit()

    # ========== 다이소 카탈로그 관련 ==========

    def insert_daiso_product(self, product: dict) -> bool:
        """다이소몰 상품 저장 (upsert)"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO daiso_catalog
                (product_no, name, price, image_url, product_url, category,
                 category_large, category_middle, category_small,
                 rating, review_count, order_count, is_new, is_best, sold_out, keywords, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(product_no) DO UPDATE SET
                    name = excluded.name,
                    price = excluded.price,
                    image_url = excluded.image_url,
                    rating = excluded.rating,
                    review_count = excluded.review_count,
                    order_count = excluded.order_count,
                    is_new = excluded.is_new,
                    is_best = excluded.is_best,
                    sold_out = excluded.sold_out,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                product.get("product_no"),
                product.get("name"),
                product.get("price"),
                product.get("image_url"),
                product.get("product_url"),
                product.get("category"),
                product.get("category_large"),
                product.get("category_middle"),
                product.get("category_small"),
                product.get("rating", 0),
                product.get("review_count", 0),
                product.get("order_count", 0),
                1 if product.get("is_new") else 0,
                1 if product.get("is_best") else 0,
                1 if product.get("sold_out") else 0,
                product.get("keywords", ""),
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"다이소 상품 저장 오류: {e}")
            return False

    def insert_daiso_products_batch(self, products: list) -> int:
        """다이소몰 상품 배치 저장"""
        count = 0
        for product in products:
            if self.insert_daiso_product(product):
                count += 1
        return count

    def search_daiso_catalog(self, keyword: str, limit: int = 20) -> list:
        """다이소 카탈로그에서 상품 검색"""
        cursor = self.conn.cursor()
        search_term = f"%{keyword}%"
        cursor.execute("""
            SELECT * FROM daiso_catalog
            WHERE name LIKE ? OR keywords LIKE ?
            ORDER BY order_count DESC
            LIMIT ?
        """, (search_term, search_term, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_daiso_product_by_no(self, product_no: str) -> Optional[dict]:
        """품번으로 다이소 상품 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM daiso_catalog WHERE product_no = ?", (product_no,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_daiso_catalog_count(self) -> int:
        """다이소 카탈로그 상품 수"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daiso_catalog")
        return cursor.fetchone()[0]

    def get_daiso_categories(self) -> list:
        """다이소 카테고리 목록"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT category_large, category_middle, COUNT(*) as count
            FROM daiso_catalog
            GROUP BY category_large, category_middle
            ORDER BY count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    # ========== 통계 ==========

    def get_stats(self) -> dict:
        """전체 통계 조회"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM videos")
        total_videos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products WHERE is_approved = 1")
        approved_products = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products WHERE is_approved = 0 AND is_hidden = 0")
        pending_products = cursor.fetchone()[0]

        cursor.execute("""
            SELECT store_key, COUNT(*) as count
            FROM products
            WHERE is_approved = 1
            GROUP BY store_key
        """)
        by_store = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_videos": total_videos,
            "total_products": total_products,
            "approved_products": approved_products,
            "pending_products": pending_products,
            "by_store": by_store,
        }

    def close(self):
        """연결 종료"""
        if self.conn:
            self.conn.close()


def main():
    """테스트 실행"""
    db = Database()

    # 테스트 데이터 삽입
    test_video = {
        "video_id": "test123",
        "title": "다이소 꿀템 10가지",
        "channel_id": "UC123",
        "channel_title": "테스트 채널",
        "published_at": "2024-01-01T00:00:00Z",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "view_count": 100000,
        "store_key": "daiso",
        "store_name": "다이소",
    }

    db.insert_video(test_video)

    test_product = {
        "video_id": "test123",
        "name": "스텐 배수구망",
        "price": 2000,
        "category": "주방",
        "reason": "물때가 안 껴요",
        "timestamp": 120,
        "keywords": ["배수구", "스텐", "주방용품"],
        "store_key": "daiso",
        "store_name": "다이소",
        "source_view_count": 100000,
        "official": {
            "product_code": "12345678",
            "official_name": "스텐레스 배수구망",
            "official_price": 2000,
            "image_url": "https://example.com/product.jpg",
            "product_url": "https://daisomall.co.kr/product/12345678",
            "matched": True,
        },
    }

    db.insert_product(test_product)

    # 통계 출력
    stats = db.get_stats()
    print("\n=== 데이터베이스 통계 ===")
    print(f"총 영상: {stats['total_videos']}")
    print(f"총 상품: {stats['total_products']}")
    print(f"승인된 상품: {stats['approved_products']}")
    print(f"승인 대기: {stats['pending_products']}")

    db.close()
    print(f"\n데이터베이스 위치: {DB_PATH}")


if __name__ == "__main__":
    main()
