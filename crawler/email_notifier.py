# -*- coding: utf-8 -*-
"""
크롤링 완료 이메일 알림
Gmail SMTP로 깔끔한 HTML 이메일을 발송합니다.
PC/모바일 Gmail 모두에서 잘 보이도록 인라인 CSS + 테이블 레이아웃 사용.
"""

import os
import sys
import json
import sqlite3
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
DB_PATH = PROJECT_ROOT / 'data' / 'products.db'

STORE_NAMES = {
    'daiso': '다이소',
    'costco': '코스트코',
    'ikea': '이케아',
    'oliveyoung': '올리브영',
    'traders': '트레이더스',
    'convenience': '편의점',
}

STORE_EMOJI = {
    'daiso': '🏪',
    'costco': '🛒',
    'ikea': '🪑',
    'oliveyoung': '💄',
    'traders': '🛍️',
    'convenience': '🏬',
}


def gather_stats():
    """DB에서 크롤링 통계 수집"""
    if not DB_PATH.exists():
        logger.error(f"DB not found: {DB_PATH}")
        return None

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 전체 상품 수
    cursor.execute("SELECT COUNT(*) FROM products WHERE is_hidden = 0")
    total_products = cursor.fetchone()[0]

    # 매장별 상품 수
    cursor.execute("""
        SELECT store_key, COUNT(*) FROM products
        WHERE is_hidden = 0 GROUP BY store_key
        ORDER BY COUNT(*) DESC
    """)
    store_counts = dict(cursor.fetchall())

    # 매칭된 상품 수
    cursor.execute("SELECT COUNT(*) FROM products WHERE is_hidden = 0 AND is_matched = 1")
    matched = cursor.fetchone()[0]

    # 전체 영상 수
    try:
        cursor.execute("SELECT COUNT(*) FROM videos")
        total_videos = cursor.fetchone()[0]
    except Exception:
        total_videos = 0

    # 오늘 추가된 상품
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(
        "SELECT COUNT(*) FROM products WHERE is_hidden = 0 AND created_at LIKE ?",
        (f"{today}%",)
    )
    new_today = cursor.fetchone()[0]

    # 오늘 추가된 매장별
    cursor.execute("""
        SELECT store_key, COUNT(*) FROM products
        WHERE is_hidden = 0 AND created_at LIKE ?
        GROUP BY store_key ORDER BY COUNT(*) DESC
    """, (f"{today}%",))
    new_by_store = dict(cursor.fetchall())

    # 카테고리별 분포 (상위 5)
    cursor.execute("""
        SELECT category, COUNT(*) FROM products
        WHERE is_hidden = 0 AND category IS NOT NULL AND category != ''
        GROUP BY category ORDER BY COUNT(*) DESC LIMIT 5
    """)
    top_categories = cursor.fetchall()

    # 최근 인기 상품 (조회수 기준 상위 5)
    cursor.execute("""
        SELECT p.name, p.store_key, p.price, p.source_view_count,
               p.official_name, p.official_price
        FROM products p
        WHERE p.is_hidden = 0 AND p.source_view_count > 0
        ORDER BY p.source_view_count DESC LIMIT 5
    """)
    popular = cursor.fetchall()

    conn.close()

    return {
        'total_products': total_products,
        'store_counts': store_counts,
        'matched': matched,
        'total_videos': total_videos,
        'new_today': new_today,
        'new_by_store': new_by_store,
        'top_categories': top_categories,
        'popular_products': popular,
        'timestamp': datetime.now(),
    }


