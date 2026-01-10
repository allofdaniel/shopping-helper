# -*- coding: utf-8 -*-
"""
개선된 상품 매칭기
- 매칭 임계값 상향 (20 -> 40)
- 다단계 검증 (이름 + 가격 + 카테고리)
- 신뢰도 점수 반환
- 수동 검토 플래그
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class MatchResult:
    """매칭 결과"""
    product_code: str
    official_name: str
    official_price: int
    score: int = 0
    name_score: int = 0
    price_score: int = 0
    category_score: int = 0
    popularity_score: int = 0
    confidence: float = 0.0
    image_url: str = ""
    product_url: str = ""
    category: str = ""
    needs_manual_review: bool = False

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "product_code": self.product_code,
            "official_name": self.official_name,
            "official_price": self.official_price,
            "score": self.score,
            "name_score": self.name_score,
            "price_score": self.price_score,
            "category_score": self.category_score,
            "popularity_score": self.popularity_score,
            "confidence": self.confidence,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "category": self.category,
            "needs_manual_review": self.needs_manual_review,
            "matched": True,
        }

    def is_valid(self) -> bool:
        """유효한 매칭인지 확인"""
        return self.score >= ImprovedProductMatcher.MATCH_THRESHOLD


class ImprovedProductMatcher:
    """개선된 상품 매칭기"""

    # 매칭 임계값 (기존 20 -> 40으로 상향)
    MATCH_THRESHOLD = 40

    # 이름 점수 최소 임계값 (이름 유사도가 너무 낮으면 매칭 거부)
    NAME_SCORE_MINIMUM = 20

    # 신뢰도 임계값 (이 이하면 수동 검토 필요)
    CONFIDENCE_THRESHOLD = 0.7

    # 가격 허용 오차 (원)
    PRICE_TOLERANCE = 1000

    # 불용어 목록 (확장)
    STOPWORDS = [
        # 매장명
        "다이소", "daiso", "코스트코", "costco", "이케아", "ikea",
        "올리브영", "트레이더스",
        # 감탄/수식어
        "진짜", "완전", "꿀템", "추천", "좋은", "최고", "대박", "레전드",
        "미친", "찐", "실화", "사세요", "무조건", "필수템", "갓성비",
        # 접사/조사
        "이", "가", "을", "를", "의", "에", "에서", "으로", "로",
        # 가격 관련
        "원", "짜리", "천원", "만원",
    ]

    # 한국어 변형 매핑
    KOREAN_VARIANTS = {
        "스텐": ["스테인레스", "스텐레스", "스틸"],
        "스테인레스": ["스텐", "스텐레스", "스틸"],
        "실리콘": ["실리콘", "실리"],
        "플라스틱": ["플라", "플스틱"],
        "대형": ["대", "빅", "large"],
        "소형": ["소", "미니", "small"],
        "세트": ["set", "모음"],
    }

    # 카테고리 매핑
    CATEGORY_MAPPING = {
        "주방": ["주방", "키친", "kitchen", "요리", "조리", "식기"],
        "인테리어": ["인테리어", "수납", "정리", "데코", "가구"],
        "청소": ["청소", "세탁", "빨래", "욕실"],
        "뷰티": ["뷰티", "화장", "스킨", "메이크업", "미용"],
        "식품": ["식품", "음식", "과자", "간식", "음료"],
    }

    def __init__(self):
        self.catalog: List[Dict] = []

    def set_catalog(self, products: List[Dict]):
        """카탈로그 설정"""
        self.catalog = products

    def match(
        self,
        product_name: str,
        price: int = None,
        category: str = None,
        keywords: List[str] = None,
    ) -> Optional[MatchResult]:
        """
        상품 매칭 수행

        Args:
            product_name: 검색할 상품명
            price: 예상 가격 (있으면 매칭 정확도 향상)
            category: 상품 카테고리
            keywords: 추가 키워드

        Returns:
            MatchResult or None
        """
        if not product_name or not self.catalog:
            return None

        # 1. 상품명 정제
        clean_name = self._clean_product_name(product_name)
        if len(clean_name) < 2:
            return None

        # 2. 변형 키워드 생성
        search_terms = self._generate_search_terms(clean_name, keywords)

        # 3. 카탈로그 검색 및 점수 계산
        best_match = None
        best_score = 0

        for candidate in self.catalog:
            score_result = self._calculate_match_score(
                query=clean_name,
                search_terms=search_terms,
                candidate=candidate,
                target_price=price,
                target_category=category,
            )

            if score_result["total_score"] > best_score:
                best_score = score_result["total_score"]
                best_match = self._create_match_result(candidate, score_result)

        # 4. 임계값 확인 (총점 + 이름 점수 최소값 모두 충족해야 함)
        if best_match and best_match.score >= self.MATCH_THRESHOLD:
            # 이름 점수가 최소 임계값 미달이면 매칭 거부
            if best_match.name_score < self.NAME_SCORE_MINIMUM:
                return None

            # 신뢰도 계산
            best_match.confidence = self._calculate_confidence(best_match)
            best_match.needs_manual_review = best_match.confidence < self.CONFIDENCE_THRESHOLD
            return best_match

        return None

    def _clean_product_name(self, name: str) -> str:
        """상품명 정제"""
        # 특수문자 제거
        clean = re.sub(r'[^\w\s가-힣]', ' ', name)

        # 불용어 제거
        words = clean.lower().split()
        filtered = [w for w in words if w not in [s.lower() for s in self.STOPWORDS]]

        # 연속 공백 제거
        result = ' '.join(filtered)
        return result.strip()

    def _generate_search_terms(self, name: str, keywords: List[str] = None) -> List[str]:
        """검색어 변형 생성"""
        terms = set()
        terms.add(name.lower())

        # 단어별 처리
        words = name.lower().split()
        for word in words:
            terms.add(word)
            # 변형 추가
            for key, variants in self.KOREAN_VARIANTS.items():
                if word == key.lower():
                    terms.update([v.lower() for v in variants])
                elif word in [v.lower() for v in variants]:
                    terms.add(key.lower())

        # 키워드 추가
        if keywords:
            terms.update([k.lower() for k in keywords])

        return list(terms)

    def _calculate_match_score(
        self,
        query: str,
        search_terms: List[str],
        candidate: Dict,
        target_price: int = None,
        target_category: str = None,
    ) -> Dict:
        """매칭 점수 계산"""
        score = {
            "name_score": 0,
            "price_score": 0,
            "category_score": 0,
            "popularity_score": 0,
            "total_score": 0,
        }

        candidate_name = candidate.get("name", "").lower()
        candidate_words = set(candidate_name.split())

        # 1. 이름 매칭 점수 (최대 50점)
        query_words = set(query.lower().split())

        # Jaccard 유사도
        if query_words and candidate_words:
            intersection = query_words & candidate_words
            union = query_words | candidate_words
            jaccard = len(intersection) / len(union) if union else 0
            score["name_score"] += int(jaccard * 30)

        # 부분 문자열 매칭
        if query.lower() in candidate_name:
            score["name_score"] += 20
        else:
            # 검색어 중 하나라도 포함되면 부분 점수
            matching_terms = sum(1 for term in search_terms if term in candidate_name and len(term) >= 2)
            score["name_score"] += min(matching_terms * 5, 15)

        # 2. 가격 매칭 점수 (최대 20점)
        if target_price and candidate.get("price"):
            candidate_price = candidate["price"]
            price_diff = abs(candidate_price - target_price)

            if price_diff == 0:
                score["price_score"] = 20  # 정확 일치
            elif price_diff <= self.PRICE_TOLERANCE:
                score["price_score"] = 15  # 범위 내
            elif price_diff <= self.PRICE_TOLERANCE * 2:
                score["price_score"] = 5   # 약간 벗어남
            # else: 0점

        # 3. 카테고리 매칭 점수 (최대 15점)
        if target_category and candidate.get("category"):
            candidate_cat = candidate["category"].lower()

            # 직접 일치
            if target_category.lower() in candidate_cat:
                score["category_score"] = 15
            else:
                # 매핑된 카테고리 확인
                for cat_key, cat_variants in self.CATEGORY_MAPPING.items():
                    if target_category.lower() in [v.lower() for v in cat_variants]:
                        if any(v.lower() in candidate_cat for v in cat_variants):
                            score["category_score"] = 10
                            break

        # 4. 인기도 점수 (최대 15점)
        order_count = candidate.get("order_count", 0)
        if order_count > 10000:
            score["popularity_score"] = 15
        elif order_count > 5000:
            score["popularity_score"] = 10
        elif order_count > 1000:
            score["popularity_score"] = 5

        # 베스트 상품 보너스
        if candidate.get("is_best"):
            score["popularity_score"] += 5

        # 총점 계산 (최대 100점)
        score["total_score"] = min(
            score["name_score"] + score["price_score"] +
            score["category_score"] + score["popularity_score"],
            100
        )

        return score

    def _create_match_result(self, candidate: Dict, score: Dict) -> MatchResult:
        """MatchResult 생성"""
        return MatchResult(
            product_code=candidate.get("product_no", ""),
            official_name=candidate.get("name", ""),
            official_price=candidate.get("price", 0),
            score=score["total_score"],
            name_score=score["name_score"],
            price_score=score["price_score"],
            category_score=score["category_score"],
            popularity_score=score["popularity_score"],
            image_url=candidate.get("image_url", ""),
            product_url=candidate.get("product_url", ""),
            category=candidate.get("category", ""),
        )

    def _calculate_confidence(self, result: MatchResult) -> float:
        """
        신뢰도 계산 (0.0 ~ 1.0)

        기준:
        - 이름 점수가 높을수록 신뢰도 높음
        - 가격도 일치하면 신뢰도 상승
        - 인기 상품이면 신뢰도 상승
        """
        # 이름 점수 비중 60%
        name_confidence = result.name_score / 50 * 0.6

        # 가격 점수 비중 25%
        price_confidence = result.price_score / 20 * 0.25

        # 인기도 비중 15%
        popularity_confidence = result.popularity_score / 15 * 0.15

        total = name_confidence + price_confidence + popularity_confidence
        return round(min(total, 1.0), 2)

    def match_batch(self, products: List[Dict]) -> List[Dict]:
        """여러 상품 일괄 매칭"""
        results = []
        for product in products:
            match = self.match(
                product_name=product.get("name", ""),
                price=product.get("price"),
                category=product.get("category"),
                keywords=product.get("keywords", []),
            )

            result = product.copy()
            if match:
                result["official"] = match.to_dict()
                result["is_matched"] = True
            else:
                result["official"] = None
                result["is_matched"] = False

            results.append(result)

        return results


def main():
    """테스트 실행"""
    matcher = ImprovedProductMatcher()

    # 테스트 카탈로그
    catalog = [
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
            "name": "실리콘 주걱 세트",
            "price": 3000,
            "category": "주방",
            "order_count": 12000,
            "is_best": True,
        },
        {
            "product_no": "100003",
            "name": "다용도 정리함 소형",
            "price": 1000,
            "category": "수납/정리",
            "order_count": 20000,
            "is_best": True,
        },
    ]

    matcher.set_catalog(catalog)

    # 테스트 검색
    test_cases = [
        ("스텐 배수구망", 2000, "주방"),
        ("다이소 진짜 좋은 실리콘 주걱", 3000, None),
        ("정리함", 1000, "인테리어"),
        ("노트북 충전기", 50000, "디지털"),  # 매칭 안됨
    ]

    print("=== 개선된 상품 매칭 테스트 ===\n")
    print(f"매칭 임계값: {ImprovedProductMatcher.MATCH_THRESHOLD}점\n")

    for name, price, category in test_cases:
        print(f"검색: {name} ({price}원, {category or '카테고리 미지정'})")
        result = matcher.match(name, price, category)

        if result:
            print(f"  -> 매칭 성공!")
            print(f"     상품: {result.official_name}")
            print(f"     가격: {result.official_price}원")
            print(f"     점수: {result.score}점 (이름:{result.name_score}, 가격:{result.price_score})")
            print(f"     신뢰도: {result.confidence}")
            print(f"     수동 검토 필요: {result.needs_manual_review}")
        else:
            print(f"  -> 매칭 실패 (임계값 미달)")

        print()


if __name__ == "__main__":
    main()
