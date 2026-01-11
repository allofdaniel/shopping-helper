# -*- coding: utf-8 -*-
"""
GenericScraper 테스트
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper_configs import (
    StoreConfig, StoreSelectors, get_store_config,
    COSTCO_CONFIG, IKEA_CONFIG, STORE_CONFIGS
)
from generic_scraper import Product, GenericScraper


class TestProduct:
    """Product 데이터클래스 테스트"""

    def test_product_creation(self):
        """기본 생성 테스트"""
        product = Product(
            product_id="12345",
            name="테스트 상품",
            store="costco",
            price=10000
        )
        assert product.product_id == "12345"
        assert product.name == "테스트 상품"
        assert product.store == "costco"
        assert product.price == 10000
        assert product.original_price == 0

    def test_product_to_dict(self):
        """딕셔너리 변환 테스트"""
        product = Product(
            product_id="12345",
            name="테스트 상품",
            store="costco",
            price=10000,
            is_sale=True,
            event_type="1+1"
        )
        d = product.to_dict()

        assert d["product_id"] == "12345"
        assert d["name"] == "테스트 상품"
        assert d["is_sale"] == True
        assert d["event_type"] == "1+1"

    def test_product_optional_fields_excluded_when_empty(self):
        """빈 확장 필드는 제외됨"""
        product = Product(
            product_id="12345",
            name="테스트",
            store="costco"
        )
        d = product.to_dict()

        assert "event_type" not in d
        assert "type_name" not in d
        assert "is_best" not in d


class TestStoreConfigs:
    """스토어 설정 테스트"""

    def test_get_store_config(self):
        """스토어 설정 조회"""
        config = get_store_config("costco")
        assert config is not None
        assert config.name == "코스트코"
        assert config.code == "costco"

    def test_get_store_config_case_insensitive(self):
        """대소문자 구분 없이 조회"""
        config1 = get_store_config("COSTCO")
        config2 = get_store_config("Costco")
        assert config1 is not None
        assert config2 is not None

    def test_get_unknown_store_returns_none(self):
        """없는 스토어는 None 반환"""
        config = get_store_config("unknown_store")
        assert config is None

    def test_all_configs_have_required_fields(self):
        """모든 설정에 필수 필드 존재"""
        for code, config in STORE_CONFIGS.items():
            assert config.name, f"{code}: name 필수"
            assert config.code, f"{code}: code 필수"
            assert config.base_url, f"{code}: base_url 필수"
            assert config.search_url, f"{code}: search_url 필수"
            assert len(config.selectors.product_list) > 0, f"{code}: product_list 필수"

    def test_event_stores_marked_correctly(self):
        """편의점은 is_event_store=True"""
        event_stores = ["cu", "gs25", "seveneleven", "emart24"]
        for code in event_stores:
            config = get_store_config(code)
            assert config.is_event_store, f"{code}은 이벤트 스토어여야 함"

        non_event_stores = ["costco", "ikea", "oliveyoung"]
        for code in non_event_stores:
            config = get_store_config(code)
            assert not config.is_event_store, f"{code}은 일반 스토어여야 함"


class TestGenericScraper:
    """GenericScraper 테스트"""

    def test_init_with_store_code(self):
        """스토어 코드로 초기화"""
        # Playwright 없이 테스트하기 위해 mock
        with patch('base_scraper.PLAYWRIGHT_AVAILABLE', False):
            with pytest.raises(RuntimeError):
                GenericScraper("costco")

    def test_init_with_invalid_store_code(self):
        """잘못된 스토어 코드"""
        with pytest.raises(ValueError, match="Unknown store code"):
            GenericScraper("invalid_store")

    def test_init_requires_store_code_or_config(self):
        """스토어 코드 또는 설정 필수"""
        with pytest.raises(ValueError):
            GenericScraper()

    def test_from_config_classmethod(self):
        """from_config 클래스 메서드"""
        with patch('base_scraper.PLAYWRIGHT_AVAILABLE', False):
            with pytest.raises(RuntimeError):
                GenericScraper.from_config(COSTCO_CONFIG)


class TestParseScript:
    """JavaScript 파싱 스크립트 생성 테스트"""

    def test_build_parse_script_costco(self):
        """코스트코 파싱 스크립트 생성"""
        # GenericScraper 초기화 없이 메서드만 테스트
        scraper = object.__new__(GenericScraper)
        scraper.store_config = COSTCO_CONFIG

        script = scraper._build_parse_script()

        assert "costco" in script.lower()
        assert ".product-list-item" in script
        assert ".product-name" in script

    def test_build_parse_script_contains_selectors(self):
        """파싱 스크립트에 셀렉터 포함"""
        with patch('base_scraper.PLAYWRIGHT_AVAILABLE', True):
            scraper = object.__new__(GenericScraper)
            scraper.store_config = IKEA_CONFIG

            script = scraper._build_parse_script()

            assert "pip-product-compact" in script
            assert "pip-header-section__title" in script


class TestProductEquality:
    """상품 비교 테스트"""

    def test_products_with_same_id_are_deduplicated(self):
        """같은 ID의 상품 중복 제거"""
        products = [
            Product(product_id="123", name="상품1", store="test"),
            Product(product_id="123", name="상품1 복사", store="test"),
            Product(product_id="456", name="상품2", store="test"),
        ]

        seen = set()
        unique = []
        for p in products:
            if p.product_id not in seen:
                seen.add(p.product_id)
                unique.append(p)

        assert len(unique) == 2
        assert unique[0].product_id == "123"
        assert unique[1].product_id == "456"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
