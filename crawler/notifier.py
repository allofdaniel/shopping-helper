# -*- coding: utf-8 -*-
"""
Discord/Slack 알림 시스템
새 상품이 추가되면 자동으로 알림 발송
"""

import os
import json
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class ProductNotifier:
    """새 상품 알림 발송기"""

    def __init__(self):
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')

    def format_price(self, price: Optional[int]) -> str:
        """가격 포맷팅"""
        if not price:
            return "가격 미정"
        return f"₩{price:,}"

    def create_discord_embed(self, products: List[Dict], store_name: str) -> Dict:
        """Discord Embed 메시지 생성"""

        # 매장별 색상
        colors = {
            'daiso': 0xFF6B6B,      # 빨강
            'costco': 0x005DAA,     # 파랑
            'ikea': 0xFFDB00,       # 노랑
            'oliveyoung': 0x00A651, # 초록
            'convenience': 0xFF7F00 # 주황
        }

        store_display = {
            'daiso': '🏪 다이소',
            'costco': '🛒 코스트코',
            'ikea': '🪑 이케아',
            'oliveyoung': '💄 올리브영',
            'convenience': '🏬 편의점'
        }

        # 상품 목록 (최대 10개)
        product_list = ""
        for i, p in enumerate(products[:10], 1):
            name = p.get('official_name') or p.get('name', '상품명 없음')
            price = self.format_price(p.get('official_price') or p.get('price'))
            code = p.get('official_code', '')

            product_list += f"**{i}. {name[:30]}**\n"
            product_list += f"   💰 {price}"
            if code:
                product_list += f" | 🏷️ `{code}`"
            product_list += "\n\n"

        if len(products) > 10:
            product_list += f"... 외 **{len(products) - 10}개** 더 있습니다\n"

        embed = {
            "embeds": [{
                "title": f"🆕 새 상품 {len(products)}개 추가!",
                "description": product_list,
                "color": colors.get(store_name, 0x808080),
                "author": {
                    "name": store_display.get(store_name, store_name),
                    "icon_url": "https://em-content.zobj.net/source/twitter/376/shopping-cart_1f6d2.png"
                },
                "footer": {
                    "text": "꿀템장바구니 | 유튜버 추천 꿀템 모음"
                },
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        return embed

    def create_slack_message(self, products: List[Dict], store_name: str) -> Dict:
        """Slack 메시지 생성"""

        store_display = {
            'daiso': '🏪 다이소',
            'costco': '🛒 코스트코',
            'ikea': '🪑 이케아',
            'oliveyoung': '💄 올리브영',
            'convenience': '🏬 편의점'
        }

        # 상품 목록
        product_blocks = []
        for i, p in enumerate(products[:5], 1):
            name = p.get('official_name') or p.get('name', '상품명 없음')
            price = self.format_price(p.get('official_price') or p.get('price'))

            product_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {name[:40]}*\n💰 {price}"
                }
            })

        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🆕 {store_display.get(store_name, store_name)} 새 상품 {len(products)}개!",
                        "emoji": True
                    }
                },
                {"type": "divider"},
                *product_blocks,
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"꿀템장바구니 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }]
                }
            ]
        }

        return message

    async def send_discord_notification(self, products: List[Dict], store_name: str) -> bool:
        """Discord 알림 발송"""
        if not self.discord_webhook:
            print("Discord webhook URL이 설정되지 않았습니다")
            return False

        if not products:
            return True

        embed = self.create_discord_embed(products, store_name)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.discord_webhook,
                    json=embed,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code in [200, 204]:
                    print(f"✅ Discord 알림 발송 성공: {len(products)}개 상품")
                    return True
                else:
                    print(f"❌ Discord 알림 실패: {response.status_code}")
                    return False

        except Exception as e:
            print(f"❌ Discord 알림 오류: {e}")
            return False

    async def send_slack_notification(self, products: List[Dict], store_name: str) -> bool:
        """Slack 알림 발송"""
        if not self.slack_webhook:
            print("Slack webhook URL이 설정되지 않았습니다")
            return False

        if not products:
            return True

        message = self.create_slack_message(products, store_name)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.slack_webhook,
                    json=message,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    print(f"✅ Slack 알림 발송 성공: {len(products)}개 상품")
                    return True
                else:
                    print(f"❌ Slack 알림 실패: {response.status_code}")
                    return False

        except Exception as e:
            print(f"❌ Slack 알림 오류: {e}")
            return False

    async def notify_new_products(self, products: List[Dict], store_name: str):
        """모든 채널로 알림 발송"""
        if not products:
            print("알림할 새 상품이 없습니다")
            return

        print(f"\n📢 {store_name} 새 상품 {len(products)}개 알림 발송 중...")

        # Discord
        if self.discord_webhook:
            await self.send_discord_notification(products, store_name)

        # Slack
        if self.slack_webhook:
            await self.send_slack_notification(products, store_name)


# 동기 버전 래퍼
def notify_sync(products: List[Dict], store_name: str):
    """동기 방식 알림 (GitHub Actions용)"""
    import asyncio

    notifier = ProductNotifier()

    # 이벤트 루프 생성 및 실행
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(notifier.notify_new_products(products, store_name))


if __name__ == "__main__":
    # 테스트
    test_products = [
        {"name": "테스트 상품 1", "price": 1000, "official_code": "TEST001"},
        {"name": "테스트 상품 2", "price": 2000, "official_code": "TEST002"},
    ]

    notify_sync(test_products, "daiso")
