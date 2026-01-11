# -*- coding: utf-8 -*-
"""
스크래퍼 호환성 레이어
- 기존 스크래퍼 API와 동일한 인터페이스 제공
- 내부적으로 GenericScraper 사용
- 점진적 마이그레이션 지원
"""
from typing import List
from dataclasses import dataclass

from generic_scraper import GenericScraper, Product
from scraper_configs import get_store_config


# ============================================================
# 기존 데이터클래스 호환 (deprecated, Product 사용 권장)
# ============================================================

@dataclass
class CostcoProduct:
    """코스트코 상품 (호환용, Product 사용 권장)"""
    product_code: str
    name: str
    price: int = 0
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    unit_price: str = ""
    rating: float = 0.0
    review_count: int = 0

    @classmethod
    def from_product(cls, p: Product) -> "CostcoProduct":
        return cls(
            product_code=p.product_id,
            name=p.name,
            price=p.price,
            image_url=p.image_url,
            product_url=p.product_url,
            category=p.category,
            unit_price=p.unit_price,
            rating=p.rating,
            review_count=p.review_count,
        )

    def to_dict(self) -> dict:
        return {
            "product_code": self.product_code,
            "name": self.name,
            "price": self.price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "unit_price": self.unit_price,
            "rating": self.rating,
            "review_count": self.review_count,
        }


@dataclass
class IkeaProduct:
    """이케아 상품 (호환용, Product 사용 권장)"""
    product_id: str
    name: str
    type_name: str = ""
    price: int = 0
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    color: str = ""
    size: str = ""
    rating: float = 0.0
    review_count: int = 0

    @classmethod
    def from_product(cls, p: Product) -> "IkeaProduct":
        return cls(
            product_id=p.product_id,
            name=p.name,
            type_name=p.type_name,
            price=p.price,
            image_url=p.image_url,
            product_url=p.product_url,
            category=p.category,
            rating=p.rating,
            review_count=p.review_count,
        )

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "type_name": self.type_name,
            "price": self.price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "color": self.color,
            "size": self.size,
            "rating": self.rating,
            "review_count": self.review_count,
        }


@dataclass
class OliveyoungProduct:
    """올리브영 상품 (호환용, Product 사용 권장)"""
    product_code: str
    name: str
    brand: str = ""
    price: int = 0
    original_price: int = 0
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    rating: float = 0.0
    review_count: int = 0
    is_best: bool = False
    is_sale: bool = False

    @classmethod
    def from_product(cls, p: Product) -> "OliveyoungProduct":
        return cls(
            product_code=p.product_id,
            name=p.name,
            brand=p.brand,
            price=p.price,
            original_price=p.original_price,
            image_url=p.image_url,
            product_url=p.product_url,
            category=p.category,
            rating=p.rating,
            review_count=p.review_count,
            is_best=p.is_best,
            is_sale=p.is_sale,
        )

    def to_dict(self) -> dict:
        return {
            "product_code": self.product_code,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "original_price": self.original_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "rating": self.rating,
            "review_count": self.review_count,
            "is_best": self.is_best,
            "is_sale": self.is_sale,
        }


@dataclass
class ConvenienceProduct:
    """편의점 상품 (호환용, Product 사용 권장)"""
    product_id: str
    name: str
    price: int = 0
    original_price: int = 0
    image_url: str = ""
    product_url: str = ""
    store: str = ""
    category: str = ""
    event_type: str = ""
    is_new: bool = False
    is_pb: bool = False

    @classmethod
    def from_product(cls, p: Product) -> "ConvenienceProduct":
        return cls(
            product_id=p.product_id,
            name=p.name,
            price=p.price,
            original_price=p.original_price,
            image_url=p.image_url,
            product_url=p.product_url,
            store=p.store,
            category=p.category,
            event_type=p.event_type,
            is_new=p.is_new,
            is_pb=p.is_pb,
        )

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "price": self.price,
            "original_price": self.original_price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "store": self.store,
            "category": self.category,
            "event_type": self.event_type,
            "is_new": self.is_new,
            "is_pb": self.is_pb,
        }


# ============================================================
# 호환성 스크래퍼 클래스
# ============================================================

class CostcoScraper:
    """
    코스트코 스크래퍼 (호환용)

    기존 코드:
        scraper = CostcoScraper()
        products = await scraper.search_products("노트북")

    내부적으로 GenericScraper 사용
    """

    def __init__(self, headless: bool = True):
        self._scraper = GenericScraper("costco")
        self._scraper.config.headless = headless

    async def search_products(self, query: str, limit: int = 20) -> List[CostcoProduct]:
        products = await self._scraper.search_products(query, limit)
        return [CostcoProduct.from_product(p) for p in products]

    async def get_category_products(self, category_path: str, limit: int = 50) -> List[CostcoProduct]:
        products = await self._scraper.get_category_products(category_path, limit)
        return [CostcoProduct.from_product(p) for p in products]

    async def close(self):
        await self._scraper.close()

    async def __aenter__(self):
        await self._scraper._init_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()