def build_prose(stats):
    """통계를 자연스러운 줄글로 변환"""
    ts = stats['timestamp']
    time_label = '오전' if ts.hour < 12 else '오후'
    hour_12 = ts.hour if ts.hour <= 12 else ts.hour - 12

    # 인사말
    greeting = f"{ts.month}월 {ts.day}일 {time_label} {hour_12}시 크롤링이 정상적으로 완료되었습니다."

    # 전체 현황
    total = stats['total_products']
    videos = stats['total_videos']
    matched = stats['matched']
    match_pct = round(matched / total * 100) if total > 0 else 0
    overview = (
        f"현재 총 {total:,}개의 상품이 등록되어 있으며, "
        f"{videos:,}개의 유튜브 영상에서 수집한 데이터입니다. "
        f"이 중 {matched:,}개({match_pct}%)가 공식 카탈로그와 매칭되어 "
        f"정확한 가격과 이미지를 제공하고 있습니다."
    )

    # 매장별 현황
    sc = stats['store_counts']
    store_parts = []
    for key, count in sc.items():
        name = STORE_NAMES.get(key, key)
        store_parts.append(f"{name} {count:,}개")
    store_line = "매장별로는 " + ", ".join(store_parts) + "입니다." if store_parts else ""

    # 오늘 신규
    new_today = stats['new_today']
    if new_today > 0:
        new_parts = []
        for key, count in stats['new_by_store'].items():
            name = STORE_NAMES.get(key, key)
            new_parts.append(f"{name} {count}개")
        new_line = (
            f"오늘 새로 추가된 상품은 {new_today}개이며, "
            + ", ".join(new_parts) + "가 추가되었습니다."
        )
    else:
        new_line = "오늘 새로 추가된 상품은 없습니다. 기존 데이터가 유지되고 있습니다."

    return greeting, overview, store_line, new_line


def build_html_email(stats):
    """Gmail 호환 반응형 HTML 이메일 생성"""
    greeting, overview, store_line, new_line = build_prose(stats)
    ts = stats['timestamp']

    # 매장별 통계 테이블 행
    store_rows = ""
    sc = stats['store_counts']
    for key, count in sorted(sc.items(), key=lambda x: -x[1]):
        emoji = STORE_EMOJI.get(key, '📦')
        name = STORE_NAMES.get(key, key)
        new_count = stats['new_by_store'].get(key, 0)
        new_badge = f'<span style="color:#16a34a;font-size:12px;"> +{new_count}</span>' if new_count > 0 else ''
        bar_width = min(round(count / max(sc.values()) * 100), 100) if sc.values() else 0
        store_rows += f"""
        <tr>
          <td style="padding:10px 12px;font-size:14px;color:#374151;border-bottom:1px solid #f3f4f6;">
            {emoji} {name}
          </td>
          <td style="padding:10px 12px;font-size:14px;color:#111827;font-weight:600;border-bottom:1px solid #f3f4f6;text-align:right;">
            {count:,}개{new_badge}
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;width:40%;">
            <div style="background:#f3f4f6;border-radius:4px;height:8px;overflow:hidden;">
              <div style="background:linear-gradient(90deg,#6366f1,#8b5cf6);height:8px;width:{bar_width}%;border-radius:4px;"></div>
            </div>
          </td>
        </tr>"""

    # 인기 상품 목록 (모바일 친화 리스트)
    popular_items = ""
    for i, p in enumerate(stats['popular_products'], 1):
        name = p[4] or p[0]  # official_name or name
        store = STORE_NAMES.get(p[1], p[1])
        price = p[5] or p[2]  # official_price or price
        price_str = f"₩{price:,}" if price else "가격 미정"
        popular_items += f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #f3f4f6;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="width:28px;vertical-align:top;padding-right:10px;">
                  <div style="background:#f3f4f6;border-radius:50%;width:24px;height:24px;text-align:center;line-height:24px;font-size:12px;color:#6b7280;font-weight:600;">{i}</div>
                </td>
                <td>
                  <p style="margin:0;font-size:14px;color:#111827;font-weight:500;">{name[:32]}</p>
                  <p style="margin:3px 0 0;font-size:12px;color:#9ca3af;">{store} &middot; {price_str}</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    # 카테고리 분포
    cat_tags = ""
    for cat, count in stats['top_categories']:
        cat_tags += (
            f'<span style="display:inline-block;background:#f0fdf4;color:#166534;'
            f'padding:4px 10px;border-radius:12px;font-size:12px;margin:3px 4px 3px 0;">'
            f'{cat} {count:,}</span>'
        )

    total = stats['total_products']
    matched = stats['matched']
    match_pct = round(matched / total * 100) if total > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">

<!-- 외부 컨테이너 -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f9fafb;">
<tr><td align="center" style="padding:24px 16px;">

