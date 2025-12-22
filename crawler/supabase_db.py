# -*- coding: utf-8 -*-
"""
Supabase 데이터베이스 연동
프로덕션 환경을 위한 클라우드 DB 연동 모듈

설정:
1. https://supabase.com/ 에서 프로젝트 생성
2. Settings > API 에서 URL과 anon key 복사
3. .env 파일에 추가:
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_KEY=eyJxxx...
"""
import os
import json
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Supabase 클라이언트
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("supabase 패키지 미설치: pip install supabase")


class SupabaseDB:
    """Supabase 데이터베이스 클래스"""

    # 테이블 생성 SQL (Supabase SQL Editor에서 실행)
    SCHEMA_SQL = """
    -- 영상 테이블
    CREATE TABLE IF NOT EXISTS videos (
        id BIGSERIAL PRIMARY KEY,
        video_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        channel_id TEXT,
        channel_title TEXT,
        published_at TIMESTAMPTZ,
        thumbnail_url TEXT,
        view_count INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        store_key TEXT,
        store_name TEXT,
        transcript TEXT,
        processed_at TIMESTAMPTZ,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- 상품 테이블
    CREATE TABLE IF NOT EXISTS products (
        id BIGSERIAL PRIMARY KEY,
        video_id TEXT NOT NULL,
        name TEXT NOT NULL,
        price INTEGER,
        category TEXT,
        reason TEXT,
        timestamp_sec INTEGER,
        keywords JSONB,
        store_key TEXT,
        store_name TEXT,
        channel_title TEXT,

        -- 공식 매장 정보
        official_code TEXT,
        official_name TEXT,
        official_price INTEGER,
        official_image_url TEXT,
        official_product_url TEXT,
        is_matched BOOLEAN DEFAULT FALSE,

        -- 메타 정보
        is_approved BOOLEAN DEFAULT FALSE,
        is_hidden BOOLEAN DEFAULT FALSE,
        source_view_count INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- 다이소 카탈로그
    CREATE TABLE IF NOT EXISTS daiso_catalog (
        id BIGSERIAL PRIMARY KEY,
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
        is_new BOOLEAN DEFAULT FALSE,
        is_best BOOLEAN DEFAULT FALSE,
        sold_out BOOLEAN DEFAULT FALSE,
        keywords TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- SNS 게시물
    CREATE TABLE IF NOT EXISTS sns_posts (
        id BIGSERIAL PRIMARY KEY,
        post_id TEXT UNIQUE NOT NULL,
        platform TEXT NOT NULL,
        author TEXT,
        author_id TEXT,
        content TEXT,
        image_urls JSONB,
        video_url TEXT,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        posted_at TIMESTAMPTZ,
        url TEXT,
        hashtags JSONB,
        store_key TEXT,
        store_name TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- 인덱스
    CREATE INDEX IF NOT EXISTS idx_videos_store ON videos(store_key);
    CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_key);
    CREATE INDEX IF NOT EXISTS idx_products_approved ON products(is_approved);
    CREATE INDEX IF NOT EXISTS idx_daiso_catalog_name ON daiso_catalog(name);
    CREATE INDEX IF NOT EXISTS idx_sns_posts_platform ON sns_posts(platform, store_key);
    """

    def __init__(self, url: str = None, key: str = None):
        """
        Args:
            url: Supabase 프로젝트 URL
            key: Supabase anon key
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase 패키지를 설치하세요: pip install supabase")

        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "Supabase 설정 필요:\n"
                "1. .env 파일에 추가:\n"
                "   SUPABASE_URL=https://xxx.supabase.co\n"
                "   SUPABASE_KEY=eyJxxx...\n"
                "2. 또는 생성자에 직접 전달"
            )

        self.client: Client = create_client(self.url, self.key)
        print(f"[Supabase] 연결됨: {self.url[:30]}...")

    # ========== 영상 관련 ==========

    def insert_video(self, video: dict) -> bool:
        """영상 정보 저장 (upsert)"""
        try:
            data = {
                "video_id": video.get("video_id"),
                "title": video.get("title"),
                "channel_id": video.get("channel_id"),
                "channel_title": video.get("channel_title"),
                "published_at": video.get("published_at"),
                "thumbnail_url": video.get("thumbnail_url"),
                "view_count": video.get("view_count", 0),
                "like_count": video.get("like_count", 0),
                "store_key": video.get("store_key"),
                "store_name": video.get("store_name"),
            }

            result = self.client.table("videos").upsert(
                data,
                on_conflict="video_id"
            ).execute()

            return len(result.data) > 0

        except Exception as e:
            print(f"영상 저장 오류: {e}")
            return False

    def update_video_transcript(self, video_id: str, transcript: str):
        """자막 저장"""
        self.client.table("videos").update({
            "transcript": transcript,
            "processed_at": datetime.now().isoformat(),
            "status": "transcribed"
        }).eq("video_id", video_id).execute()

    def update_video_status(self, video_id: str, status: str):
        """영상 상태 업데이트"""
        self.client.table("videos").update({
            "status": status
        }).eq("video_id", video_id).execute()

    def get_pending_videos(self, limit: int = 10) -> list:
        """처리 대기 영상 조회"""
        result = self.client.table("videos").select("*").eq(
            "status", "pending"
        ).order(
            "view_count", desc=True
        ).limit(limit).execute()

        return result.data

    # ========== 상품 관련 ==========

    def insert_product(self, product: dict) -> int:
        """상품 정보 저장"""
        try:
            official = product.get("official", {})

            data = {
                "video_id": product.get("video_id"),
                "name": product.get("name"),
                "price": product.get("price"),
                "category": product.get("category"),
                "reason": product.get("reason"),
                "timestamp_sec": product.get("timestamp"),
                "keywords": product.get("keywords", []),
                "store_key": product.get("store_key"),
                "store_name": product.get("store_name"),
                "channel_title": product.get("channel_title"),
                "official_code": official.get("product_code"),
                "official_name": official.get("official_name"),
                "official_price": official.get("official_price"),
                "official_image_url": official.get("image_url"),
                "official_product_url": official.get("product_url"),
                "is_matched": bool(official.get("matched")),
                "source_view_count": product.get("source_view_count", 0),
            }

            result = self.client.table("products").insert(data).execute()
            return result.data[0]["id"] if result.data else 0

        except Exception as e:
            print(f"상품 저장 오류: {e}")
            return 0

    def get_products_by_store(self, store_key: str, approved_only: bool = True,
                               limit: int = 100, offset: int = 0) -> list:
        """매장별 상품 조회"""
        query = self.client.table("products").select(
            "*, videos(title, channel_title, view_count)"
        ).eq("store_key", store_key).eq("is_hidden", False)

        if approved_only:
            query = query.eq("is_approved", True)

        result = query.order(
            "source_view_count", desc=True
        ).range(offset, offset + limit - 1).execute()

        return result.data

    def get_pending_products(self, limit: int = 50) -> list:
        """승인 대기 상품 조회"""
        result = self.client.table("products").select(
            "*, videos(title, channel_title, thumbnail_url)"
        ).eq("is_approved", False).eq("is_hidden", False).order(
            "source_view_count", desc=True
        ).limit(limit).execute()

        return result.data

    def approve_product(self, product_id: int):
        """상품 승인"""
        self.client.table("products").update({
            "is_approved": True,
            "updated_at": datetime.now().isoformat()
        }).eq("id", product_id).execute()

    def hide_product(self, product_id: int):
        """상품 숨김"""
        self.client.table("products").update({
            "is_hidden": True,
            "updated_at": datetime.now().isoformat()
        }).eq("id", product_id).execute()

    # ========== 다이소 카탈로그 ==========

    def insert_daiso_product(self, product: dict) -> bool:
        """다이소 상품 저장 (upsert)"""
        try:
            data = {
                "product_no": product.get("product_no"),
                "name": product.get("name"),
                "price": product.get("price"),
                "image_url": product.get("image_url"),
                "product_url": product.get("product_url"),
                "category": product.get("category"),
                "category_large": product.get("category_large"),
                "category_middle": product.get("category_middle"),
                "category_small": product.get("category_small"),
                "rating": product.get("rating", 0),
                "review_count": product.get("review_count", 0),
                "order_count": product.get("order_count", 0),
                "is_new": product.get("is_new", False),
                "is_best": product.get("is_best", False),
                "sold_out": product.get("sold_out", False),
                "keywords": product.get("keywords", ""),
                "updated_at": datetime.now().isoformat()
            }

            self.client.table("daiso_catalog").upsert(
                data,
                on_conflict="product_no"
            ).execute()

            return True

        except Exception as e:
            print(f"다이소 상품 저장 오류: {e}")
            return False

    def search_daiso_catalog(self, keyword: str, limit: int = 20) -> list:
        """다이소 카탈로그 검색"""
        result = self.client.table("daiso_catalog").select("*").ilike(
            "name", f"%{keyword}%"
        ).order(
            "order_count", desc=True
        ).limit(limit).execute()

        return result.data

    # ========== SNS 게시물 ==========

    def insert_sns_post(self, post: dict) -> bool:
        """SNS 게시물 저장"""
        try:
            data = {
                "post_id": post.get("post_id"),
                "platform": post.get("platform"),
                "author": post.get("author"),
                "author_id": post.get("author_id"),
                "content": post.get("content"),
                "image_urls": post.get("image_urls", []),
                "video_url": post.get("video_url"),
                "likes": post.get("likes", 0),
                "comments": post.get("comments", 0),
                "shares": post.get("shares", 0),
                "posted_at": post.get("posted_at"),
                "url": post.get("url"),
                "hashtags": post.get("hashtags", []),
                "store_key": post.get("store_key"),
                "store_name": post.get("store_name"),
            }

            self.client.table("sns_posts").upsert(
                data,
                on_conflict="post_id"
            ).execute()

            return True

        except Exception as e:
            print(f"SNS 게시물 저장 오류: {e}")
            return False

    # ========== 통계 ==========

    def get_stats(self) -> dict:
        """전체 통계 조회"""
        videos = self.client.table("videos").select("id", count="exact").execute()
        products = self.client.table("products").select("id", count="exact").execute()
        approved = self.client.table("products").select("id", count="exact").eq(
            "is_approved", True
        ).execute()
        pending = self.client.table("products").select("id", count="exact").eq(
            "is_approved", False
        ).eq("is_hidden", False).execute()

        return {
            "total_videos": videos.count or 0,
            "total_products": products.count or 0,
            "approved_products": approved.count or 0,
            "pending_products": pending.count or 0,
        }


def migrate_from_sqlite(sqlite_path: str, supabase_db: SupabaseDB):
    """SQLite에서 Supabase로 데이터 마이그레이션"""
    import sqlite3

    print(f"마이그레이션 시작: {sqlite_path}")

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 영상 마이그레이션
    print("영상 마이그레이션...")
    cursor.execute("SELECT * FROM videos")
    videos = [dict(row) for row in cursor.fetchall()]
    for video in videos:
        supabase_db.insert_video(video)
    print(f"  -> {len(videos)}개 영상")

    # 2. 상품 마이그레이션
    print("상품 마이그레이션...")
    cursor.execute("SELECT * FROM products")
    products = [dict(row) for row in cursor.fetchall()]
    for product in products:
        supabase_db.insert_product(product)
    print(f"  -> {len(products)}개 상품")

    # 3. 다이소 카탈로그 마이그레이션
    print("다이소 카탈로그 마이그레이션...")
    cursor.execute("SELECT * FROM daiso_catalog")
    catalog = [dict(row) for row in cursor.fetchall()]
    for item in catalog:
        supabase_db.insert_daiso_product(item)
    print(f"  -> {len(catalog)}개 상품")

    conn.close()
    print("마이그레이션 완료!")


def test_connection():
    """연결 테스트"""
    try:
        db = SupabaseDB()
        stats = db.get_stats()
        print(f"\n연결 성공!")
        print(f"총 영상: {stats['total_videos']}")
        print(f"총 상품: {stats['total_products']}")
    except Exception as e:
        print(f"연결 실패: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        # python supabase_db.py migrate data/products.db
        sqlite_path = sys.argv[2] if len(sys.argv) > 2 else "data/products.db"
        db = SupabaseDB()
        migrate_from_sqlite(sqlite_path, db)
    else:
        test_connection()
