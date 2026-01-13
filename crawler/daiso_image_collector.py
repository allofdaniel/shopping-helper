# -*- coding: utf-8 -*-
"""
다이소 이미지 수집기 (Docker용)
서버에서 실행하여 모든 다이소 이미지를 다운로드하고 Git에 푸시합니다.
"""
import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright 필요: pip install playwright && playwright install chromium")
    sys.exit(1)

# 환경 설정
DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data/daiso.json"))
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "/app/images/daiso"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
GIT_REPO = os.getenv("GIT_REPO", "")
GIT_TOKEN = os.getenv("GIT_TOKEN", "")


class DaisoImageCollector:
    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None
        self.success = 0
        self.skip = 0
        self.fail = 0

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

    async def download_image(self, product_url: str, product_no: str) -> bytes:
        page = await self.context.new_page()
        try:
            await page.goto(product_url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(1)

            img_url = await page.evaluate('''() => {
                const img = document.querySelector('img[src*="/file/PD/"]');
                if (img && img.src && img.naturalWidth > 200) return img.src;
                const images = document.querySelectorAll('img');
                for (const i of images) {
                    if (i.naturalWidth > 200 && i.naturalHeight > 200) return i.src;
                }
                return null;
            }''')

            if img_url:
                resp = await page.goto(img_url, timeout=10000)
                if resp and resp.ok:
                    return await resp.body()
            return None
        except Exception:
            return None
        finally:
            await page.close()

    def save_image(self, data: bytes, product_no: str):
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        filepath = IMAGE_DIR / f"{product_no}.jpg"
        with open(filepath, 'wb') as f:
            f.write(data)

    def is_downloaded(self, product_no: str) -> bool:
        filepath = IMAGE_DIR / f"{product_no}.jpg"
        return filepath.exists() and filepath.stat().st_size > 5000

    async def collect_all(self):
        print(f"[{datetime.now()}] 다이소 이미지 수집 시작")
        print(f"  데이터: {DATA_PATH}")
        print(f"  저장 위치: {IMAGE_DIR}")

        # JSON 로드
        if not DATA_PATH.exists():
            print(f"데이터 파일 없음: {DATA_PATH}")
            return

        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        products = data.get("products", [])
        total = len(products)
        print(f"  전체 상품: {total}개")

        # 이미 다운로드된 수
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        existing = len(list(IMAGE_DIR.glob("*.jpg")))
        print(f"  기존 이미지: {existing}개\n")

        await self.init_browser()

        try:
            for i, p in enumerate(products):
                product_no = str(p.get("product_no", ""))
                product_url = p.get("product_url", "")

                # 숫자가 아닌 상품번호 스킵
                if not product_no.isdigit():
                    self.skip += 1
                    continue

                # 이미 다운로드됨
                if self.is_downloaded(product_no):
                    self.skip += 1
                    continue

                print(f"[{i+1}/{total}] {product_no}...", end=" ", flush=True)

                img_data = await self.download_image(product_url, product_no)

                if img_data and len(img_data) > 5000:
                    self.save_image(img_data, product_no)
                    self.success += 1
                    print(f"OK ({len(img_data):,})")
                else:
                    self.fail += 1
                    print("FAIL")

                await asyncio.sleep(0.3)

                # 진행상황 출력
                if (i + 1) % 100 == 0:
                    print(f"\n=== 진행: {i+1}/{total} (성공: {self.success}, 실패: {self.fail}) ===\n")

        finally:
            await self.close_browser()

        print(f"\n[{datetime.now()}] 수집 완료")
        print(f"  성공: {self.success}")
        print(f"  스킵: {self.skip}")
        print(f"  실패: {self.fail}")

    def git_push(self):
        """Git에 이미지 푸시"""
        if not GIT_REPO or not GIT_TOKEN:
            print("Git 설정이 없어 푸시 스킵")
            return

        print("\n[Git Push] 시작...")
        try:
            # Git 설정
            subprocess.run(["git", "config", "user.email", "bot@localhost"], check=True)
            subprocess.run(["git", "config", "user.name", "Image Bot"], check=True)

            # 변경사항 추가 및 커밋
            subprocess.run(["git", "add", str(IMAGE_DIR)], check=True)
            subprocess.run([
                "git", "commit", "-m",
                f"feat: Add {self.success} Daiso images [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"
            ], check=True)

            # 푸시
            repo_url = GIT_REPO.replace("https://", f"https://{GIT_TOKEN}@")
            subprocess.run(["git", "push", repo_url, "master"], check=True)
            print("[Git Push] 완료!")

        except subprocess.CalledProcessError as e:
            print(f"[Git Push] 실패: {e}")


async def main():
    collector = DaisoImageCollector()
    await collector.collect_all()
    collector.git_push()


if __name__ == "__main__":
    asyncio.run(main())
