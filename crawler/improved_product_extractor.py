# -*- coding: utf-8 -*-
"""
개선된 AI 기반 상품 추출기
- 자막 검증 통합
- 부정 리뷰 필터링
- 신뢰도 점수 반환
- 중복 제거
"""
import json
import os
import re
from typing import Optional, List, Dict
from transcript_validator import TranscriptValidator

# 환경 변수에서 API 키 로드
try:
    from config import OPENAI_API_KEY, GEMINI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Google Gemini - 새 SDK 우선, 레거시 fallback
try:
    from google import genai as new_genai
    GEMINI_AVAILABLE = True
    GEMINI_NEW_SDK = True
except ImportError:
    try:
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
        GEMINI_NEW_SDK = False
    except ImportError:
        GEMINI_AVAILABLE = False
        GEMINI_NEW_SDK = False


# 매장별 가격 범위
STORE_PRICE_RANGES = {
    "다이소": (1000, 10000),
    "이케아": (1000, 500000),
    "코스트코": (5000, 200000),
}

# 개선된 프롬프트
IMPROVED_EXTRACTION_PROMPT = """
당신은 {store_name} 추천 영상에서 상품 정보를 추출하는 전문가입니다.

## 반드시 지켜야 할 핵심 규칙

### 1. 해당 매장 상품만 추출
- 이 영상은 **{store_name}** 추천 영상입니다.
- **{store_name} 상품만** 추출하세요.
- 다른 매장(올리브영, 세리아, 미니소 등) 상품은 절대 추출하지 마세요.
{store_specific_rules}

### 2. 긍정적 추천만 추출
다음 표현이 있을 때만 추출:
- "추천", "강추", "꿀템", "필수템", "인생템"
- "좋아요", "대박", "최고", "가성비 좋아요"
- "꼭 사세요", "후회 없어요"

다음 표현이 있으면 is_recommended: false:
- "비추", "별로", "후회", "실패"
- "사지 마세요", "돈 아까워요"
- "안 좋아요", "품질 별로"

### 3. 맥락 이해 (매우 중요!)
단순히 단어가 등장했다고 상품으로 추출하지 마세요.

잘못된 예시:
- "배수구가 막혀서..." → 배수구망을 추천하는 게 아님
- "A보다 B가 나아요"의 A → 비교 대상일 뿐, 추천이 아님
- "예전에 샀던 000" → 과거 구매 언급일 뿐, 현재 추천 아님

올바른 예시:
- "스텐 배수구망 2천원인데 진짜 좋아요 강추!" → 이건 추천

### 4. 구체적인 상품명과 가격 필수
- 상품명이 불명확하면 추출하지 마세요.
- "이것저것", "여러가지" 같은 모호한 표현은 추출 제외.
- 가격 범위: {price_range_min:,}원 ~ {price_range_max:,}원

### 5. 신뢰도 점수 기준
- 0.9 이상: 상품명 + 가격 + 추천 이유 모두 명확
- 0.7~0.9: 상품명과 추천 의도 명확, 가격 불확실
- 0.5~0.7: 상품이 언급되었으나 세부정보 불확실
- 0.5 미만: 추측성 → 추출하지 마세요

## 출력 형식 (JSON 배열만 출력, 다른 설명 없이!)

```json
[
  {{
    "name": "구체적 상품명",
    "price": 가격숫자,
    "category": "카테고리",
    "reason": "추천 이유 1-2문장",
    "recommendation_quote": "실제 영상에서 말한 추천 멘트 그대로 인용",
    "timestamp": 초단위숫자,
    "keywords": ["키워드1", "키워드2"],
    "confidence": 0.0~1.0,
    "is_recommended": true/false
  }}
]
```

## 자막

{transcript}
"""

# 매장별 추가 규칙
STORE_SPECIFIC_RULES = {
    "다이소": """
- 올리브영/세리아/미니소 제품은 제외
- "다이소에서 산 000" = 다이소 상품 O
- "다이소처럼 저렴한 000" = 다이소 상품 X
- 가격대: 대부분 1,000~5,000원""",
    "이케아": """
- 상품명이 스웨덴어인 경우가 많음 (KALLAX, MALM, LACK 등)
- 한글명과 스웨덴어명 둘 다 있으면 스웨덴어명 우선
- 조립 가구가 많음""",
    "코스트코": """
- 커클랜드(Kirkland) 브랜드는 코스트코 PB 상품
- 멤버십 전용 매장 상품만 해당
- 식품류 많음, 대용량 제품 많음"""
}


