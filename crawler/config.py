"""
꿀템장바구니 - 설정 파일
통합된 설정 관리 모듈
"""
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

# .env 파일 로드
load_dotenv()

# === API Keys ===
YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

# === AWS S3 Settings ===
AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
S3_BUCKET: str = os.getenv("S3_BUCKET", "notam-korea-data")

# === Database ===
DATA_DIR: Path = Path(__file__).parent.parent / "data"
DB_PATH: Path = DATA_DIR / "products.db"


def validate_config() -> dict:
    """설정 검증 및 상태 반환

    Returns:
        dict: 설정 상태 {key: (is_set, is_required)}
    """
    return {
        "YOUTUBE_API_KEY": (bool(YOUTUBE_API_KEY), True),
        "GEMINI_API_KEY": (bool(GEMINI_API_KEY), True),
        "OPENAI_API_KEY": (bool(OPENAI_API_KEY), False),
        "AWS_ACCESS_KEY_ID": (bool(AWS_ACCESS_KEY_ID), False),
        "AWS_SECRET_ACCESS_KEY": (bool(AWS_SECRET_ACCESS_KEY), False),
    }


def check_required_config() -> list:
    """필수 설정 누락 확인

    Returns:
        list: 누락된 필수 설정 키 리스트
    """
    config_status = validate_config()
    missing = [key for key, (is_set, is_required) in config_status.items()
               if is_required and not is_set]
    return missing

# 타겟 매장 카테고리
STORE_CATEGORIES = {
    "daiso": {
        "name": "다이소",
        "keywords": ["다이소", "daiso", "다이소 꿀템", "다이소 추천", "다이소 신상"],
        "mall_url": "https://www.daisomall.co.kr",
        "icon": "🏪",
    },
    "costco": {
        "name": "코스트코",
        "keywords": ["코스트코", "costco", "코스트코 추천", "코스트코 꿀템"],
        "mall_url": "https://www.costco.co.kr",
        "icon": "🛒",
    },
    "traders": {
        "name": "트레이더스",
        "keywords": ["트레이더스", "traders", "이마트 트레이더스", "트레이더스 추천"],
        "mall_url": "https://traders.ssg.com",
        "icon": "🏬",
    },
    "ikea": {
        "name": "이케아",
        "keywords": ["이케아", "ikea", "이케아 추천", "이케아 꿀템"],
        "mall_url": "https://www.ikea.com/kr",
        "icon": "🪑",
    },
    "oliveyoung": {
        "name": "올리브영",
        "keywords": ["올리브영", "oliveyoung", "올영", "올리브영 추천"],
        "mall_url": "https://www.oliveyoung.co.kr",
        "icon": "💄",
    },
    "cu": {
        "name": "CU",
        "keywords": ["cu", "씨유", "CU 신상", "CU 추천", "CU 꿀템"],
        "mall_url": "https://cu.bgfretail.com",
        "icon": "🟣",
    },
    "gs25": {
        "name": "GS25",
        "keywords": ["gs25", "gs", "지에스", "GS25 신상", "GS25 추천"],
        "mall_url": "https://gs25.gsretail.com",
        "icon": "🔵",
    },
    "seveneleven": {
        "name": "세븐일레븐",
        "keywords": ["세븐일레븐", "seven eleven", "7eleven", "세븐 신상"],
        "mall_url": "https://www.7-eleven.co.kr",
        "icon": "🟢",
    },
    "emart24": {
        "name": "이마트24",
        "keywords": ["이마트24", "emart24", "이마트 편의점", "이마트24 신상"],
        "mall_url": "https://emart24.co.kr",
        "icon": "🟡",
    },
    "convenience": {
        "name": "편의점",
        "keywords": ["편의점", "CU", "GS25", "세븐일레븐", "이마트24", "편의점 신상", "편의점 추천"],
        "mall_url": "",
        "icon": "🏪",
    },
    "coupang": {
        "name": "쿠팡",
        "keywords": ["쿠팡", "coupang", "로켓배송", "쿠팡 추천"],
        "mall_url": "https://www.coupang.com",
        "icon": "📦",
        "is_comparison": True,  # 가격 비교용
    },
}

