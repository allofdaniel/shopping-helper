# -*- coding: utf-8 -*-
"""
개선된 데이터베이스 모듈 테스트
"""
import pytest
import sys
import os
import tempfile
from pathlib import Path

# 상위 디렉토리 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from improved_database import ImprovedDatabase, CATALOG_CONFIG


@pytest.fixture
def temp_db():
    """임시 데이터베이스 생성"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = ImprovedDatabase(db_path)
    yield db

    db.close()
    try:
        os.unlink(db_path)
    except:
        pass


class TestCatalogConfig:
    """카탈로그 설정 테스트"""

    def test_all_stores_configured(self):
        """모든 매장이 설정되어 있는지"""
        expected_stores = ["daiso", "costco", "oliveyoung", "coupang", "traders", "ikea", "convenience"]
        for store in expected_stores:
            assert store in CATALOG_CONFIG, f"{store} not in CATALOG_CONFIG"

    def test_config_has_required_keys(self):
        """각 설정에 필수 키가 있는지"""
        required_keys = ["table", "id_column", "columns", "update_columns"]

        for store, config in CATALOG_CONFIG.items():
            for key in required_keys:
                assert key in config, f"{store} missing {key}"


class TestGenericCatalogMethods:
    """제너릭 카탈로그 메서드 테스트"""

    def test_insert_daiso_product(self, temp_db):
        """다이소 상품 삽입"""
        product = {
            "product_no": "12345678",
            "name": "스테인레스 배수구망",
            "price": 2000,
            "image_url": "https://example.com/image.jpg",
            "product_url": "https://daisomall.co.kr/12345678",
            "category": "주방",
            "category_large": "생활",
            "category_middle": "주방용품",
            "category_small": "싱크대용품",
        }

        result = temp_db.insert_catalog_product("daiso", product)
        assert result is True

        # 조회
        count = temp_db.get_catalog_count("daiso")
        assert count == 1

    def test_insert_costco_product(self, temp_db):
        """코스트코 상품 삽입"""
        product = {
            "product_code": "1234567",
            "name": "커클랜드 견과류",
            "price": 25000,
            "image_url": "https://example.com/image.jpg",
            "product_url": "https://costco.co.kr/1234567",
        }

        result = temp_db.insert_catalog_product("costco", product)
        assert result is True
        assert temp_db.get_catalog_count("costco") == 1

    def test_insert_oliveyoung_product(self, temp_db):
        """올리브영 상품 삽입"""
        product = {
            "product_code": "A000000001",
            "name": "라운드랩 독도 토너",
            "brand": "라운드랩",
            "price": 15000,
            "original_price": 20000,
            "is_sale": True,
        }

        result = temp_db.insert_catalog_product("oliveyoung", product)
        assert result is True

    def test_insert_coupang_product(self, temp_db):
        """쿠팡 상품 삽입"""
        product = {
            "product_id": "12345678901",
            "name": "맥심 모카골드",
            "price": 8900,
            "is_rocket": True,
            "is_rocket_fresh": False,
        }

        result = temp_db.insert_catalog_product("coupang", product)
        assert result is True

    def test_insert_traders_product(self, temp_db):
        """트레이더스 상품 삽입"""
        product = {
            "item_id": "123456",
            "name": "트레이더스 물티슈",
            "brand": "트레이더스",
            "price": 5000,
        }

        result = temp_db.insert_catalog_product("traders", product)
        assert result is True

    def test_insert_ikea_product(self, temp_db):
        """이케아 상품 삽입"""
        product = {
            "product_id": "12345678",
            "name": "LACK",
            "type_name": "사이드 테이블",
            "price": 9900,
            "color": "화이트",
        }

        result = temp_db.insert_catalog_product("ikea", product)
        assert result is True

    def test_insert_convenience_product(self, temp_db):
        """편의점 상품 삽입"""
        product = {
            "product_id": "C001",
            "store": "cu",
            "name": "CU 삼각김밥",
            "price": 1200,
            "event_type": "1+1",
            "is_new": True,
        }

        result = temp_db.insert_catalog_product("convenience", product)
        assert result is True

    def test_upsert_updates_existing(self, temp_db):
        """기존 상품 업데이트 (upsert)"""
        product = {
            "product_no": "12345678",
            "name": "스테인레스 배수구망",
            "price": 2000,
        }

        # 첫 삽입
        temp_db.insert_catalog_product("daiso", product)
        assert temp_db.get_catalog_count("daiso") == 1

        # 가격 변경 후 재삽입 (upsert)
        product["price"] = 2500
        temp_db.insert_catalog_product("daiso", product)

        # 개수는 그대로
        assert temp_db.get_catalog_count("daiso") == 1

    def test_batch_insert(self, temp_db):
        """배치 삽입"""
        products = [
            {"product_no": "001", "name": "상품1", "price": 1000},
            {"product_no": "002", "name": "상품2", "price": 2000},
            {"product_no": "003", "name": "상품3", "price": 3000},
        ]

        count = temp_db.insert_catalog_products_batch("daiso", products)
        assert count == 3
        assert temp_db.get_catalog_count("daiso") == 3

    def test_search_catalog(self, temp_db):
        """카탈로그 검색"""
        products = [
            {"product_no": "001", "name": "스테인레스 배수구망", "price": 2000},
            {"product_no": "002", "name": "플라스틱 배수구망", "price": 1000},
            {"product_no": "003", "name": "실리콘 주걱", "price": 3000},
        ]
        temp_db.insert_catalog_products_batch("daiso", products)

        # 검색
        results = temp_db.search_catalog("daiso", "배수구망")
        assert len(results) == 2

    def test_invalid_store_returns_false(self, temp_db):
        """잘못된 매장 키는 False 반환"""
        product = {"name": "Test", "price": 1000}
        result = temp_db.insert_catalog_product("invalid_store", product)
        assert result is False


class TestBackwardCompatibility:
    """하위 호환성 테스트"""

    def test_legacy_daiso_methods(self, temp_db):
        """기존 다이소 메서드 동작"""
        product = {
            "product_no": "12345678",
            "name": "테스트 상품",
            "price": 2000,
        }

        # 기존 메서드 사용
        result = temp_db.insert_daiso_product(product)
        assert result is True

        results = temp_db.search_daiso_catalog("테스트")
        assert len(results) >= 1

    def test_legacy_costco_methods(self, temp_db):
        """기존 코스트코 메서드 동작"""
        product = {
            "product_code": "1234567",
            "name": "테스트 상품",
            "price": 25000,
        }

        result = temp_db.insert_costco_product(product)
        assert result is True
        assert temp_db.get_costco_catalog_count() == 1

    def test_legacy_convenience_count(self, temp_db):
        """기존 편의점 메서드 동작"""
        products = [
            {"product_id": "C001", "store": "cu", "name": "상품1", "price": 1000},
            {"product_id": "C002", "store": "cu", "name": "상품2", "price": 2000},
            {"product_id": "G001", "store": "gs25", "name": "상품3", "price": 1500},
        ]

        for p in products:
            temp_db.insert_convenience_product(p)

        # 전체 개수
        assert temp_db.get_convenience_catalog_count() == 3

        # 매장별 개수
        assert temp_db.get_convenience_catalog_count("cu") == 2
        assert temp_db.get_convenience_catalog_count("gs25") == 1


class TestVideoAndProducts:
    """영상 및 상품 테스트"""

    def test_insert_video(self, temp_db):
        """영상 삽입"""
        video = {
            "video_id": "test123",
            "title": "다이소 꿀템 10가지",
            "channel_id": "UC123",
            "channel_title": "테스트 채널",
            "view_count": 100000,
            "store_key": "daiso",
            "store_name": "다이소",
        }

        result = temp_db.insert_video(video)
        assert result is True

    def test_insert_product(self, temp_db):
        """상품 삽입"""
        # 영상 먼저 삽입
        video = {"video_id": "test123", "title": "테스트", "store_key": "daiso", "store_name": "다이소"}
        temp_db.insert_video(video)

        product = {
            "video_id": "test123",
            "name": "스텐 배수구망",
            "price": 2000,
            "category": "주방",
            "store_key": "daiso",
            "store_name": "다이소",
            "official": {
                "product_code": "12345678",
                "official_name": "스테인레스 배수구망",
                "official_price": 2000,
                "matched": True,
            },
        }

        result = temp_db.insert_product(product)
        assert result is not None

    def test_duplicate_product_ignored(self, temp_db):
        """중복 상품 무시"""
        video = {"video_id": "test123", "title": "테스트", "store_key": "daiso", "store_name": "다이소"}
        temp_db.insert_video(video)

        product = {
            "video_id": "test123",
            "name": "스텐 배수구망",
            "price": 2000,
            "store_key": "daiso",
            "store_name": "다이소",
        }

        result1 = temp_db.insert_product(product)
        result2 = temp_db.insert_product(product)  # 중복

        assert result1 is not None
        assert result2 is None  # 중복 무시


class TestStats:
    """통계 테스트"""

    def test_get_stats(self, temp_db):
        """통계 조회"""
        stats = temp_db.get_stats()

        assert "total_videos" in stats
        assert "total_products" in stats
        assert "by_store" in stats

    def test_catalog_counts_in_stats(self, temp_db):
        """카탈로그 개수 통계"""
        # 상품 삽입
        temp_db.insert_catalog_product("costco", {"product_code": "1", "name": "T1", "price": 1000})
        temp_db.insert_catalog_product("costco", {"product_code": "2", "name": "T2", "price": 2000})

        # 개수 확인
        assert temp_db.get_catalog_count("costco") == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
