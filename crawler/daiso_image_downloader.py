# -*- coding: utf-8 -*-
"""
다이소 이미지 다운로더
Playwright를 사용하여 다이소몰 이미지를 다운로드하고 Supabase Storage에 업로드합니다.

다이소몰은 핫링크 보호가 있어서 직접 이미지 URL 접근이 불가능합니다.
Playwright로 브라우저 컨텍스트에서 이미지를 다운로드해야 합니다.
"""
import os
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[!] Playwright 설치 필요: pip install playwright && playwright install chromium")

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("[!] Supabase 설치 필요: pip install supabase")

# 로컬 이미지 저장 디렉토리 (web/public에 저장하여 Vercel에서 서빙)
IMAGE_DIR = Path(__file__).parent.parent / "web" / "public" / "images" / "daiso"


class DaisoImageDownloader:
    """다이소 이미지 다운로더"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.playwright = None

        # Supabase 클라이언트
        self.supabase: Optional[Client] = None
        if SUPABASE_AVAILABLE:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                self.supabase = create_client(url, key)
                print(f"[Supabase] 연결됨")

    async def _init_browser(self):
        """브라우저 초기화"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 필요합니다")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def _close_browser(self):
        """브라우저 종료"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

    async def download_image(self, image_url: str, product_no: str) -> Optional[bytes]:
        """
        이미지 다운로드 (Playwright 사용)

        Args:
            image_url: 다이소몰 이미지 URL
            product_no: 상품 번호 (파일명용)

        Returns:
            이미지 바이트 데이터 또는 None
        """
        if not self.browser:
            await self._init_browser()

        try:
            page = await self.context.new_page()

            # 이미지 URL로 직접 이동 (브라우저 컨텍스트에서)
            response = await page.goto(image_url, timeout=30000)

            if response and response.ok:
                # 이미지 데이터 가져오기
                image_data = await response.body()
                await page.close()
                return image_data
            else:
                print(f"[!] 이미지 다운로드 실패: {response.status if response else 'No response'}")
                await page.close()
                return None

        except Exception as e:
            print(f"[!] 이미지 다운로드 오류 ({product_no}): {e}")
            return None

    async def download_image_from_product_page(self, product_url: str, product_no: str) -> Optional[bytes]:
        """
        상품 페이지에서 이미지 다운로드
        핫링크 보호 우회를 위해 상품 페이지에서 직접 이미지 추출
        """
        if not self.browser:
            await self._init_browser()

        try:
            page = await self.context.new_page()
            await page.goto(product_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)  # 이미지 로딩 대기

            # 상품 메인 이미지 찾기
            image_data = await page.evaluate('''async () => {
                // 메인 상품 이미지 선택자들
                const selectors = [
                    'img.product-image',
                    'img[alt*="상품"]',
                    '.product-detail img',
                    '.swiper-slide img',
                    'img[src*="/file/PD/"]'
                ];

                for (const selector of selectors) {
                    const img = document.querySelector(selector);
                    if (img && img.src && img.complete) {
                        return img.src;
                    }
                }

                // 첫 번째 큰 이미지 찾기
                const images = document.querySelectorAll('img');
                for (const img of images) {
                    if (img.naturalWidth > 200 && img.naturalHeight > 200) {
                        return img.src;
                    }
                }

                return null;
            }''')

            if image_data:
                # 찾은 이미지 URL로 다시 요청
                response = await page.goto(image_data, timeout=15000)
                if response and response.ok:
                    data = await response.body()
                    await page.close()
                    return data

            await page.close()
            return None

        except Exception as e:
            print(f"[!] 상품 페이지 이미지 추출 오류 ({product_no}): {e}")
            return None

    def save_image_locally(self, image_data: bytes, product_no: str) -> str:
        """
        이미지를 로컬에 저장

        Returns:
            웹에서 접근 가능한 상대 URL (/images/daiso/{product_no}.jpg)
        """
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        filename = f"{product_no}.jpg"
        filepath = IMAGE_DIR / filename

        with open(filepath, 'wb') as f:
            f.write(image_data)

        # 웹에서 접근 가능한 상대 URL 반환
        return f"/images/daiso/{product_no}.jpg"

    async def upload_to_supabase(self, image_data: bytes, product_no: str) -> Optional[str]:
        """
        Supabase Storage에 이미지 업로드

        Returns:
            공개 URL 또는 None
        """
        if not self.supabase:
            print("[!] Supabase 클라이언트가 없습니다")
            return None

        try:
            bucket_name = "product-images"
            file_path = f"daiso/{product_no}.jpg"

            # 업로드
            result = self.supabase.storage.from_(bucket_name).upload(
                file_path,
                image_data,
                {"content-type": "image/jpeg", "upsert": "true"}
            )

            # 공개 URL 생성
            public_url = self.supabase.storage.from_(bucket_name).get_public_url(file_path)
            return public_url

        except Exception as e:
            print(f"[!] Supabase 업로드 오류 ({product_no}): {e}")
            return None

    async def process_product(self, product_no: str, image_url: str, product_url: str) -> Optional[str]:
        """
        단일 상품 이미지 처리

        Returns:
            새로운 이미지 URL (/images/daiso/{product_no}.jpg)
        """
        # 이미 처리된 파일이 있으면 스킵
        existing_file = IMAGE_DIR / f"{product_no}.jpg"
        if existing_file.exists() and existing_file.stat().st_size > 1000:
            return f"/images/daiso/{product_no}.jpg"

        print(f"  처리 중: {product_no}")

        # 1. 상품 페이지에서 이미지 추출 (가장 안정적)
        image_data = None
        if product_url:
            image_data = await self.download_image_from_product_page(product_url, product_no)

        # 2. 실패하면 직접 이미지 URL 시도 (보통 실패함)
        if not image_data and image_url:
            image_data = await self.download_image(image_url, product_no)

        if not image_data:
            print(f"    -> 이미지 다운로드 실패")
            return None

        print(f"    -> 이미지 다운로드 성공 ({len(image_data)} bytes)")

        # 3. 로컬에 저장 (web/public/images/daiso/)
        new_url = self.save_image_locally(image_data, product_no)
        print(f"    -> 저장됨: {new_url}")

        return new_url

    async def process_all_daiso_images(self, limit: int = 100, update_db: bool = True):
        """
        모든 다이소 이미지 처리

        Args:
            limit: 처리할 최대 상품 수
            update_db: DB 업데이트 여부
        """
        if not self.supabase:
            print("[!] Supabase 연결이 필요합니다")
            return

        print(f"\n=== 다이소 이미지 다운로드 시작 (최대 {limit}개) ===\n")

        # 다이소몰 URL을 가진 상품 조회
        result = self.supabase.table("daiso_catalog").select(
            "product_no, image_url, product_url"
        ).like(
            "image_url", "%daisomall.co.kr%"
        ).limit(limit).execute()

        products = result.data
        print(f"처리할 상품: {len(products)}개\n")

        success_count = 0
        fail_count = 0

        for product in products:
            product_no = product.get("product_no")
            image_url = product.get("image_url")
            product_url = product.get("product_url")

            new_url = await self.process_product(product_no, image_url, product_url)

            if new_url and update_db:
                # DB 업데이트
                try:
                    self.supabase.table("daiso_catalog").update({
                        "image_url": new_url,
                        "updated_at": datetime.now().isoformat()
                    }).eq("product_no", product_no).execute()
                    success_count += 1
                except Exception as e:
                    print(f"    -> DB 업데이트 오류: {e}")
                    fail_count += 1
            elif new_url:
                success_count += 1
            else:
                fail_count += 1

            # 요청 간 대기
            await asyncio.sleep(1)

        print(f"\n=== 완료 ===")
        print(f"성공: {success_count}개")
        print(f"실패: {fail_count}개")

    async def close(self):
        """리소스 정리"""
        await self._close_browser()


async def main():
    """테스트 실행"""
    print("=== 다이소 이미지 다운로더 테스트 ===\n")

    downloader = DaisoImageDownloader(headless=True)

    try:
        # 테스트: 단일 이미지 다운로드
        test_url = "https://www.daisomall.co.kr/file/PD/20231204/yNe0TJIGqo8WdHsPXcBx1043198_00_00yNe0TJIGqo8WdHsPXcBx.jpg"
        test_product_no = "1043198"
        test_product_url = "https://www.daisomall.co.kr/pd/pdr/SCR_PDR_0001?pdNo=1043198"

        print(f"테스트 상품: {test_product_no}")
        result = await downloader.process_product(test_product_no, test_url, test_product_url)

        if result:
            print(f"\n성공! 새 URL: {result}")
        else:
            print("\n실패")

    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())