# 모니터링할 유튜브 채널 (구독자 10만+, 리뷰 채널)
# 채널 핸들(@username) 또는 채널 ID 사용
TARGET_CHANNELS = {
    "daiso": [
        # 다이소/살림 추천 채널들
        {"handle": "@살림설렘", "name": "살림설렘", "priority": 1},
        {"handle": "@hejdoo", "name": "헤이두 Hejdoo", "priority": 1},
        {"handle": "@살림연구소오클", "name": "살림연구소 오클", "priority": 1},
        {"handle": "@야무진", "name": "야무진", "priority": 2},
        {"handle": "@sobilife", "name": "소비일상", "priority": 2},
        {"handle": "@알뜰파파", "name": "알뜰파파", "priority": 2},
        {"handle": "@행운의카일89", "name": "행운의카일", "priority": 3},
        {"handle": "@살림유니", "name": "살림유니", "priority": 3},
        {"handle": "@먹킷", "name": "먹킷리스트", "priority": 3},
        # 뷰티/화장품 다이소 리뷰
        {"id": "UCrlUlicedicJ5mlibqC62Eg", "name": "인씨 (뷰드름)", "priority": 1},
    ],
    "costco": [
        {"handle": "@먹킷", "name": "먹킷리스트", "priority": 1},
        {"handle": "@코스트코맛녀", "name": "코스트코맛녀", "priority": 1},
    ],
    "traders": [
        {"handle": "@먹킷", "name": "먹킷리스트", "priority": 1},
        {"handle": "@코스트코맛녀", "name": "코스트코맛녀", "priority": 2},
    ],
    "ikea": [
        {"handle": "@hejdoo", "name": "헤이두 Hejdoo", "priority": 1},
        {"handle": "@살림설렘", "name": "살림설렘", "priority": 2},
    ],
    "oliveyoung": [
        {"id": "UCrlUlicedicJ5mlibqC62Eg", "name": "인씨 (뷰드름)", "priority": 1},
        {"handle": "@디렉터파이", "name": "디렉터파이", "priority": 2},
        {"handle": "@lamuqe", "name": "라뮤끄", "priority": 2},
    ],
    "cu": [
        {"handle": "@편의점고인물", "name": "편의점고인물", "priority": 1},
        {"handle": "@먹킷", "name": "먹킷리스트", "priority": 2},
    ],
    "gs25": [
        {"handle": "@편의점고인물", "name": "편의점고인물", "priority": 1},
        {"handle": "@먹킷", "name": "먹킷리스트", "priority": 2},
    ],
    "seveneleven": [
        {"handle": "@편의점고인물", "name": "편의점고인물", "priority": 1},
    ],
    "emart24": [
        {"handle": "@편의점고인물", "name": "편의점고인물", "priority": 1},
    ],
    "convenience": [
        {"handle": "@편의점고인물", "name": "편의점고인물", "priority": 1},
        {"handle": "@먹킷", "name": "먹킷리스트", "priority": 2},
    ],
    "coupang": [
        {"handle": "@먹킷", "name": "먹킷리스트", "priority": 1},
    ],
}

