"""
꿀템장바구니 - AI 분석기
자막 텍스트에서 상품 정보를 추출합니다.
"""
import json
import re
from typing import Optional

# 새 SDK (google-genai) 우선 사용, 없으면 레거시 fallback
try:
    from google import genai
    NEW_SDK = True
except ImportError:
    import google.generativeai as genai
    NEW_SDK = False

from config import GEMINI_API_KEY, PRODUCT_EXTRACTION_PROMPT


class AIAnalyzer:
    """Gemini API를 사용한 AI 분석기"""

    MODEL_NAME = "gemini-2.0-flash"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API 키가 필요합니다. .env 파일을 확인하세요.")

        if NEW_SDK:
            # 새 SDK: Client 기반
            self.client = genai.Client(api_key=self.api_key)
            self.model = None  # 새 SDK는 client.models.generate_content() 사용
        else:
            # 레거시 SDK
            genai.configure(api_key=self.api_key)
            self.client = None
            self.model = genai.GenerativeModel(self.MODEL_NAME)

    def extract_products(self, transcript: str, store_name: str) -> list:
        """
        자막에서 추천 상품 리스트 추출

        Args:
            transcript: 영상 자막 전체 텍스트
            store_name: 매장명 (다이소, 코스트코 등)

        Returns:
            [
                {
                    "name": "상품명",
                    "price": 가격(int),
                    "category": "카테고리",
                    "reason": "추천 이유",
                    "timestamp": 초(int),
                    "keywords": ["키워드1", "키워드2"]
                },
                ...
            ]
        """
        if not transcript or len(transcript) < 50:
            return []

        prompt = PRODUCT_EXTRACTION_PROMPT.format(
            store_name=store_name,
            transcript=transcript[:8000]  # 토큰 제한 고려
        )

        try:
            # SDK에 따라 다른 방식으로 호출
            if NEW_SDK and self.client:
                response = self.client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=prompt
                )
                text = response.text.strip()
            else:
                response = self.model.generate_content(prompt)
                text = response.text.strip()

            # JSON 추출 (마크다운 코드블록 제거)
            json_match = re.search(r'\[[\s\S]*\]', text)
            if json_match:
                products = json.loads(json_match.group())
                return self._validate_products(products)
            return []

        except json.JSONDecodeError as e:
            print(f"  [!] JSON 파싱 오류: {e}")
            return []
        except Exception as e:
            print(f"  [!] AI 분석 오류: {e}")
            return []

    def _validate_products(self, products: list) -> list:
        """추출된 상품 데이터 검증 및 정제"""
        validated = []

        for p in products:
            if not isinstance(p, dict):
                continue

            # 필수 필드 확인
            name = p.get("name", "").strip()
            if not name or len(name) < 2:
                continue

            validated.append({
                "name": name,
                "price": self._parse_price(p.get("price")),
                "category": p.get("category", "기타"),
                "reason": p.get("reason", "")[:200],  # 최대 200자
                "timestamp": self._parse_timestamp(p.get("timestamp")),
                "keywords": p.get("keywords", [name])[:5],  # 최대 5개
            })

        return validated

    def _parse_price(self, price) -> Optional[int]:
        """가격 파싱 (다양한 형식 대응)"""
        if price is None:
            return None
        if isinstance(price, int):
            return price
        if isinstance(price, float):
            return int(price)
        if isinstance(price, str):
            # "1,000원", "1000", "3천원" 등 파싱
            price = price.replace(",", "").replace("원", "").strip()
            if "천" in price:
                price = price.replace("천", "000")
            if "만" in price:
                price = price.replace("만", "0000")
            try:
                return int(re.sub(r'[^\d]', '', price))
            except ValueError:
                return None
        return None

    def _parse_timestamp(self, timestamp) -> Optional[int]:
        """타임스탬프 파싱 (초 단위)"""
        if timestamp is None:
            return None
        if isinstance(timestamp, int):
            return timestamp
        if isinstance(timestamp, float):
            return int(timestamp)
        if isinstance(timestamp, str):
            # "2:30", "150" 등 파싱
            if ":" in timestamp:
                parts = timestamp.split(":")
                try:
                    if len(parts) == 2:
                        return int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except ValueError:
                    return None
            else:
                try:
                    return int(re.sub(r'[^\d]', '', timestamp))
                except ValueError:
                    return None
        return None

    def analyze_sentiment(self, text: str) -> dict:
        """
        텍스트의 추천/비추천 감성 분석
        (확장 기능 - 비추천 상품 필터링용)
        """
        prompt = f"""
다음 텍스트에서 상품에 대한 감성을 분석해주세요.
"추천", "비추천", "중립" 중 하나로 답하고, 간단한 이유를 설명해주세요.

텍스트: {text[:1000]}

출력 형식:
{{"sentiment": "추천/비추천/중립", "reason": "이유"}}
"""
        try:
            if NEW_SDK and self.client:
                response = self.client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=prompt
                )
            else:
                response = self.model.generate_content(prompt)

            json_match = re.search(r'\{[\s\S]*\}', response.text)
            if json_match:
                return json.loads(json_match.group())
            return {"sentiment": "중립", "reason": "분석 불가"}
        except Exception:
            return {"sentiment": "중립", "reason": "분석 오류"}


def main():
    """테스트 실행"""
    # 테스트용 자막 (실제 다이소 리뷰 영상 자막 예시)
    sample_transcript = """
    안녕하세요 오늘은 다이소 꿀템 10가지를 소개해 드릴게요
    첫 번째는 스텐 배수구망이에요 가격은 2천원인데 진짜 물때가 안 껴요
    두 번째는 실리콘 주방장갑 3천원짜리인데 세척이 너무 편해요
    세 번째로 소개해드릴 건 미니 빗자루 세트예요 천원인데 화장대 청소할 때 진짜 좋아요
    네 번째는 다용도 정리함이에요 5천원인데 옷장 정리할 때 딱이에요
    이건 진짜 사지 마세요 플라스틱 도마는 칼집이 너무 많이 나요
    """

    try:
        analyzer = AIAnalyzer()
        print("AI 분석 테스트 중...")

        products = analyzer.extract_products(sample_transcript, "다이소")

        print("\n=== 추출된 상품 ===")
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product['name']}")
            print(f"   가격: {product['price']}원")
            print(f"   카테고리: {product['category']}")
            print(f"   추천 이유: {product['reason']}")

    except ValueError as e:
        print(f"오류: {e}")
        print("\n[Gemini API 키 발급 방법]")
        print("1. https://aistudio.google.com/ 접속")
        print("2. 'Get API Key' 클릭")
        print("3. API 키 생성")
        print("4. .env 파일에 GEMINI_API_KEY=발급받은키 추가")


if __name__ == "__main__":
    main()