<!-- 메인 카드 (max 600px) -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

  <!-- 헤더 -->
  <tr>
    <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:28px 32px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.8);letter-spacing:0.5px;">DAILY CRAWLING REPORT</p>
            <h1 style="margin:6px 0 0;font-size:22px;color:#ffffff;font-weight:700;">
              크롤링 리포트
            </h1>
            <p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.85);">
              {ts.strftime('%Y년 %m월 %d일 %H:%M')}
            </p>
          </td>
          <td align="right" style="vertical-align:top;">
            <div style="background:rgba(255,255,255,0.2);border-radius:50%;width:48px;height:48px;text-align:center;line-height:48px;font-size:24px;">
              &#x1F6D2;
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- 핵심 지표 카드 -->
  <tr>
    <td style="padding:24px 32px 0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="33%" style="text-align:center;padding:16px 8px;background:#faf5ff;border-radius:8px;">
            <p style="margin:0;font-size:24px;font-weight:700;color:#7c3aed;">{total:,}</p>
            <p style="margin:4px 0 0;font-size:11px;color:#6b7280;letter-spacing:0.3px;">전체 상품</p>
          </td>
          <td width="6"></td>
          <td width="33%" style="text-align:center;padding:16px 8px;background:#f0fdf4;border-radius:8px;">
            <p style="margin:0;font-size:24px;font-weight:700;color:#16a34a;">{stats['new_today']:,}</p>
            <p style="margin:4px 0 0;font-size:11px;color:#6b7280;letter-spacing:0.3px;">오늘 신규</p>
          </td>
          <td width="6"></td>
          <td width="33%" style="text-align:center;padding:16px 8px;background:#eff6ff;border-radius:8px;">
            <p style="margin:0;font-size:24px;font-weight:700;color:#2563eb;">{match_pct}%</p>
            <p style="margin:4px 0 0;font-size:11px;color:#6b7280;letter-spacing:0.3px;">카탈로그 매칭</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- 본문 (줄글) -->
  <tr>
    <td style="padding:24px 32px;">
      <p style="margin:0 0 14px;font-size:15px;line-height:1.7;color:#374151;">
        {greeting}
      </p>
      <p style="margin:0 0 14px;font-size:15px;line-height:1.7;color:#374151;">
        {overview}
      </p>
      <p style="margin:0 0 14px;font-size:15px;line-height:1.7;color:#374151;">
        {store_line}
      </p>
      <p style="margin:0;font-size:15px;line-height:1.7;color:#374151;">
        {new_line}
      </p>
    </td>
  </tr>

  <!-- 구분선 -->
  <tr><td style="padding:0 32px;"><div style="border-top:1px solid #e5e7eb;"></div></td></tr>

  <!-- 매장별 현황 -->
  <tr>
    <td style="padding:24px 32px;">
      <h2 style="margin:0 0 16px;font-size:16px;font-weight:700;color:#111827;">매장별 현황</h2>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <tr style="background:#f9fafb;">
          <td style="padding:8px 12px;font-size:12px;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb;">매장</td>
          <td style="padding:8px 12px;font-size:12px;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb;text-align:right;">상품 수</td>
          <td style="padding:8px 12px;font-size:12px;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb;width:40%;">비율</td>
        </tr>
        {store_rows}
      </table>
    </td>
  </tr>

  <!-- 구분선 -->
  <tr><td style="padding:0 32px;"><div style="border-top:1px solid #e5e7eb;"></div></td></tr>

  <!-- 인기 상품 TOP 5 -->
  {"" if not popular_items else f'''
  <tr>
    <td style="padding:24px 32px;">
      <h2 style="margin:0 0 16px;font-size:16px;font-weight:700;color:#111827;">인기 상품 TOP 5</h2>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        {popular_items}
      </table>
    </td>
  </tr>

  <tr><td style="padding:0 32px;"><div style="border-top:1px solid #e5e7eb;"></div></td></tr>
  '''}

  <!-- 카테고리 분포 -->
  {"" if not cat_tags else f'''
  <tr>
    <td style="padding:24px 32px;">
      <h2 style="margin:0 0 12px;font-size:16px;font-weight:700;color:#111827;">주요 카테고리</h2>
      <div>{cat_tags}</div>
    </td>
  </tr>

  <tr><td style="padding:0 32px;"><div style="border-top:1px solid #e5e7eb;"></div></td></tr>
  '''}

  <!-- CTA 버튼 -->
  <tr>
    <td align="center" style="padding:28px 32px;">
      <a href="https://kkul.app" target="_blank"
         style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#ffffff;text-decoration:none;padding:14px 36px;border-radius:8px;font-size:15px;font-weight:600;letter-spacing:0.3px;">
        꿀템장바구니 바로가기 &rarr;
      </a>
    </td>
  </tr>

  <!-- 푸터 -->
  <tr>
    <td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;text-align:center;">
        이 메일은 꿀템장바구니 자동 크롤링 시스템에서 발송되었습니다.<br>
        매일 오전 9시, 오후 9시에 자동으로 전송됩니다.
      </p>
    </td>
  </tr>