# 검색 키워드 (채널 외 추가 검색용)
SEARCH_KEYWORDS = {
    "daiso": [
        "다이소 추천템", "다이소 꿀템", "다이소 신상", "다이소 품절대란",
        "다이소 살림템", "다이소 정리", "다이소 주방", "다이소 화장품",
    ],
    "costco": [
        "코스트코 추천", "코스트코 꿀템", "코스트코 신상",
        "코스트코 식품", "코스트코 생활용품",
    ],
    "traders": [
        "트레이더스 추천", "트레이더스 꿀템", "트레이더스 신상",
        "이마트 트레이더스", "트레이더스 식품",
    ],
    "ikea": [
        "이케아 추천", "이케아 꿀템", "이케아 수납", "이케아 정리",
        "이케아 가구", "이케아 인테리어",
    ],
    "oliveyoung": [
        "올리브영 추천", "올리브영 꿀템", "올영세일", "올리브영 신상",
        "올리브영 스킨케어", "올리브영 메이크업", "올리브영 1+1",
    ],
    "cu": [
        "CU 신상", "CU 추천", "CU 꿀템", "씨유 신상", "CU 1+1",
    ],
    "gs25": [
        "GS25 신상", "GS25 추천", "GS25 꿀템", "지에스 신상", "GS25 1+1",
    ],
    "seveneleven": [
        "세븐일레븐 신상", "세븐일레븐 추천", "세븐일레븐 꿀템",
    ],
    "emart24": [
        "이마트24 신상", "이마트24 추천", "이마트24 꿀템",
    ],
    "convenience": [
        "편의점 신상", "편의점 추천", "편의점 꿀템",
        "CU 신상", "GS25 신상", "세븐일레븐 신상", "이마트24 신상",
        "편의점 1+1", "편의점 행사",
    ],
    "coupang": [
        "쿠팡 추천", "쿠팡 꿀템", "로켓배송 추천",
        "쿠팡 할인", "쿠팡 가성비",
    ],
}

# 상품 카테고리
PRODUCT_CATEGORIES = {
    "food": {"name": "식품", "icon": "🍽️", "keywords": ["식품", "간식", "음료", "과자", "라면"]},
    "beauty": {"name": "뷰티", "icon": "💄", "keywords": ["화장품", "스킨케어", "메이크업", "향수", "뷰티"]},
    "living": {"name": "생활용품", "icon": "🏠", "keywords": ["생활", "청소", "세탁", "욕실", "주방"]},
    "kitchen": {"name": "주방", "icon": "🍳", "keywords": ["주방", "조리", "식기", "수납"]},
    "interior": {"name": "인테리어", "icon": "🪴", "keywords": ["인테리어", "수납", "정리", "데코", "가구"]},
    "fashion": {"name": "패션", "icon": "👕", "keywords": ["패션", "의류", "액세서리", "가방"]},
    "digital": {"name": "디지털", "icon": "📱", "keywords": ["전자", "디지털", "충전", "케이블"]},
    "health": {"name": "건강", "icon": "💊", "keywords": ["건강", "영양제", "운동", "헬스"]},
    "baby": {"name": "유아", "icon": "👶", "keywords": ["유아", "아기", "육아", "키즈"]},
    "pet": {"name": "반려동물", "icon": "🐕", "keywords": ["반려", "펫", "강아지", "고양이"]},
    "office": {"name": "문구/오피스", "icon": "📝", "keywords": ["문구", "오피스", "학용품", "사무"]},
    "outdoor": {"name": "아웃도어", "icon": "⛺", "keywords": ["캠핑", "아웃도어", "여행", "레저"]},
}

# AI 분석 프롬프트
PRODUCT_EXTRACTION_PROMPT = """
다음은 {store_name} 추천 영상의 자막입니다.
이 영상에서 추천하는 상품들을 추출해주세요.

규칙:
1. 반드시 JSON 배열 형식으로 출력
2. 비추천/구매 금지 상품은 제외
3. 가격은 숫자만 (예: 1000, 3000)
4. 타임스탬프는 초 단위 (예: 120 = 2분)

출력 형식:
[
  {{
    "name": "상품명",
    "price": 가격(숫자),
    "category": "카테고리 (주방/청소/인테리어/뷰티/간식 등)",
    "reason": "추천 이유 (1-2문장)",
    "timestamp": 해당 상품 언급 시작 시간(초),
    "keywords": ["검색 키워드1", "검색 키워드2"]
  }}
]

자막:
{transcript}
"""

# 수집 설정
CRAWL_CONFIG = {
    "check_interval_hours": 1,  # 신규 영상 체크 주기
    "max_results_per_channel": 10,  # 채널당 최대 조회 영상 수
    "published_after_days": 30,  # 최근 N일 이내 영상만
}
