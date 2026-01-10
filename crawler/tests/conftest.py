# -*- coding: utf-8 -*-
"""
pytest 공통 설정 및 픽스처
"""
import pytest
import sys
from pathlib import Path

# crawler 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


# ========== 샘플 데이터 픽스처 ==========

@pytest.fixture
def sample_good_transcript():
    """좋은 품질의 자막 샘플 (충분한 길이, 상품 언급)"""
    return """
    오늘은 다이소 꿀템 10가지를 소개해드릴게요!
    첫 번째는 스텐 배수구망이에요. 가격은 2천원인데요, 물때도 안 끼고 진짜 좋아요.
    스테인리스라서 녹도 안 슬고 위생적이에요. 주방에 필수템이죠.

    두 번째는 실리콘 주걱이에요. 3천원인데 열에도 강하고 냄비에 흠집도 안 나요.
    특히 코팅 프라이팬 쓰시는 분들한테 강추에요.

    세 번째 서랍 정리함 천원이에요. 양말이나 속옷 정리할 때 딱이에요.
    싹 정리되고 미니멀해지는 느낌 있잖아요.

    네 번째 먼지털이개 2천원. 전 진짜 이거 없으면 청소 못해요.
    TV나 컴퓨터 먼지 닦을 때 최고예요.

    다섯 번째 밀폐용기 세트 5천원. 냉장고 정리 끝이에요.
    투명해서 내용물이 바로 보이고 사이즈별로 다양하게 들어있어요.

    여섯 번째는 다이소 손톱깎이 세트예요. 3천원인데 품질이 진짜 좋아요.
    날이 날카롭고 손톱이 튀지 않아요.

    일곱 번째 휴대용 빗자루 세트 2천원. 책상 위나 자동차 청소할 때 완전 좋아요.
    작은데 흡입력이 좋아서 먼지가 싹 빠져요.

    여덟 번째 다용도 후크 세트 천원이에요. 주방이나 욕실에 붙여서 쓰면 돼요.
    접착력이 좋아서 잘 안 떨어져요.

    아홉 번째 디퓨저 3천원. 다이소 디퓨저가 이 가격에 이 퀄리티라고?
    은은하게 향이 퍼져서 집안이 좋은 향기로 가득해요.

    열 번째 압축봉 2천원. 옷장이나 신발장 정리할 때 필수예요.
    길이 조절되고 튼튼해서 오래 써요.
    """


@pytest.fixture
def sample_bad_transcript_too_short():
    """너무 짧은 자막 샘플"""
    return "다이소 추천템 알려드릴게요"


@pytest.fixture
def sample_bad_transcript_no_products():
    """상품 언급이 없는 자막"""
    return """
    오늘 날씨가 정말 좋네요. 산책하기 딱 좋은 날씨예요.
    저는 오늘 점심에 라면을 먹었어요. 맛있었어요.
    내일은 친구를 만나기로 했어요. 오랜만에 만나서 기대돼요.
    요즘 운동을 열심히 하고 있어요. 건강이 중요하잖아요.
    """


@pytest.fixture
def sample_negative_review_transcript():
    """부정적 리뷰가 포함된 자막 (충분한 길이)"""
    return """
    다이소 비추템 알려드릴게요. 오늘은 다이소에서 사면 후회하는 상품들을 소개합니다.

    첫 번째 다이소 선풍기는 절대 사지 마세요. 소음도 심하고 바람도 약해요.
    완전 실패템이에요. 돈 버렸어요. 3천원인데 진짜 별로에요. 다른거 사세요.

    두 번째 이 이어폰도 비추해요. 음질이 너무 안 좋아요.
    천원짜리 이어폰치고도 별로예요. 절대 구매금지입니다.

    세 번째 이 텀블러도 비추. 뚜껑이 잘 안 닫혀요. 물이 새요.

    근데 스텐 배수구망은 진짜 좋아요! 2천원인데 퀄리티 최고예요.
    이건 강추드려요. 주방에 필수템이에요. 물때도 안끼고 위생적이에요.

    그리고 실리콘 주걱도 추천해요. 3천원인데 열에 강하고 좋아요.
    """


@pytest.fixture
def sample_products():
    """추출된 상품 샘플"""
    return [
        {
            "name": "스텐 배수구망",
            "price": 2000,
            "category": "주방",
            "reason": "물때가 안 껴서 관리가 편해요",
            "timestamp": 120,
            "keywords": ["배수구", "스텐", "주방"],
            "confidence": 0.95,
        },
        {
            "name": "실리콘 주걱",
            "price": 3000,
            "category": "주방",
            "reason": "열에 강하고 코팅 프라이팬에 좋아요",
            "timestamp": 180,
            "keywords": ["주걱", "실리콘", "주방용품"],
            "confidence": 0.92,
        },
        {
            "name": "서랍 정리함",
            "price": 1000,
            "category": "인테리어",
            "reason": "양말 정리에 딱 좋아요",
            "timestamp": 240,
            "keywords": ["정리함", "수납", "서랍"],
            "confidence": 0.88,
        },
    ]


@pytest.fixture
def sample_catalog_products():
    """다이소 카탈로그 상품 샘플"""
    return [
        {
            "product_no": "100001",
            "name": "스테인레스 배수구망",
            "price": 2000,
            "category": "주방",
            "order_count": 15000,
            "is_best": True,
        },
        {
            "product_no": "100002",
            "name": "스텐 배수구 거름망 대형",
            "price": 3000,
            "category": "주방",
            "order_count": 8000,
            "is_best": False,
        },
        {
            "product_no": "100003",
            "name": "실리콘 주걱 세트",
            "price": 3000,
            "category": "주방",
            "order_count": 12000,
            "is_best": True,
        },
        {
            "product_no": "100004",
            "name": "다용도 정리함 S",
            "price": 1000,
            "category": "수납/정리",
            "order_count": 20000,
            "is_best": True,
        },
    ]


@pytest.fixture
def sample_video():
    """영상 정보 샘플"""
    return {
        "video_id": "test_video_001",
        "title": "다이소 꿀템 TOP 10 추천!",
        "description": "다이소에서 꼭 사야할 제품들을 소개합니다.",
        "channel_id": "UC_test_channel",
        "channel_title": "살림 유튜버",
        "published_at": "2025-01-15T10:00:00Z",
        "thumbnail_url": "https://i.ytimg.com/vi/test_video_001/maxresdefault.jpg",
        "view_count": 500000,
        "like_count": 15000,
        "store_key": "daiso",
        "store_name": "다이소",
    }