</table>
<!-- /메인 카드 -->

</td></tr>
</table>
<!-- /외부 컨테이너 -->

</body>
</html>"""
    return html


def build_plain_text(stats):
    """플레인 텍스트 버전 (HTML 미지원 클라이언트용)"""
    greeting, overview, store_line, new_line = build_prose(stats)
    ts = stats['timestamp']

    lines = [
        f"크롤링 리포트 - {ts.strftime('%Y년 %m월 %d일 %H:%M')}",
        "=" * 40,
        "",
        greeting,
        "",
        overview,
        "",
        store_line,
        "",
        new_line,
        "",
        "-" * 40,
        "매장별 현황:",
    ]

    sc = stats['store_counts']
    for key, count in sorted(sc.items(), key=lambda x: -x[1]):
        name = STORE_NAMES.get(key, key)
        new_c = stats['new_by_store'].get(key, 0)
        extra = f" (+{new_c})" if new_c > 0 else ""
        lines.append(f"  {name}: {count:,}개{extra}")

    lines += [
        "",
        f"전체: {stats['total_products']:,}개 | 영상: {stats['total_videos']:,}개",
        "",
        "꿀템장바구니: https://kkul.app",
    ]

    return "\n".join(lines)


def send_email(stats):
    """Gmail SMTP로 이메일 발송"""
    gmail_user = os.getenv('GMAIL_USER')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
    recipient = os.getenv('NOTIFY_EMAIL', gmail_user)

    if not gmail_user or not gmail_app_password:
        logger.warning("GMAIL_USER 또는 GMAIL_APP_PASSWORD가 설정되지 않았습니다. 이메일 발송을 건너뜁니다.")
        return False

    ts = stats['timestamp']
    new_today = stats['new_today']
    total = stats['total_products']

    # 제목: 간결하게
    if new_today > 0:
        subject = f"크롤링 완료 — 신규 {new_today}개, 전체 {total:,}개 ({ts.strftime('%m/%d')})"
    else:
        subject = f"크롤링 완료 — 전체 {total:,}개 유지 ({ts.strftime('%m/%d')})"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"꿀템장바구니 <{gmail_user}>"
    msg['To'] = recipient

    # 플레인 텍스트 + HTML
    plain = build_plain_text(stats)
    html = build_html_email(stats)

    msg.attach(MIMEText(plain, 'plain', 'utf-8'))
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, [recipient], msg.as_string())

        logger.info(f"이메일 발송 완료 -> {recipient}")
        return True

    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False


def save_preview(stats, output_path=None):
    """이메일 미리보기 HTML 파일 생성 (디버그용)"""
    if output_path is None:
        output_path = BASE_DIR / 'email_preview.html'

    html = build_html_email(stats)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info(f"미리보기 저장: {output_path}")
    return output_path


def main():
    """메인: 통계 수집 -> 이메일 발송"""
    logger.info("=== 이메일 알림 시작 ===")

    stats = gather_stats()
    if not stats:
        logger.error("통계 수집 실패")
        sys.exit(1)

    # 이메일 발송
    sent = send_email(stats)

    # 미리보기 파일도 저장 (디버그)
    if '--preview' in sys.argv:
        save_preview(stats)

    logger.info("=== 이메일 알림 완료 ===")
    return sent


if __name__ == '__main__':
    main()
