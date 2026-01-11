# -*- coding: utf-8 -*-
"""
개선된 데이터베이스 모듈
- UNIQUE 제약조건 추가 (video_id, name, price)
- 중복 삽입 방지
- 품질 메트릭 추가
- 제너릭 카탈로그 insert 메서드
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from config import DB_PATH, DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).parent.parent / "data"
    DB_PATH = DATA_DIR / "products.db"


# 카탈로그 테이블 설정 (제너릭 insert를 위한 매핑)
CATALOG_CONFIG: Dict[str, Dict[str, Any]] = {
    "daiso": {
        "table": "daiso_catalog",
        "id_column": "product_no",
        "columns": ["product_no", "name", "price", "image_url", "product_url", "category",
                    "category_large", "category_middle", "category_small",
                    "rating", "review_count", "order_count", "is_new", "is_best", "sold_out", "keywords"],
        "update_columns": ["name", "price", "image_url", "rating", "review_count",
                           "order_count", "is_new", "is_best", "sold_out"],
        "bool_columns": ["is_new", "is_best", "sold_out"],
    },
    "costco": {
        "table": "costco_catalog",
        "id_column": "product_code",
        "columns": ["product_code", "name", "price", "image_url", "product_url", "category",
                    "unit_price", "rating", "review_count", "keywords"],
        "update_columns": ["name", "price", "image_url", "product_url", "unit_price", "rating", "review_count"],
        "bool_columns": [],
    },
    "oliveyoung": {
        "table": "oliveyoung_catalog",
        "id_column": "product_code",
        "columns": ["product_code", "name", "brand", "price", "original_price", "image_url",
                    "product_url", "category", "rating", "review_count", "is_best", "is_sale", "keywords"],
        "update_columns": ["name", "brand", "price", "original_price", "image_url", "product_url",
                           "rating", "review_count", "is_best", "is_sale"],
        "bool_columns": ["is_best", "is_sale"],
    },
    "coupang": {
        "table": "coupang_catalog",
        "id_column": "product_id",
        "columns": ["product_id", "name", "price", "original_price", "image_url", "product_url",
                    "category", "rating", "review_count", "is_rocket", "is_rocket_fresh", "seller", "keywords"],
        "update_columns": ["name", "price", "original_price", "image_url", "product_url",
                           "rating", "review_count", "is_rocket", "is_rocket_fresh", "seller"],
        "bool_columns": ["is_rocket", "is_rocket_fresh"],
    },
    "traders": {
        "table": "traders_catalog",
        "id_column": "item_id",
        "columns": ["item_id", "name", "brand", "price", "original_price", "image_url",
                    "product_url", "category", "unit_price", "keywords"],
        "update_columns": ["name", "brand", "price", "original_price", "image_url", "product_url", "unit_price"],
        "bool_columns": [],
    },
    "ikea": {
        "table": "ikea_catalog",
        "id_column": "product_id",
        "columns": ["product_id", "name", "type_name", "price", "image_url", "product_url",
                    "category", "color", "size", "rating", "review_count", "keywords"],
        "update_columns": ["name", "type_name", "price", "image_url", "product_url",
                           "rating", "review_count"],
        "bool_columns": [],
    },
    "convenience": {
        "table": "convenience_catalog",
        "id_column": "product_id",  # + store (복합키)
        "columns": ["product_id", "store", "name", "price", "original_price", "image_url",
                    "product_url", "category", "event_type", "is_new", "is_pb", "keywords"],
        "update_columns": ["name", "price", "original_price", "image_url", "event_type", "is_new"],
        "bool_columns": ["is_new", "is_pb"],
        "composite_key": ["product_id", "store"],
    },
}


class ImprovedDatabase:
    """개선된 데이터베이스 클래스"""

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = None
        self._connect()
        self._create_tables()
        self._migrate_existing_tables()
        self._add_unique_constraints()

    def _connect(self):
        """데이터베이스 연결"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

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
                transcript_quality_score REAL DEFAULT 0,
                processed_at TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 상품 테이블 (UNIQUE 제약조건 포함)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER,
                category TEXT,
                reason TEXT,
                recommendation_quote TEXT,
                timestamp_sec INTEGER,
                timestamp_text TEXT,
                keywords TEXT,
                store_key TEXT,
                store_name TEXT,

                -- 영상 내 추천 구간 (시작~끝 타임스탬프)
                video_start_sec INTEGER,
                video_end_sec INTEGER,
                video_url TEXT,

                -- 공식 매장 정보
                official_code TEXT,
                official_name TEXT,
                official_price INTEGER,
                official_image_url TEXT,
                official_product_url TEXT,
                official_description TEXT,
                official_category TEXT,
                is_matched INTEGER DEFAULT 0,
                match_score INTEGER DEFAULT 0,
                match_confidence REAL DEFAULT 0,

                -- 품질 메트릭
                extraction_confidence REAL DEFAULT 0,
                needs_manual_review INTEGER DEFAULT 0,

                -- 메타 정보
                is_approved INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                source_view_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            )
        """)

        # 다이소 카탈로그 테이블
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

        # 코스트코 카탈로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS costco_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                unit_price TEXT,
                rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 올리브영 카탈로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oliveyoung_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                brand TEXT,
                price INTEGER,
                original_price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                is_best INTEGER DEFAULT 0,
                is_sale INTEGER DEFAULT 0,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 쿠팡 카탈로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coupang_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                price INTEGER,
                original_price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                is_rocket INTEGER DEFAULT 0,
                is_rocket_fresh INTEGER DEFAULT 0,
                seller TEXT,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 트레이더스 카탈로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traders_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                brand TEXT,
                price INTEGER,
                original_price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                unit_price TEXT,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 이케아 카탈로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ikea_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                type_name TEXT,
                price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                color TEXT,
                size TEXT,
                rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 편의점 카탈로그 테이블 (통합)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS convenience_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                store TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER,
                original_price INTEGER,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                event_type TEXT,
                is_new INTEGER DEFAULT 0,
                is_pb INTEGER DEFAULT 0,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_id, store)
            )
        """)

        # 품질 로그 테이블 (새로 추가)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                transcript_length INTEGER,
                transcript_quality_score REAL,
                products_extracted INTEGER,
                products_matched INTEGER,
                avg_extraction_confidence REAL,
                avg_match_confidence REAL,
                processing_time_sec REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            )
        """)

        self.conn.commit()

    def _migrate_existing_tables(self):
        """기존 테이블에 새 컬럼 추가 (마이그레이션)"""
        cursor = self.conn.cursor()

        # videos 테이블에 필요한 컬럼들
        videos_columns = [
            ("transcript_quality_score", "REAL DEFAULT 0"),
            ("processed_at", "TEXT"),
            ("status", "TEXT DEFAULT 'pending'"),
        ]
        for col_name, col_type in videos_columns:
            try:
                cursor.execute(f"ALTER TABLE videos ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    pass  # 이미 존재하면 무시

        # products 테이블에 필요한 컬럼들
        products_columns = [
            ("recommendation_quote", "TEXT"),
            ("extraction_confidence", "REAL DEFAULT 0"),
            ("needs_manual_review", "INTEGER DEFAULT 0"),
            ("official_code", "TEXT"),
            ("official_name", "TEXT"),
            ("official_price", "INTEGER"),
            ("official_image_url", "TEXT"),
            ("official_product_url", "TEXT"),
            ("official_description", "TEXT"),
            ("official_category", "TEXT"),
            ("is_matched", "INTEGER DEFAULT 0"),
            ("match_score", "INTEGER DEFAULT 0"),
            ("match_confidence", "REAL DEFAULT 0"),
            ("is_approved", "INTEGER DEFAULT 0"),
            ("is_hidden", "INTEGER DEFAULT 0"),
            ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
            # 영상 타임스탬프 관련 컬럼
            ("video_start_sec", "INTEGER"),
            ("video_end_sec", "INTEGER"),
            ("video_url", "TEXT"),
        ]
        for col_name, col_type in products_columns:
            try:
                cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    pass  # 이미 존재하면 무시

        self.conn.commit()

    def _add_unique_constraints(self):
        """UNIQUE 제약조건 추가 (이미 있으면 무시)"""
        cursor = self.conn.cursor()

        # products 테이블에 UNIQUE 인덱스 추가
        # (video_id, name, price) 조합이 유일해야 함
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_products_unique
                ON products(video_id, name, COALESCE(price, 0))
            """)
            self.conn.commit()
        except sqlite3.OperationalError as e:
            # 이미 존재하면 무시
            if "already exists" not in str(e):
                print(f"인덱스 생성 경고: {e}")

        # 추가 인덱스
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_approved ON products(is_approved)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_video_id ON products(video_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_confidence ON products(extraction_confidence)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_store_key ON videos(store_key)")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

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

    def update_video_transcript(self, video_id: str, transcript: str, quality_score: float = 0):
        """자막 저장"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE videos
            SET transcript = ?, transcript_quality_score = ?,
                processed_at = ?, status = 'transcribed'
            WHERE video_id = ?
        """, (transcript, quality_score, datetime.now().isoformat(), video_id))
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

    def get_transcribed_videos(self, limit: int = 20) -> list:
        """자막 추출 완료된 영상 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM videos
            WHERE status = 'transcribed'
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

    def get_all_video_ids(self) -> List[str]:
        """모든 영상 ID 조회 (중복 체크용)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT video_id FROM videos")
        return [row[0] for row in cursor.fetchall()]

    def video_exists(self, video_id: str) -> bool:
        """영상 존재 여부 확인"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM videos WHERE video_id = ? LIMIT 1", (video_id,))
        return cursor.fetchone() is not None

    # ========== 상품 관련 ==========

    def insert_product(self, product: dict) -> Optional[int]:
        """
        상품 정보 저장 (중복 시 무시)

        Returns:
            삽입된 ID 또는 None (중복 시)
        """
        cursor = self.conn.cursor()

        # keywords 리스트를 JSON 문자열로
        keywords = product.get("keywords", [])
        if isinstance(keywords, list):
            keywords = json.dumps(keywords, ensure_ascii=False)

        official = product.get("official", {}) or {}

        # 가격이 없고 공식 가격이 있으면 사용
        price = product.get("price")
        if price is None and official:
            price = official.get("official_price") or official.get("price")

        # 매칭 여부 확인
        is_matched = 1 if official.get("matched") or official.get("product_no") else 0

        # 카탈로그 매칭 안 되면 숨김 처리 (다이소몰 기준)
        is_hidden = 0 if is_matched else 1

        # 영상 URL 생성
        video_id = product.get("video_id")
        video_url = product.get("video_url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else None)

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO products
                (video_id, name, price, category, reason, recommendation_quote,
                 timestamp_sec, timestamp_text, keywords, store_key, store_name,
                 video_start_sec, video_end_sec, video_url,
                 official_code, official_name, official_price,
                 official_image_url, official_product_url, official_description, official_category,
                 is_matched, match_score, match_confidence, extraction_confidence,
                 needs_manual_review, is_hidden, source_view_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                video_id,
                product.get("name"),
                price,  # 공식 가격 fallback 적용
                product.get("category"),
                product.get("reason"),
                product.get("recommendation_quote"),
                product.get("timestamp"),
                self._format_timestamp(product.get("timestamp")),
                keywords,
                product.get("store_key"),
                product.get("store_name"),
                product.get("video_start_sec") or product.get("timestamp"),  # 시작 시간 (없으면 timestamp 사용)
                product.get("video_end_sec"),  # 끝 시간
                video_url,
                official.get("product_code") or official.get("product_no"),
                official.get("official_name") or official.get("name"),
                official.get("official_price") or official.get("price"),
                official.get("image_url"),
                official.get("product_url"),
                official.get("description", ""),
                official.get("category", ""),
                is_matched,
                official.get("score", 0),
                official.get("confidence", 0),
                product.get("confidence", 0),
                1 if product.get("needs_manual_review") or official.get("needs_manual_review") else 0,
                is_hidden,  # 카탈로그 매칭 안 되면 숨김
                product.get("source_view_count", 0),
            ))
            self.conn.commit()

            if cursor.rowcount > 0:
                return cursor.lastrowid
            else:
                return None  # 중복으로 무시됨

        except sqlite3.IntegrityError:
            # 중복 삽입 시도
            return None
        except Exception as e:
            print(f"상품 저장 오류: {e}")
            return None

    def _format_timestamp(self, seconds: int) -> Optional[str]:
        """초를 MM:SS 형식으로 변환"""
        if seconds is None:
            return None
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    # ========== 제너릭 카탈로그 메서드 ==========

    def insert_catalog_product(self, store_key: str, product: dict) -> bool:
        """
        제너릭 카탈로그 상품 저장 (upsert)

        Args:
            store_key: 매장 키 (daiso, costco, oliveyoung, coupang, traders, ikea, convenience)
            product: 상품 데이터 딕셔너리

        Returns:
            성공 여부
        """
        config = CATALOG_CONFIG.get(store_key)
        if not config:
            print(f"알 수 없는 매장: {store_key}")
            return False

        cursor = self.conn.cursor()
        table = config["table"]
        columns = config["columns"]
        update_columns = config["update_columns"]
        bool_columns = config.get("bool_columns", [])

        # 값 추출 및 bool 변환
        values = []
        for col in columns:
            val = product.get(col, "" if col == "keywords" else None)
            if col in bool_columns:
                val = 1 if val else 0
            elif val is None and col not in ["price", "original_price", "rating", "review_count"]:
                val = ""
            values.append(val)

        # ON CONFLICT 절 생성
        if config.get("composite_key"):
            conflict_cols = ", ".join(config["composite_key"])
        else:
            conflict_cols = config["id_column"]

        update_set = ", ".join([f"{col} = excluded.{col}" for col in update_columns])
        update_set += ", updated_at = CURRENT_TIMESTAMP"

        placeholders = ", ".join(["?"] * len(columns))
        columns_str = ", ".join(columns)

        query = f"""
            INSERT INTO {table}
            ({columns_str}, updated_at)
            VALUES ({placeholders}, CURRENT_TIMESTAMP)
            ON CONFLICT({conflict_cols}) DO UPDATE SET
                {update_set}
        """

        try:
            cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"{store_key} 상품 저장 오류: {e}")
            return False

    def insert_catalog_products_batch(self, store_key: str, products: List[dict]) -> int:
        """
        카탈로그 상품 배치 저장

        Args:
            store_key: 매장 키
            products: 상품 리스트

        Returns:
            저장된 상품 수
        """
        count = 0
        for product in products:
            if self.insert_catalog_product(store_key, product):
                count += 1
        return count

    def search_catalog(self, store_key: str, keyword: str, limit: int = 20) -> list:
        """
        카탈로그 검색

        Args:
            store_key: 매장 키
            keyword: 검색 키워드
            limit: 결과 제한

        Returns:
            검색 결과 리스트
        """
        config = CATALOG_CONFIG.get(store_key)
        if not config:
            return []

        cursor = self.conn.cursor()
        table = config["table"]
        search_term = f"%{keyword}%"

        # 브랜드 컬럼이 있으면 포함
        if "brand" in config["columns"]:
            query = f"""
                SELECT * FROM {table}
                WHERE name LIKE ? OR brand LIKE ? OR keywords LIKE ?
                ORDER BY review_count DESC
                LIMIT ?
            """
            cursor.execute(query, (search_term, search_term, search_term, limit))
        else:
            query = f"""
                SELECT * FROM {table}
                WHERE name LIKE ? OR keywords LIKE ?
                ORDER BY review_count DESC
                LIMIT ?
            """
            cursor.execute(query, (search_term, search_term, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_catalog_all(self, store_key: str) -> list:
        """카탈로그 전체 조회"""
        config = CATALOG_CONFIG.get(store_key)
        if not config:
            return []

        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {config['table']} ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_catalog_count(self, store_key: str) -> int:
        """카탈로그 상품 수 조회"""
        config = CATALOG_CONFIG.get(store_key)
        if not config:
            return 0

        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {config['table']}")
        return cursor.fetchone()[0]

    def get_products_by_store(self, store_key: str, approved_only: bool = True,
                               limit: int = 100, offset: int = 0) -> list:
        """매장별 상품 조회"""
        cursor = self.conn.cursor()
        query = """
            SELECT p.*, v.title as video_title, v.channel_title,
                   v.thumbnail_url, v.view_count as video_view_count
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
        """승인 대기 상품 조회 (수동 검토 필요 우선)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.*, v.title as video_title, v.channel_title, v.thumbnail_url
            FROM products p
            JOIN videos v ON p.video_id = v.video_id
            WHERE p.is_approved = 0 AND p.is_hidden = 0
            ORDER BY p.needs_manual_review DESC, p.extraction_confidence DESC,
                     p.source_view_count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_products_needing_review(self, limit: int = 50) -> list:
        """수동 검토 필요 상품 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.*, v.title as video_title, v.channel_title, v.thumbnail_url
            FROM products p
            JOIN videos v ON p.video_id = v.video_id
            WHERE p.needs_manual_review = 1 AND p.is_hidden = 0
            ORDER BY p.source_view_count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def approve_product(self, product_id: int):
        """상품 승인"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE products
            SET is_approved = 1, needs_manual_review = 0, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), product_id))
        self.conn.commit()

    def hide_product(self, product_id: int):
        """상품 숨김"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE products
            SET is_hidden = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), product_id))
        self.conn.commit()

    def check_duplicate_product(self, video_id: str, name: str, price: int = None) -> bool:
        """상품 중복 확인"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id FROM products
            WHERE video_id = ? AND name = ? AND COALESCE(price, 0) = ?
        """, (video_id, name, price or 0))
        return cursor.fetchone() is not None

    # ========== 품질 로그 ==========

    def log_quality_metrics(
        self,
        video_id: str,
        transcript_length: int,
        transcript_quality_score: float,
        products_extracted: int,
        products_matched: int,
        avg_extraction_confidence: float,
        avg_match_confidence: float,
        processing_time_sec: float,
    ):
        """품질 메트릭 로깅"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO quality_logs
            (video_id, transcript_length, transcript_quality_score,
             products_extracted, products_matched,
             avg_extraction_confidence, avg_match_confidence, processing_time_sec)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video_id, transcript_length, transcript_quality_score,
            products_extracted, products_matched,
            avg_extraction_confidence, avg_match_confidence, processing_time_sec,
        ))
        self.conn.commit()

    def get_quality_stats(self) -> dict:
        """품질 통계 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_processed,
                AVG(transcript_quality_score) as avg_transcript_quality,
                SUM(products_extracted) as total_extracted,
                SUM(products_matched) as total_matched,
                AVG(avg_extraction_confidence) as avg_extraction_conf,
                AVG(avg_match_confidence) as avg_match_conf,
                AVG(processing_time_sec) as avg_processing_time
            FROM quality_logs
        """)
        row = cursor.fetchone()
        return dict(row) if row else {}

    # ========== 다이소 카탈로그 (하위 호환) ==========

    def insert_daiso_product(self, product: dict) -> bool:
        """다이소몰 상품 저장 (제너릭 메서드 사용)"""
        return self.insert_catalog_product("daiso", product)

    def search_daiso_catalog(self, keyword: str, limit: int = 20) -> list:
        """다이소 카탈로그에서 상품 검색"""
        return self.search_catalog("daiso", keyword, limit)

    def get_daiso_catalog_all(self) -> list:
        """다이소 카탈로그 전체 조회"""
        return self.get_catalog_all("daiso")

    # ========== 코스트코 카탈로그 (하위 호환) ==========

    def insert_costco_product(self, product: dict) -> bool:
        """코스트코 상품 저장 (제너릭 메서드 사용)"""
        return self.insert_catalog_product("costco", product)

    def search_costco_catalog(self, keyword: str, limit: int = 20) -> list:
        """코스트코 카탈로그에서 상품 검색"""
        return self.search_catalog("costco", keyword, limit)

    def get_costco_catalog_all(self) -> list:
        """코스트코 카탈로그 전체 조회"""
        return self.get_catalog_all("costco")

    def get_costco_catalog_count(self) -> int:
        """코스트코 카탈로그 상품 수"""
        return self.get_catalog_count("costco")

    # ========== 올리브영 카탈로그 (하위 호환) ==========

    def insert_oliveyoung_product(self, product: dict) -> bool:
        """올리브영 상품 저장 (제너릭 메서드 사용)"""
        return self.insert_catalog_product("oliveyoung", product)

    def search_oliveyoung_catalog(self, keyword: str, limit: int = 20) -> list:
        """올리브영 카탈로그에서 상품 검색"""
        return self.search_catalog("oliveyoung", keyword, limit)

    def get_oliveyoung_catalog_all(self) -> list:
        """올리브영 카탈로그 전체 조회"""
        return self.get_catalog_all("oliveyoung")

    def get_oliveyoung_catalog_count(self) -> int:
        """올리브영 카탈로그 상품 수"""
        return self.get_catalog_count("oliveyoung")

    # ========== 쿠팡 카탈로그 (하위 호환) ==========

    def insert_coupang_product(self, product: dict) -> bool:
        """쿠팡 상품 저장 (제너릭 메서드 사용)"""
        return self.insert_catalog_product("coupang", product)

    def search_coupang_catalog(self, keyword: str, limit: int = 20) -> list:
        """쿠팡 카탈로그에서 상품 검색"""
        return self.search_catalog("coupang", keyword, limit)

    def get_coupang_catalog_all(self) -> list:
        """쿠팡 카탈로그 전체 조회"""
        return self.get_catalog_all("coupang")

    def get_coupang_catalog_count(self) -> int:
        """쿠팡 카탈로그 상품 수"""
        return self.get_catalog_count("coupang")

    # ========== 트레이더스 카탈로그 (하위 호환) ==========

    def insert_traders_product(self, product: dict) -> bool:
        """트레이더스 상품 저장 (제너릭 메서드 사용)"""
        return self.insert_catalog_product("traders", product)

    def get_traders_catalog_count(self) -> int:
        """트레이더스 카탈로그 상품 수"""
        return self.get_catalog_count("traders")

    # ========== 이케아 카탈로그 (하위 호환) ==========

    def insert_ikea_product(self, product: dict) -> bool:
        """이케아 상품 저장 (제너릭 메서드 사용)"""
        return self.insert_catalog_product("ikea", product)

    def get_ikea_catalog_count(self) -> int:
        """이케아 카탈로그 상품 수"""
        return self.get_catalog_count("ikea")

    # ========== 편의점 카탈로그 (하위 호환) ==========

    def insert_convenience_product(self, product: dict) -> bool:
        """편의점 상품 저장 (제너릭 메서드 사용)"""
        return self.insert_catalog_product("convenience", product)

    def get_convenience_catalog_count(self, store: str = None) -> int:
        """편의점 카탈로그 상품 수"""
        cursor = self.conn.cursor()
        if store:
            cursor.execute("SELECT COUNT(*) FROM convenience_catalog WHERE store = ?", (store,))
        else:
            cursor.execute("SELECT COUNT(*) FROM convenience_catalog")
        return cursor.fetchone()[0]

    def get_convenience_catalog_by_store(self, store: str) -> list:
        """편의점별 카탈로그 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM convenience_catalog WHERE store = ? ORDER BY updated_at DESC", (store,))
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

        # needs_manual_review 컬럼이 없을 수 있으므로 안전하게 처리
        try:
            cursor.execute("SELECT COUNT(*) FROM products WHERE needs_manual_review = 1 AND is_hidden = 0")
            needs_review = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            needs_review = 0

        # is_matched 컬럼도 안전하게 처리
        try:
            cursor.execute("SELECT COUNT(*) FROM products WHERE is_matched = 1")
            matched_products = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            matched_products = 0

        cursor.execute("""
            SELECT store_key, COUNT(*) as count
            FROM products
            WHERE is_approved = 1
            GROUP BY store_key
        """)
        by_store = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM products
            WHERE is_approved = 1
            GROUP BY category
        """)
        by_category = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_videos": total_videos,
            "total_products": total_products,
            "approved_products": approved_products,
            "pending_products": pending_products,
            "needs_review": needs_review,
            "matched_products": matched_products,
            "by_store": by_store,
            "by_category": by_category,
        }

    def close(self):
        """연결 종료"""
        if self.conn:
            self.conn.close()


def main():
    """테스트 실행"""
    db = ImprovedDatabase()

    print("=== 개선된 데이터베이스 테스트 ===\n")

    # 테스트 데이터 삽입
    test_video = {
        "video_id": "test_improved_001",
        "title": "다이소 꿀템 10가지",
        "channel_id": "UC123",
        "channel_title": "테스트 채널",
        "published_at": "2024-01-01T00:00:00Z",
        "view_count": 100000,
        "store_key": "daiso",
        "store_name": "다이소",
    }
    db.insert_video(test_video)

    # 상품 삽입 테스트 (중복 확인)
    test_product = {
        "video_id": "test_improved_001",
        "name": "스텐 배수구망",
        "price": 2000,
        "category": "주방",
        "reason": "물때가 안 껴요",
        "recommendation_quote": "진짜 이거 없으면 주방 청소 못해요",
        "timestamp": 120,
        "confidence": 0.95,
        "store_key": "daiso",
        "store_name": "다이소",
        "source_view_count": 100000,
        "official": {
            "product_code": "12345678",
            "official_name": "스테인레스 배수구망",
            "official_price": 2000,
            "matched": True,
            "score": 85,
            "confidence": 0.9,
        },
    }

    result1 = db.insert_product(test_product)
    print(f"첫 번째 삽입: {result1}")

    # 중복 삽입 시도
    result2 = db.insert_product(test_product)
    print(f"중복 삽입 시도: {result2 or '무시됨 (중복)'}")

    # 다른 상품 삽입
    test_product2 = test_product.copy()
    test_product2["name"] = "실리콘 주걱"
    test_product2["price"] = 3000
    result3 = db.insert_product(test_product2)
    print(f"다른 상품 삽입: {result3}")

    # 통계 출력
    stats = db.get_stats()
    print(f"\n=== 통계 ===")
    print(f"총 영상: {stats['total_videos']}")
    print(f"총 상품: {stats['total_products']}")
    print(f"승인 대기: {stats['pending_products']}")
    print(f"수동 검토 필요: {stats['needs_review']}")

    db.close()


if __name__ == "__main__":
    main()
