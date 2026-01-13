# -*- coding: utf-8 -*-
"""
다이소 전체 이미지 배치 다운로더
JSON 파일에서 상품 정보를 읽어 이미지를 다운로드합니다.
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright 설치 필요: pip install playwright && playwright install chromium")
    sys.exit(1)

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
JSON_PATH = BASE_DIR / "web" / "public" / "data" / "daiso.json"
IMAGE_DIR = BASE_DIR / "web" / "public" / "images" / "daiso"


class BatchImageDownloader:
    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None
        self.success_count = 0
        self.skip_count = 0
        self.fail_count = 0

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

    async def close_browser(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def download_image_from_page(self, product_url: str, product_no: str) -> bytes:
        """상품 페이지에서 이미지 다운로드"""
        page = await self.context.new_page()
        try:
            await page.goto(product_url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(1.5)

            # 메인 이미지 URL 추출
            image_url = await page.evaluate('''() => {
                const selectors = [
                    'img[src*="/file/PD/"]',
                    '.product-detail img',
                    '.swiper-slide img'
                ];
                for (const sel of selectors) {
                    const img = document.querySelector(sel);
                    if (img && img.src && img.naturalWidth > 200) {
                        return img.src;
                    }
                }
                const images = document.querySelectorAll('img');
                for (const img of images) {
                    if (img.naturalWidth > 200 && img.naturalHeight > 200) {
                        return img.src;
                    }
                }
                return null;
            }''')

            if image_url:
                response = await page.goto(image_url, timeout=10000)
                if response and response.ok:
                    return await response.body()
            return None
        except Exception as e:
            return None
        finally:
            await page.close()

    def save_image(self, data: bytes, product_no: str) -> str:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        filepath = IMAGE_DIR / f"{product_no}.jpg"
        with open(filepath, 'wb') as f:
            f.write(data)
        return str(filepath)

    def is_already_downloaded(self, product_no: str) -> bool:
        filepath = IMAGE_DIR / f"{product_no}.jpg"
        return filepath.exists() and filepath.stat().st_size > 5000

    async def process_batch(self, products: list, start_idx: int = 0):
        """배치 처리"""
        total = len(products)

        for i, product in enumerate(products[start_idx:], start=start_idx):
            product_no = product.get("product_no", "")
            product_url = product.get("product_url", "")

            # 숫자가 아닌 product_no는 스킵 (예: B202505145097)
            if not product_no or not product_no.isdigit():
                self.skip_count += 1
                continue

            # 이미 다운로드된 경우 스킵
            if self.is_already_downloaded(product_no):
                self.skip_count += 1
                continue

            print(f"[{i+1}/{total}] {product_no} 다운로드 중...", end=" ")

            try:
                image_data = await self.download_image_from_page(product_url, product_no)
                if image_data and len(image_data) > 5000:
                    self.save_image(image_data, product_no)
                    self.success_count += 1
                    print(f"성공 ({len(image_data):,} bytes)")
                else:
                    self.fail_count += 1
                    print("실패 (이미지 없음)")
            except Exception as e:
                self.fail_count += 1
                print(f"오류: {e}")

            # 요청 간 대기
            await asyncio.sleep(0.5)

            # 50개마다 상태 출력
            if (i + 1) % 50 == 0:
                print(f"\n=== 진행 상황: {i+1}/{total} (성공: {self.success_count}, 스킵: {self.skip_count}, 실패: {self.fail_count}) ===\n")


async def main():
    print("=== 다이소 이미지 배치 다운로더 ===\n")

    # JSON 로드
    if not JSON_PATH.exists():
        print(f"JSON 파일 없음: {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    products = data.get("products", [])
    print(f"전체 상품: {len(products)}개")

    # 이미 다운로드된 이미지 확인
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    existing = len(list(IMAGE_DIR.glob("*.jpg")))
    print(f"이미 다운로드된 이미지: {existing}개\n")

    downloader = BatchImageDownloader()

    try:
        await downloader.init_browser()
        await downloader.process_batch(products)
    finally:
        await downloader.close_browser()

    print(f"\n=== 완료 ===")
    print(f"성공: {downloader.success_count}")
    print(f"스킵: {downloader.skip_count}")
    print(f"실패: {downloader.fail_count}")


if __name__ == "__main__":
    asyncio.run(main())
