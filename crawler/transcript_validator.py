# -*- coding: utf-8 -*-
"""
자막 품질 검증기
영상 자막이 상품 추출에 적합한지 검증합니다.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class TranscriptQuality:
    """자막 품질 검증 결과"""
    is_valid: bool
    length: int = 0
    quality_score: float = 0.0
    product_mention_count: int = 0
    price_mention_count: int = 0
    store_mention_count: int = 0
    has_negative_reviews: bool = False
    negative_product_count: int = 0
    positive_product_count: int = 0
    store_mismatch_warning: bool = False
    rejection_reason: Optional[str] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "is_valid": self.is_valid,
            "length": self.length,
            "quality_score": self.quality_score,
            "product_mention_count": self.product_mention_count,
            "price_mention_count": self.price_mention_count,
            "store_mention_count": self.store_mention_count,
            "has_negative_reviews": self.has_negative_reviews,
            "negative_product_count": self.negative_product_count,
            "positive_product_count": self.positive_product_count,
            "store_mismatch_warning": self.store_mismatch_warning,
            "rejection_reason": self.rejection_reason,
        }

    @classmethod
    def invalid(cls, reason: str) -> "TranscriptQuality":
        """유효하지 않은 결과 생성"""
        return cls(is_valid=False, rejection_reason=reason)


class TranscriptValidator:
    """자막 품질 검증기"""

    # 최소 자막 길이 (문자 수)
    MIN_LENGTH = 300

    # 상품 관련 키워드
    PRODUCT_KEYWORDS = [
        # 추천/소개 관련
        "추천", "꿀템", "필수템", "강추", "좋아요", "최고", "대박",
        "인기", "베스트", "핫템", "소개", "리뷰",
        # 상품 유형
        "제품", "상품", "템", "아이템", "용품",
        # 품질/특징
        "퀄리티", "품질", "가성비", "싸고", "저렴",
        # 구매 관련
        "구매", "구입", "샀", "사세요", "사야",
    ]

    # 가격 패턴
    PRICE_PATTERNS = [
        r'\d{1,2}천원',           # 1천원, 2천원
        r'\d{1,2},?\d{3}원',      # 1,000원, 3000원
        r'\d{1,2}원짜리',         # 천원짜리
        r'가격[은이가]?\s*\d+',   # 가격은 2000
        r'\d+원[이에]',           # 2000원이에요
    ]

    # 부정적 리뷰 키워드
    NEGATIVE_KEYWORDS = [
        "비추", "비추천", "별로", "실패", "후회", "사지마", "사지 마",
        "구매금지", "안좋", "안 좋", "최악", "돈 아까", "돈아까",
        "환불", "교환", "불량", "고장", "망했", "실망",
    ]

    # 긍정적 추천 키워드
    POSITIVE_KEYWORDS = [
        "강추", "추천", "좋아요", "최고", "대박", "꿀템", "필수",
        "진짜 좋", "완전 좋", "강력 추천", "꼭 사",
    ]

    # 매장별 키워드
    STORE_KEYWORDS = {
        "다이소": ["다이소", "daiso", "다이소몰"],
        "코스트코": ["코스트코", "costco", "코스코"],
        "이케아": ["이케아", "ikea", "이게아"],
        "올리브영": ["올리브영", "oliveyoung", "올영"],
        "트레이더스": ["트레이더스", "traders", "이마트 트레이더스"],
        "CU": ["씨유", "cu", "CU"],
        "GS25": ["지에스", "gs25", "GS25", "gs"],
        "세븐일레븐": ["세븐일레븐", "7eleven", "세븐"],
        "이마트24": ["이마트24", "emart24"],
        "쿠팡": ["쿠팡", "coupang", "로켓배송"],
    }

    def validate(self, transcript: str, store_name: str = None) -> TranscriptQuality:
        """
        자막 품질 검증

        Args:
            transcript: 자막 텍스트
            store_name: 검증할 매장 이름 (선택)

        Returns:
            TranscriptQuality: 검증 결과
        """
        # None 또는 빈 문자열 체크
        if not transcript:
            return TranscriptQuality.invalid("자막이 없습니다")

        # 공백 제거 후 텍스트
        clean_text = transcript.strip()
        if not clean_text:
            return TranscriptQuality.invalid("자막이 비어있습니다")

        length = len(clean_text)

        # 1. 최소 길이 검증
        if length < self.MIN_LENGTH:
            return TranscriptQuality(
                is_valid=False,
                length=length,
                quality_score=length / self.MIN_LENGTH * 0.5,
                rejection_reason=f"자막 길이가 너무 짧습니다 ({length}자 < {self.MIN_LENGTH}자)"
            )

        # 2. 상품 언급 분석
        product_mentions = self._count_keywords(clean_text, self.PRODUCT_KEYWORDS)
        price_mentions = self._count_price_mentions(clean_text)

        # 3. 부정/긍정 리뷰 분석
        negative_count = self._count_keywords(clean_text, self.NEGATIVE_KEYWORDS)
        positive_count = self._count_keywords(clean_text, self.POSITIVE_KEYWORDS)

        # 상품 언급이 없으면 실패
        if product_mentions == 0 and price_mentions == 0:
            return TranscriptQuality(
                is_valid=False,
                length=length,
                quality_score=0.3,
                product_mention_count=0,
                price_mention_count=0,
                rejection_reason="상품 관련 언급이 없습니다"
            )

        # 4. 매장 관련성 분석
        store_mentions = 0
        store_mismatch = False
        if store_name:
            store_mentions = self._count_store_mentions(clean_text, store_name)
            # 다른 매장이 더 많이 언급되면 경고
            other_store_max = 0
            for other_store, keywords in self.STORE_KEYWORDS.items():
                if other_store != store_name:
                    other_count = sum(clean_text.lower().count(kw.lower()) for kw in keywords)
                    other_store_max = max(other_store_max, other_count)
            if other_store_max > store_mentions and store_mentions == 0:
                store_mismatch = True

        # 5. 품질 점수 계산
        quality_score = self._calculate_quality_score(
            length=length,
            product_mentions=product_mentions,
            price_mentions=price_mentions,
            positive_count=positive_count,
            negative_count=negative_count,
            store_mentions=store_mentions,
        )

        return TranscriptQuality(
            is_valid=True,
            length=length,
            quality_score=quality_score,
            product_mention_count=product_mentions,
            price_mention_count=price_mentions,
            store_mention_count=store_mentions,
            has_negative_reviews=negative_count > 0,
            negative_product_count=negative_count,
            positive_product_count=positive_count,
            store_mismatch_warning=store_mismatch,
            rejection_reason=None,
        )

    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """키워드 등장 횟수 카운트"""
        text_lower = text.lower()
        count = 0
        for keyword in keywords:
            count += text_lower.count(keyword.lower())
        return count

    def _count_price_mentions(self, text: str) -> int:
        """가격 언급 횟수 카운트"""
        count = 0
        for pattern in self.PRICE_PATTERNS:
            matches = re.findall(pattern, text)
            count += len(matches)
        return count

    def _count_store_mentions(self, text: str, store_name: str) -> int:
        """매장 언급 횟수 카운트"""
        keywords = self.STORE_KEYWORDS.get(store_name, [store_name])
        return self._count_keywords(text, keywords)

    def _calculate_quality_score(
        self,
        length: int,
        product_mentions: int,
        price_mentions: int,
        positive_count: int,
        negative_count: int,
        store_mentions: int,
    ) -> float:
        """
        품질 점수 계산 (0.0 ~ 1.0)

        가중치:
        - 길이: 30%
        - 상품 언급: 25%
        - 가격 언급: 20%
        - 긍정 리뷰: 15%
        - 매장 언급: 10%
        """
        score = 0.0

        # 길이 점수 (300자 이상이면 만점, 최대 1000자까지 가산점)
        length_score = min(length / 1000, 1.0)
        score += length_score * 0.30

        # 상품 언급 점수 (5개 이상이면 만점)
        product_score = min(product_mentions / 5, 1.0)
        score += product_score * 0.25

        # 가격 언급 점수 (3개 이상이면 만점)
        price_score = min(price_mentions / 3, 1.0)
        score += price_score * 0.20

        # 긍정 리뷰 점수 (부정보다 긍정이 많으면 높은 점수)
        if positive_count > 0:
            sentiment_ratio = positive_count / max(positive_count + negative_count, 1)
            score += sentiment_ratio * 0.15
        else:
            score += 0.05  # 중립

        # 매장 언급 점수 (1개 이상이면 만점)
        store_score = min(store_mentions, 1.0)
        score += store_score * 0.10

        return round(min(score, 1.0), 2)

    def is_analyzable(self, transcript: str, store_name: str = None) -> bool:
        """분석 가능 여부 간단 체크"""
        result = self.validate(transcript, store_name)
        return result.is_valid

    def get_rejection_reason(self, transcript: str, store_name: str = None) -> Optional[str]:
        """거부 사유 반환"""
        result = self.validate(transcript, store_name)
        return result.rejection_reason


def main():
    """테스트 실행"""
    validator = TranscriptValidator()

    # 테스트 자막들
    test_cases = [
        ("좋은 자막", """
        오늘은 다이소 꿀템 10가지를 소개할게요!
        첫 번째는 스텐 배수구망이에요. 가격은 2천원인데 물때도 안끼고 진짜 좋아요.
        두 번째는 실리콘 주걱 3천원. 열에도 강하고 냄비에 흠집도 안 나요.
        세 번째 서랍 정리함 천원. 싹 정리되고 미니멀해져요.
        네 번째 먼지털이개 2천원. 청소할 때 필수템이에요.
        다섯 번째 밀폐용기 세트 5천원. 냉장고 정리 끝이에요.
        """),
        ("너무 짧은 자막", "다이소 추천템이에요"),
        ("상품 언급 없음", "오늘 날씨가 좋네요. 산책하기 좋은 날이에요." * 10),
    ]

    for name, transcript in test_cases:
        print(f"\n=== {name} ===")
        result = validator.validate(transcript, "다이소")
        print(f"유효: {result.is_valid}")
        print(f"길이: {result.length}자")
        print(f"품질 점수: {result.quality_score}")
        print(f"상품 언급: {result.product_mention_count}회")
        print(f"가격 언급: {result.price_mention_count}회")
        if result.rejection_reason:
            print(f"거부 사유: {result.rejection_reason}")


if __name__ == "__main__":
    main()