class ImprovedProductExtractor:
    """개선된 AI 상품 추출기"""

    # 최소 신뢰도 (이 이하는 필터링)
    MIN_CONFIDENCE = 0.5

    def __init__(self, provider: str = "auto", test_mode: bool = False):
        """
        Args:
            provider: "openai", "gemini", "auto"
            test_mode: True면 실제 API 호출 안 함
        """
        self.provider = provider
        self.test_mode = test_mode
        self.validator = TranscriptValidator()

        if not test_mode:
            self._setup_provider()

    def _setup_provider(self):
        """AI 제공자 설정"""
        if self.provider == "auto":
            if GEMINI_AVAILABLE and GEMINI_API_KEY:
                self.provider = "gemini"
            elif OPENAI_AVAILABLE and OPENAI_API_KEY:
                self.provider = "openai"
            else:
                raise ValueError("사용 가능한 AI API가 없습니다.")

        if self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ImportError("google-genai 패키지를 설치하세요: pip install google-genai")
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY가 필요합니다")

            self.model_name = "gemini-2.0-flash"

            if GEMINI_NEW_SDK:
                # 새 SDK: Client 기반
                self.gemini_client = new_genai.Client(api_key=GEMINI_API_KEY)
                self.model = None
            else:
                # 레거시 SDK
                genai.configure(api_key=GEMINI_API_KEY)
                self.gemini_client = None
                model_names = ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-pro"]
                self.model = None
                for model_name in model_names:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        self.model_name = model_name
                        break
                    except Exception:
                        continue
                if self.model is None:
                    self.model = genai.GenerativeModel("gemini-pro")

        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai 패키지를 설치하세요")
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 필요합니다")
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def validate_transcript(self, transcript: str, store_name: str = None) -> bool:
        """자막 유효성 검증"""
        result = self.validator.validate(transcript, store_name)
        return result.is_valid

    def extract_products(self, transcript: str, store_name: str = "다이소") -> List[Dict]:
        """
        자막에서 상품 추출

        Args:
            transcript: 영상 자막
            store_name: 매장명

        Returns:
            추출된 상품 리스트
        """
        # 1. 자막 검증
        validation = self.validator.validate(transcript, store_name)
        if not validation.is_valid:
            print(f"[자막 검증 실패] {validation.rejection_reason}")
            return []

        # 2. 테스트 모드면 바로 리턴
        if self.test_mode:
            return []

        # 3. AI 추출
        prompt = self.build_prompt(transcript, store_name)

        try:
            if self.provider == "gemini":
                response = self._extract_with_gemini(prompt)
            elif self.provider == "openai":
                response = self._extract_with_openai(prompt)
            else:
                return []

            # 4. 파싱 및 필터링
            products = self._parse_response(response)

            # 5. 중복 제거
            products = self._remove_duplicates(products)

            return products

        except Exception as e:
            print(f"상품 추출 오류: {e}")
            return []

    def build_prompt(self, transcript: str, store_name: str) -> str:
        """프롬프트 생성"""
        # 자막이 너무 길면 자르기
        max_chars = 15000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "...(생략)"

        # 매장별 가격 범위
        price_range = STORE_PRICE_RANGES.get(store_name, (1000, 100000))

        # 매장별 추가 규칙
        store_rules = STORE_SPECIFIC_RULES.get(store_name, "")

        return IMPROVED_EXTRACTION_PROMPT.format(
            store_name=store_name,
            store_specific_rules=store_rules,
            price_range_min=price_range[0],
            price_range_max=price_range[1],
            transcript=transcript
        )

    def _extract_with_gemini(self, prompt: str) -> str:
        """Gemini로 추출"""
        if GEMINI_NEW_SDK and self.gemini_client:
            # 새 SDK
            response = self.gemini_client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        else:
            # 레거시 SDK
            response = self.model.generate_content(prompt)
            return response.text

    def _extract_with_openai(self, prompt: str) -> str:
        """OpenAI로 추출"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # 더 정확한 모델 사용
            messages=[
                {
                    "role": "system",
                    "content": "당신은 영상에서 추천 상품을 정확하게 추출하는 전문가입니다. "
                               "반드시 JSON 배열로만 응답하세요. "
                               "추측으로 상품을 만들어내지 마세요."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # 더 일관된 결과
            max_tokens=3000
        )
        return response.choices[0].message.content

    def _parse_response(self, response_text: str, min_confidence: float = None) -> List[Dict]:
        """AI 응답 파싱"""
        if not response_text:
            return []

        if min_confidence is None:
            min_confidence = self.MIN_CONFIDENCE

        # 마크다운 코드 블록 제거
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)

        # JSON 배열 추출
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            return []

        try:
            products = json.loads(json_match.group())
            if not isinstance(products, list):
                return []

            valid_products = []
            for p in products:
                if not isinstance(p, dict):
                    continue

                name = str(p.get("name", "")).strip()
                if not name or len(name) < 2:
                    continue

                # 비추천 상품 필터링
                if p.get("is_recommended") is False:
                    continue

                # 신뢰도 필터링
                confidence = p.get("confidence", 0.5)
                if isinstance(confidence, str):
                    try:
                        confidence = float(confidence)
                    except:
                        confidence = 0.5

                if confidence < min_confidence:
                    continue

                # 가격 정규화
                price = self._normalize_price(p.get("price"))

                valid_products.append({
                    "name": name,
                    "price": price,
                    "category": str(p.get("category", "")).strip(),
                    "reason": str(p.get("reason", "")).strip(),
                    "recommendation_quote": str(p.get("recommendation_quote", "")).strip(),
                    "timestamp": self._normalize_timestamp(p.get("timestamp")),
                    "keywords": p.get("keywords", []) if isinstance(p.get("keywords"), list) else [],
                    "confidence": round(confidence, 2),
                    "is_recommended": True,
                })

            return valid_products

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return []

    def _normalize_price(self, price) -> Optional[int]:
        """가격 정규화"""
        if price is None:
            return None

        if isinstance(price, int):
            return price

        if isinstance(price, float):
            return int(price)

        if isinstance(price, str):
            # "2,000원", "2천원", "5000" 등 처리
            price_str = price.replace(",", "").replace("원", "").strip()

            # "2천", "5만" 처리
            if "천" in price_str:
                try:
                    num = float(price_str.replace("천", ""))
                    return int(num * 1000)
                except:
                    pass
            elif "만" in price_str:
                try:
                    num = float(price_str.replace("만", ""))
                    return int(num * 10000)
                except:
                    pass
            else:
                try:
                    return int(price_str)
                except:
                    pass

        return None

    def _normalize_timestamp(self, timestamp) -> Optional[int]:
        """타임스탬프 정규화 (초 단위)"""
        if timestamp is None:
            return None

        if isinstance(timestamp, int):
            return timestamp

        if isinstance(timestamp, float):
            return int(timestamp)

        if isinstance(timestamp, str):
            # "2:30" 형식 처리
            if ":" in timestamp:
                parts = timestamp.split(":")
                try:
                    if len(parts) == 2:
                        return int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except:
                    pass
            else:
                try:
                    return int(timestamp)
                except:
                    pass

        return None

    def _remove_duplicates(self, products: List[Dict]) -> List[Dict]:
        """중복 상품 제거 (이름 유사도 기반)"""
        if len(products) <= 1:
            return products

        unique_products = []
        seen_names = set()

        for product in products:
            name = product.get("name", "").lower()
            # 공백, 특수문자 제거하여 정규화
            normalized = re.sub(r'[^\w가-힣]', '', name)

            # 이미 유사한 이름이 있는지 확인
            is_duplicate = False
            for seen in seen_names:
                # 간단한 유사도 체크 (70% 이상 겹치면 중복)
                if self._is_similar(normalized, seen, threshold=0.7):
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_names.add(normalized)
                unique_products.append(product)

        return unique_products

    def _is_similar(self, s1: str, s2: str, threshold: float = 0.7) -> bool:
        """두 문자열의 유사도 체크"""
        if not s1 or not s2:
            return False

        # 하나가 다른 하나를 포함하면 유사
        if s1 in s2 or s2 in s1:
            return True

        # 글자 겹침 비율
        set1 = set(s1)
        set2 = set(s2)
        intersection = set1 & set2
        union = set1 | set2

        if not union:
            return False

        jaccard = len(intersection) / len(union)
        return jaccard >= threshold


def main():
    """테스트 실행"""
    extractor = ImprovedProductExtractor(test_mode=True)

    # 테스트 자막
    test_transcript = """
    오늘은 다이소 꿀템 5가지를 소개할게요!

    첫 번째는 스텐 배수구망이에요. 가격은 2천원인데 물때도 안끼고 진짜 좋아요.
    이거 없으면 주방 청소 못해요.

    두 번째는 실리콘 주걱 3천원. 열에 강해서 코팅팬에 딱이에요.

    세 번째로 다이소 선풍기는 비추해요. 소음이 너무 심하고 바람도 약해요.
    이건 사지 마세요.

    네 번째 밀폐용기 세트 5천원. 냉장고 정리 끝이에요!
    """

    print("=== 개선된 상품 추출기 테스트 ===\n")

    # 자막 검증
    is_valid = extractor.validate_transcript(test_transcript, "다이소")
    print(f"자막 유효성: {is_valid}")

    # 프롬프트 확인
    prompt = extractor.build_prompt(test_transcript, "다이소")
    print(f"\n프롬프트 길이: {len(prompt)}자")
    print("프롬프트에 포함된 키워드:")
    print(f"  - '비추천': {'비추천' in prompt}")
    print(f"  - 'confidence': {'confidence' in prompt}")
    print(f"  - 'is_recommended': {'is_recommended' in prompt}")
    print(f"  - '실제': {'실제' in prompt}")

    # 파싱 테스트
    test_response = '''
    [
        {"name": "스텐 배수구망", "price": 2000, "confidence": 0.95, "is_recommended": true},
        {"name": "실리콘 주걱", "price": 3000, "confidence": 0.9, "is_recommended": true},
        {"name": "다이소 선풍기", "price": 5000, "confidence": 0.8, "is_recommended": false},
        {"name": "밀폐용기 세트", "price": 5000, "confidence": 0.85, "is_recommended": true}
    ]
    '''

    products = extractor._parse_response(test_response)
    print(f"\n파싱된 상품 ({len(products)}개, 비추천 제외됨):")
    for p in products:
        print(f"  - {p['name']}: {p['price']}원 (신뢰도: {p['confidence']})")


if __name__ == "__main__":
    main()