class IkeaScraper:
    """이케아 스크래퍼 (호환용)"""

    def __init__(self, headless: bool = True):
        self._scraper = GenericScraper("ikea")
        self._scraper.config.headless = headless

    async def search_products(self, query: str, limit: int = 20) -> List[IkeaProduct]:
        products = await self._scraper.search_products(query, limit)
        return [IkeaProduct.from_product(p) for p in products]

    async def get_category_products(self, category_path: str, limit: int = 50) -> List[IkeaProduct]:
        products = await self._scraper.get_category_products(category_path, limit)
        return [IkeaProduct.from_product(p) for p in products]

    async def close(self):
        await self._scraper.close()

    async def __aenter__(self):
        await self._scraper._init_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()


class OliveyoungScraper:
    """올리브영 스크래퍼 (호환용)"""

    def __init__(self, headless: bool = True):
        self._scraper = GenericScraper("oliveyoung")
        self._scraper.config.headless = headless

    async def search_products(self, query: str, limit: int = 20) -> List[OliveyoungProduct]:
        products = await self._scraper.search_products(query, limit)
        return [OliveyoungProduct.from_product(p) for p in products]

    async def get_category_products(self, category_code: str, limit: int = 50) -> List[OliveyoungProduct]:
        products = await self._scraper.get_category_products(category_code, limit)
        return [OliveyoungProduct.from_product(p) for p in products]

    async def close(self):
        await self._scraper.close()

    async def __aenter__(self):
        await self._scraper._init_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()


class CUScraper:
    """CU 스크래퍼 (호환용)"""

    def __init__(self, headless: bool = True):
        self._scraper = GenericScraper("cu")
        self._scraper.config.headless = headless

    async def get_event_products(self, event_type: str = "1+1", limit: int = 30) -> List[ConvenienceProduct]:
        products = await self._scraper.get_event_products(event_type, limit)
        return [ConvenienceProduct.from_product(p) for p in products]

    async def get_new_products(self, limit: int = 30) -> List[ConvenienceProduct]:
        # 신상품은 별도 URL 필요, 현재는 이벤트 상품 반환
        products = await self._scraper.get_event_products("신상품", limit)
        for p in products:
            p.is_new = True
        return [ConvenienceProduct.from_product(p) for p in products]

    async def close(self):
        await self._scraper.close()

    async def __aenter__(self):
        await self._scraper._init_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()


class GS25Scraper:
    """GS25 스크래퍼 (호환용)"""

    def __init__(self, headless: bool = True):
        self._scraper = GenericScraper("gs25")
        self._scraper.config.headless = headless

    async def get_event_products(self, limit: int = 30) -> List[ConvenienceProduct]:
        products = await self._scraper.get_event_products("1+1", limit)
        return [ConvenienceProduct.from_product(p) for p in products]

    async def close(self):
        await self._scraper.close()

    async def __aenter__(self):
        await self._scraper._init_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()


class SevenElevenScraper:
    """세븐일레븐 스크래퍼 (호환용)"""

    def __init__(self, headless: bool = True):
        self._scraper = GenericScraper("seveneleven")
        self._scraper.config.headless = headless

    async def get_event_products(self, event_type: str = "1+1", limit: int = 30) -> List[ConvenienceProduct]:
        products = await self._scraper.get_event_products(event_type, limit)
        return [ConvenienceProduct.from_product(p) for p in products]

    async def close(self):
        await self._scraper.close()

    async def __aenter__(self):
        await self._scraper._init_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()


class Emart24Scraper:
    """이마트24 스크래퍼 (호환용)"""

    def __init__(self, headless: bool = True):
        self._scraper = GenericScraper("emart24")
        self._scraper.config.headless = headless

    async def get_event_products(self, event_type: str = "1+1", limit: int = 30) -> List[ConvenienceProduct]:
        products = await self._scraper.get_event_products(event_type, limit)
        return [ConvenienceProduct.from_product(p) for p in products]

    async def close(self):
        await self._scraper.close()

    async def __aenter__(self):
        await self._scraper._init_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()


# ============================================================
# 통합 스크래퍼 호환
# ============================================================

class ConvenienceStoreScraper:
    """편의점 통합 스크래퍼 (호환용)"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.scrapers = {
            "cu": CUScraper,
            "gs25": GS25Scraper,
            "seveneleven": SevenElevenScraper,
            "emart24": Emart24Scraper,
        }

    async def get_all_event_products(self, limit_per_store: int = 20):
        """모든 편의점 이벤트 상품 수집"""
        import asyncio
        results = {}

        for store_key, ScraperClass in self.scrapers.items():
            scraper = ScraperClass(headless=self.headless)
            try:
                products = await scraper.get_event_products(limit=limit_per_store)
                results[store_key] = products
            except Exception as e:
                print(f"[에러] {store_key} 수집 실패: {e}")
                results[store_key] = []
            finally:
                await scraper.close()

            await asyncio.sleep(2)

        return results
