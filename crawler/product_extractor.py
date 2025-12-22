# -*- coding: utf-8 -*-
"""
AI 기반 상품 추출기
유튜브 영상 자막에서 추천 상품을 추출합니다.
"""
import json
import os
import re
from typing import Optional
from config import OPENAI_API_KEY, GEMINI_API_KEY, PRODUCT_EXTRACTION_PROMPT

# OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Google Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class ProductExtractor:
    """AI를 사용하여 영상 자막에서 상품 정보 추출"""

    def __init__(self, provider: str = "auto"):
        """
        Args:
            provider: "openai", "gemini", "auto" (자동 선택)
        """
        self.provider = provider
        self._setup_provider()

    def _setup_provider(self):
        """AI 제공자 설정"""
        if self.provider == "auto":
            # Gemini 우선 (무료 티어 있음)
            if GEMINI_AVAILABLE and GEMINI_API_KEY:
                self.provider = "gemini"
            elif OPENAI_AVAILABLE and OPENAI_API_KEY:
                self.provider = "openai"
            else:
                raise ValueError("사용 가능한 AI API가 없습니다. OPENAI_API_KEY 또는 GEMINI_API_KEY를 설정하세요.")

        if self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ImportError("google-generativeai 패키지를 설치하세요: pip install google-generativeai")
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY가 필요합니다.")
            genai.configure(api_key=GEMINI_API_KEY)
            # 모델 우선순위: gemini-2.0-flash > gemini-1.5-flash > gemini-pro
            model_names = ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-pro"]
            self.model = None
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    break
                except Exception:
                    continue
            if self.model is None:
                self.model = genai.GenerativeModel("gemini-pro")

        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai 패키지를 설치하세요: pip install openai")
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 필요합니다.")
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def extract_products(self, transcript: str, store_name: str = "다이소") -> list:
        """
        자막에서 추천 상품 추출

        Args:
            transcript: 영상 자막 텍스트
            store_name: 매장 이름 (다이소, 코스트코 등)

        Returns:
            추출된 상품 리스트
        """
        if not transcript or len(transcript.strip()) < 50:
            return []

        # 자막이 너무 길면 앞부분만 사용 (토큰 제한)
        max_chars = 15000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "..."

        prompt = PRODUCT_EXTRACTION_PROMPT.format(
            store_name=store_name,
            transcript=transcript
        )

        try:
            if self.provider == "gemini":
                return self._extract_with_gemini(prompt)
            elif self.provider == "openai":
                return self._extract_with_openai(prompt)
        except Exception as e:
            print(f"상품 추출 오류: {e}")
            return []

    def _extract_with_gemini(self, prompt: str) -> list:
        """Gemini로 추출"""
        response = self.model.generate_content(prompt)
        return self._parse_response(response.text)

    def _extract_with_openai(self, prompt: str) -> list:
        """OpenAI로 추출"""
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 영상에서 추천 상품을 추출하는 전문가입니다. 반드시 JSON 배열로만 응답하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return self._parse_response(response.choices[0].message.content)

    def _parse_response(self, response_text: str) -> list:
        """AI 응답에서 JSON 파싱"""
        if not response_text:
            return []

        # JSON 블록 추출
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            return []

        try:
            products = json.loads(json_match.group())
            if not isinstance(products, list):
                return []

            # 유효성 검사 및 정규화
            valid_products = []
            for p in products:
                if isinstance(p, dict) and p.get("name"):
                    valid_products.append({
                        "name": str(p.get("name", "")).strip(),
                        "price": int(p.get("price", 0)) if p.get("price") else None,
                        "category": str(p.get("category", "")).strip(),
                        "reason": str(p.get("reason", "")).strip(),
                        "timestamp": int(p.get("timestamp", 0)) if p.get("timestamp") else None,
                        "keywords": p.get("keywords", []) if isinstance(p.get("keywords"), list) else [],
                    })

            return valid_products

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return []


def test_extractor():
    """테스트"""
    # 샘플 자막
    sample_transcript = """
    오늘은 다이소 꿀템 10가지를 소개할게요.
    첫 번째는 스텐 배수구망이에요. 가격은 2천원인데 물때도 안끼고 진짜 좋아요.
    두 번째는 실리콘 주걱 3천원짜리예요. 열에도 강하고 냄비에 흠집도 안 나요.
    세 번째 서랍 정리함 천원이에요. 싹 정리되고 미니멀해져요.
    네 번째 먼지털이개 2천원. 전 진짜 이거 없으면 청소 못해요.
    다섯 번째 밀폐용기 세트 5천원. 냉장고 정리 끝이에요.
    """

    try:
        extractor = ProductExtractor(provider="auto")
        print(f"사용 중인 AI: {extractor.provider}")

        products = extractor.extract_products(sample_transcript, "다이소")

        print(f"\n=== 추출된 상품 ({len(products)}개) ===")
        for i, p in enumerate(products, 1):
            print(f"\n{i}. {p['name']}")
            if p.get('price'):
                print(f"   가격: {p['price']}원")
            if p.get('category'):
                print(f"   카테고리: {p['category']}")
            if p.get('reason'):
                print(f"   추천 이유: {p['reason']}")
            if p.get('keywords'):
                print(f"   키워드: {', '.join(p['keywords'])}")

    except Exception as e:
        print(f"테스트 실패: {e}")
        print("\n[AI API 키 설정 방법]")
        print("1. .env 파일에 다음 중 하나 추가:")
        print("   GEMINI_API_KEY=your_key  (권장 - 무료)")
        print("   OPENAI_API_KEY=your_key")
        print("\n2. Gemini API 키 발급:")
        print("   https://makersuite.google.com/app/apikey")


if __name__ == "__main__":
    test_extractor()
