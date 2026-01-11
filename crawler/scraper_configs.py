# -*- coding: utf-8 -*-
"""
스토어별 스크래퍼 설정
- URL, 셀렉터, 파싱 규칙을 설정으로 분리
- 새 스토어 추가시 설정만 추가하면 됨
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StoreSelectors:
    """스토어별 HTML 셀렉터 설정"""
    # 상품 목록 셀렉터 (여러 개 시도)
    product_list: List[str] = field(default_factory=list)

    # 개별 필드 셀렉터
    name: List[str] = field(default_factory=list)
    price: List[str] = field(default_factory=list)
    original_price: List[str] = field(default_factory=list)
    image: List[str] = field(default_factory=list)
    link: List[str] = field(default_factory=list)
    rating: List[str] = field(default_factory=list)
    review_count: List[str] = field(default_factory=list)
    brand: List[str] = field(default_factory=list)

    # 상품 ID 추출 패턴 (URL에서)
    id_pattern: str = ""
    id_attribute: str = ""  # data-product-id 등

    # 이벤트/뱃지 셀렉터
    event_type: List[str] = field(default_factory=list)
    is_best: List[str] = field(default_factory=list)
    is_sale: List[str] = field(default_factory=list)

    # 팝업/쿠키 동의 셀렉터
    cookie_popup: str = ""


@dataclass
class StoreConfig:
    """스토어별 설정"""
    name: str  # 스토어 이름 (한글)
    code: str  # 스토어 코드 (영문, 고유 ID)
    base_url: str
    search_url: str
    selectors: StoreSelectors

    # 검색 URL 패턴 (%s는 검색어)
    search_query_param: str = "q"

    # 카테고리 URL 패턴
    category_url_pattern: str = ""

    # 페이지 로딩 대기
    page_load_delay: float = 3.0

    # 스크롤 필요 여부
    requires_scroll: bool = False
    scroll_times: int = 3

    # 특수 처리 플래그
    needs_main_page_first: bool = False  # 메인 페이지 먼저 방문 필요
    is_event_store: bool = False  # 편의점 등 이벤트 상품 위주


# ============================================================
# 스토어별 설정 정의
# ============================================================

COSTCO_CONFIG = StoreConfig(
    name="코스트코",
    code="costco",
    base_url="https://www.costco.co.kr",
    search_url="https://www.costco.co.kr/search",
    search_query_param="text",
    selectors=StoreSelectors(
        product_list=[
            '.product-list-item',
            '.product-tile',
            '[data-component="product-card"]'
        ],
        name=['.product-name', '.product-tile-name', 'h3 a', '.tile-name'],
        price=['.product-price', '.price', '.money'],
        original_price=['.original-price', '.was-price'],
        image=['img.product-image', 'img'],
        link=['a.product-link', 'a[href*="/p/"]', 'h3 a'],
        rating=['.star-rating', '.rating'],
        review_count=['.review-count', '.ratings-count'],
        id_pattern=r'/p/(\d+)',
        cookie_popup='#onetrust-accept-btn-handler',
    ),
    page_load_delay=4.0,
)

IKEA_CONFIG = StoreConfig(
    name="이케아",
    code="ikea",
    base_url="https://www.ikea.com/kr/ko",
    search_url="https://www.ikea.com/kr/ko/search/",
    search_query_param="q",
    selectors=StoreSelectors(
        product_list=[
            '.pip-product-compact',
            '.plp-product-list__item',
            '[data-testid="product-card"]'
        ],
        name=[
            '.pip-header-section__title--small',
            '.pip-header-section__title',
            '[class*="product-name"]'
        ],
        price=[
            '.pip-temp-price__integer',
            '.pip-price__integer',
            '[class*="price"]'
        ],
        image=['img'],
        link=['a[href*="/p/"]'],
        rating=['[class*="rating"]'],
        id_pattern=r'-(\d{8})',
        id_attribute='',
        cookie_popup='#onetrust-accept-btn-handler',
    ),
    page_load_delay=4.0,
)

OLIVEYOUNG_CONFIG = StoreConfig(
    name="올리브영",
    code="oliveyoung",
    base_url="https://www.oliveyoung.co.kr",
    search_url="https://www.oliveyoung.co.kr/store/search/getSearchMain.do",
    search_query_param="query",
    selectors=StoreSelectors(
        product_list=[
            'ul.cate_prd_list li',
            'div.prd_info',
            '.search_list li',
            '#Contents ul li[data-ref-goodsno]'
        ],
        name=['.tx_name', '.prd_name', '.name a'],
        price=['.tx_cur', '.prd_price .price', '.price'],
        original_price=['.tx_org', '.prd_price del', '.org_price'],
        image=['img'],
        link=['a[href*="goodsNo="]'],
        rating=['.point', '.review_point'],
        review_count=['.count', '.review_count'],
        brand=['.tx_brand', '.brand', '.prd_brand'],
        id_pattern=r'goodsNo=([A-Z0-9]+)',
        id_attribute='data-ref-goodsno',
        is_best=['.badge_best', '.best', '.icon_best'],
        is_sale=['.badge_sale', '.sale', '.icon_sale'],
    ),
    page_load_delay=4.0,
    needs_main_page_first=True,
)

TRADERS_CONFIG = StoreConfig(
    name="트레이더스",
    code="traders",
    base_url="https://traders.ssg.com",
    search_url="https://traders.ssg.com/search.ssg",
    search_query_param="query",
    selectors=StoreSelectors(
        product_list=[
            '.cunit_prod',
            '.cunit_item',
            'li[data-unittype="item"]'
        ],
        name=['.title', '.cunit_info .name', 'a.clickable'],
        price=['.ssg_price', '.price', '.opt_price'],
        original_price=['.old_price', '.normal_price'],
        image=['img.i_img', 'img'],
        link=['a.clickable'],
        id_pattern=r'/item/(\d+)',
        id_attribute='data-item-id',
        cookie_popup='',
    ),
    page_load_delay=3.0,
)

COUPANG_CONFIG = StoreConfig(
    name="쿠팡",
    code="coupang",
    base_url="https://www.coupang.com",
    search_url="https://www.coupang.com/np/search",
    search_query_param="q",
    selectors=StoreSelectors(
        product_list=[
            'li.search-product',
            '.search-product-wrap',
            '[class*="product-item"]'
        ],
        name=['.name', 'div.name', '.product-title'],
        price=['.price-value', '.price', '[class*="price"]'],
        original_price=['.base-price', '.origin-price'],
        image=['img.search-product-wrap-img', 'img'],
        link=['a.search-product-link', 'a[href*="/products/"]'],
        rating=['.rating', '.star-rating'],
        review_count=['.rating-total-count', '.count'],
        id_pattern=r'/products/(\d+)',
        cookie_popup='',
    ),
    page_load_delay=3.0,
)

DAISO_CONFIG = StoreConfig(
    name="다이소",
    code="daiso",
    base_url="https://www.daiso.co.kr",
    search_url="https://www.daiso.co.kr/goods/goods_search.php",
    search_query_param="keyword",
    selectors=StoreSelectors(
        product_list=[
            '.goods_list li',
            '.item_list li',
            '.product_item'
        ],
        name=['.goods_name', '.item_name', '.name'],
        price=['.goods_price', '.price', '.cost'],
        image=['img'],
        link=['a[href*="goods_no="]'],
        id_pattern=r'goods_no=(\d+)',
        cookie_popup='',
    ),
    page_load_delay=3.0,
)


# 편의점 설정 (이벤트 상품 위주)
CU_CONFIG = StoreConfig(
    name="CU",
    code="cu",
    base_url="https://cu.bgfretail.com",
    search_url="https://cu.bgfretail.com/event/plus.do",
    selectors=StoreSelectors(
        product_list=['.prod_list li', '.product_list li', 'ul.list li'],
        name=['.name', '.prod_name', '.tit'],
        price=['.price', '.cost', '.won'],
        image=['img'],
    ),
    page_load_delay=3.0,
    is_event_store=True,
)

GS25_CONFIG = StoreConfig(
    name="GS25",
    code="gs25",
    base_url="https://gs25.gsretail.com",
    search_url="https://gs25.gsretail.com/gscvs/ko/products/event-goods",
    selectors=StoreSelectors(
        product_list=['.prod_box', '.product_list li', '.prd_item'],
        name=['.tit', '.prd_name', '.name'],
        price=['.price', '.cost'],
        image=['img'],
        event_type=['.flag', '.badge', '.event_type'],
    ),
    page_load_delay=3.0,
    is_event_store=True,
)

SEVENELEVEN_CONFIG = StoreConfig(
    name="세븐일레븐",
    code="seveneleven",
    base_url="https://www.7-eleven.co.kr",
    search_url="https://www.7-eleven.co.kr/product/presentList.asp",
    selectors=StoreSelectors(
        product_list=['.pic_product', '.product_list li', 'ul.list_711 li'],
        name=['.name', '.tit_product', '.txt_product'],
        price=['.price', '.price_product'],
        image=['img'],
    ),
    page_load_delay=3.0,
    is_event_store=True,
)

EMART24_CONFIG = StoreConfig(
    name="이마트24",
    code="emart24",
    base_url="https://emart24.co.kr",
    search_url="https://emart24.co.kr/goods/event",
    selectors=StoreSelectors(
        product_list=['.itemWrap', '.goods_list li', '.product_item'],
        name=['.itemTitle', '.goods_name', '.name'],
        price=['.itemPrice', '.goods_price', '.price'],
        image=['img'],
    ),
    page_load_delay=3.0,
    is_event_store=True,
)


# 전체 스토어 설정 매핑
STORE_CONFIGS: Dict[str, StoreConfig] = {
    "costco": COSTCO_CONFIG,
    "ikea": IKEA_CONFIG,
    "oliveyoung": OLIVEYOUNG_CONFIG,
    "traders": TRADERS_CONFIG,
    "coupang": COUPANG_CONFIG,
    "daiso": DAISO_CONFIG,
    "cu": CU_CONFIG,
    "gs25": GS25_CONFIG,
    "seveneleven": SEVENELEVEN_CONFIG,
    "emart24": EMART24_CONFIG,
}


def get_store_config(store_code: str) -> Optional[StoreConfig]:
    """스토어 코드로 설정 조회"""
    return STORE_CONFIGS.get(store_code.lower())


def list_available_stores() -> List[str]:
    """사용 가능한 스토어 코드 목록"""
    return list(STORE_CONFIGS.keys())
