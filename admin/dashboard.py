"""
꿀템장바구니 - 관리자 대시보드
Streamlit 기반 상품 검수 및 승인 인터페이스
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# 크롤러 모듈 경로 추가 (절대 경로 사용)
crawler_path = Path(__file__).resolve().parent.parent / "crawler"
sys.path.insert(0, str(crawler_path))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(crawler_path / ".env")

import streamlit as st
import pandas as pd
from database import Database
from config import STORE_CATEGORIES

# 페이지 설정
st.set_page_config(
    page_title="꿀템장바구니 관리자",
    page_icon="🛒",
    layout="wide",
)

# 데이터베이스 연결
@st.cache_resource
def get_db():
    return Database()

db = get_db()


def get_detailed_stats():
    """상세 통계 조회"""
    cursor = db.conn.cursor()
    stats = {}

    # 기본 통계
    cursor.execute("SELECT COUNT(*) FROM videos")
    stats["total_videos"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products")
    stats["total_products"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products WHERE is_approved = 1")
    stats["approved_products"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products WHERE is_approved = 0 AND is_hidden = 0")
    stats["pending_products"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products WHERE is_hidden = 1")
    stats["hidden_products"] = cursor.fetchone()[0]

    # 품번 매칭 통계
    cursor.execute("SELECT COUNT(*) FROM products WHERE official_code IS NOT NULL AND official_code != ''")
    stats["matched_products"] = cursor.fetchone()[0]

    # 카테고리별 통계
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM products
        WHERE is_approved = 1
        GROUP BY category
        ORDER BY count DESC
    """)
    stats["by_category"] = {row[0] or "미분류": row[1] for row in cursor.fetchall()}

    # 채널별 통계
    cursor.execute("""
        SELECT v.channel_title, COUNT(p.id) as count
        FROM videos v
        JOIN products p ON v.video_id = p.video_id
        WHERE p.is_approved = 1
        GROUP BY v.channel_id
        ORDER BY count DESC
        LIMIT 10
    """)
    stats["by_channel"] = {row[0]: row[1] for row in cursor.fetchall()}

    # 일별 수집 통계 (최근 7일)
    cursor.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM products
        WHERE created_at >= date('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """)
    stats["daily_products"] = {row[0]: row[1] for row in cursor.fetchall()}

    # 가격대별 분포
    cursor.execute("""
        SELECT
            CASE
                WHEN COALESCE(official_price, price) < 5000 THEN '5천원 미만'
                WHEN COALESCE(official_price, price) < 10000 THEN '5천~1만원'
                WHEN COALESCE(official_price, price) < 30000 THEN '1만~3만원'
                WHEN COALESCE(official_price, price) < 50000 THEN '3만~5만원'
                ELSE '5만원 이상'
            END as price_range,
            COUNT(*) as count
        FROM products
        WHERE is_approved = 1 AND (official_price IS NOT NULL OR price IS NOT NULL)
        GROUP BY price_range
    """)
    stats["by_price_range"] = {row[0]: row[1] for row in cursor.fetchall()}

    return stats


def bulk_approve_products(product_ids: list):
    """벌크 승인"""
    cursor = db.conn.cursor()
    cursor.executemany(
        "UPDATE products SET is_approved = 1 WHERE id = ?",
        [(pid,) for pid in product_ids]
    )
    db.conn.commit()
    return len(product_ids)


def bulk_hide_products(product_ids: list):
    """벌크 숨김"""
    cursor = db.conn.cursor()
    cursor.executemany(
        "UPDATE products SET is_hidden = 1 WHERE id = ?",
        [(pid,) for pid in product_ids]
    )
    db.conn.commit()
    return len(product_ids)


def export_products_to_json():
    """승인된 상품 JSON 내보내기"""
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT p.*, v.channel_title, v.channel_id, v.view_count as video_view_count
        FROM products p
        LEFT JOIN videos v ON p.video_id = v.video_id
        WHERE p.is_approved = 1
        ORDER BY p.source_view_count DESC
    """)
    columns = [desc[0] for desc in cursor.description]
    products = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return json.dumps(products, ensure_ascii=False, indent=2, default=str)


def export_products_to_csv():
    """승인된 상품 CSV 내보내기"""
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT
            p.id, p.name, p.official_name, p.price, p.official_price,
            p.category, p.store_key, p.official_code, p.official_product_url,
            v.channel_title, v.view_count as video_views
        FROM products p
        LEFT JOIN videos v ON p.video_id = v.video_id
        WHERE p.is_approved = 1
        ORDER BY p.source_view_count DESC
    """)
    columns = [desc[0] for desc in cursor.description]
    products = [dict(zip(columns, row)) for row in cursor.fetchall()]
    df = pd.DataFrame(products)
    return df.to_csv(index=False)


def main():
    st.title("🛒 꿀템장바구니 관리자 대시보드")

    # 사이드바 - 통계
    with st.sidebar:
        st.header("📊 통계")
        stats = db.get_stats()

        col1, col2 = st.columns(2)
        col1.metric("총 영상", stats["total_videos"])
        col2.metric("총 상품", stats["total_products"])

        col3, col4 = st.columns(2)
        col3.metric("승인됨", stats["approved_products"])
        col4.metric("대기중", stats["pending_products"])

        st.divider()
        st.subheader("매장별 현황")
        for store_key, count in stats["by_store"].items():
            store_name = STORE_CATEGORIES.get(store_key, {}).get("name", store_key)
            st.write(f"• {store_name}: {count}개")

        st.divider()
        if st.button("🔄 새로고침"):
            st.cache_resource.clear()
            st.rerun()

    # 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 승인 대기",
        "✅ 승인된 상품",
        "🎬 수집된 영상",
        "📊 상세 통계",
        "⚙️ 관리 도구"
    ])

    # 탭 1: 승인 대기 상품
    with tab1:
        st.subheader("승인 대기 상품")

        # 필터 옵션
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            store_filter = st.selectbox(
                "매장 필터",
                ["전체"] + [v["name"] for v in STORE_CATEGORIES.values()],
                key="pending_store_filter"
            )
        with filter_col2:
            matched_filter = st.selectbox(
                "품번 매칭",
                ["전체", "매칭됨", "미매칭"],
                key="pending_matched_filter"
            )
        with filter_col3:
            sort_option = st.selectbox(
                "정렬",
                ["최신순", "조회수순", "가격순"],
                key="pending_sort"
            )

        # 쿼리 구성
        cursor = db.conn.cursor()
        query = """
            SELECT p.*, v.title as video_title, v.channel_title, v.thumbnail_url
            FROM products p
            LEFT JOIN videos v ON p.video_id = v.video_id
            WHERE p.is_approved = 0 AND p.is_hidden = 0
        """
        params = []

        if store_filter != "전체":
            store_key = [k for k, v in STORE_CATEGORIES.items() if v["name"] == store_filter][0]
            query += " AND p.store_key = ?"
            params.append(store_key)

        if matched_filter == "매칭됨":
            query += " AND p.official_code IS NOT NULL AND p.official_code != ''"
        elif matched_filter == "미매칭":
            query += " AND (p.official_code IS NULL OR p.official_code = '')"

        if sort_option == "최신순":
            query += " ORDER BY p.created_at DESC"
        elif sort_option == "조회수순":
            query += " ORDER BY p.source_view_count DESC"
        else:
            query += " ORDER BY COALESCE(p.official_price, p.price) ASC"

        query += " LIMIT 100"
        cursor.execute(query, params)
        pending = [dict(row) for row in cursor.fetchall()]

        if not pending:
            st.info("승인 대기 중인 상품이 없습니다.")
        else:
            # 벌크 작업 UI
            st.markdown("---")
            bulk_col1, bulk_col2, bulk_col3, bulk_col4 = st.columns([2, 1, 1, 1])

            # 세션 상태 초기화
            if "selected_pending" not in st.session_state:
                st.session_state.selected_pending = set()

            with bulk_col1:
                if st.checkbox("전체 선택", key="select_all_pending"):
                    st.session_state.selected_pending = {p["id"] for p in pending}
                else:
                    if len(st.session_state.selected_pending) == len(pending):
                        st.session_state.selected_pending = set()

            with bulk_col2:
                st.write(f"선택: {len(st.session_state.selected_pending)}개")

            with bulk_col3:
                if st.button("✅ 선택 승인", disabled=len(st.session_state.selected_pending) == 0):
                    count = bulk_approve_products(list(st.session_state.selected_pending))
                    st.success(f"{count}개 상품 승인 완료")
                    st.session_state.selected_pending = set()
                    st.rerun()

            with bulk_col4:
                if st.button("❌ 선택 숨김", disabled=len(st.session_state.selected_pending) == 0):
                    count = bulk_hide_products(list(st.session_state.selected_pending))
                    st.warning(f"{count}개 상품 숨김 처리")
                    st.session_state.selected_pending = set()
                    st.rerun()

            st.markdown("---")

            for product in pending:
                with st.container():
                    col0, col1, col2, col3 = st.columns([0.5, 1, 3, 1])

                    with col0:
                        is_selected = st.checkbox(
                            "",
                            value=product["id"] in st.session_state.selected_pending,
                            key=f"select_{product['id']}"
                        )
                        if is_selected:
                            st.session_state.selected_pending.add(product["id"])
                        else:
                            st.session_state.selected_pending.discard(product["id"])

                    with col1:
                        # 썸네일
                        if product.get("official_image_url"):
                            st.image(product["official_image_url"], width=100)
                        elif product.get("thumbnail_url"):
                            st.image(product["thumbnail_url"], width=100)
                        else:
                            st.write("🖼️ 이미지 없음")

                    with col2:
                        st.markdown(f"**{product['name']}**")
                        price = product.get('official_price') or product.get('price') or 0
                        st.write(f"💰 {price:,}원 | 📁 {product.get('category', '기타')}")
                        st.write(f"💡 {product.get('reason', '')}")
                        st.caption(f"출처: {product.get('video_title', '')} ({product.get('channel_title', '')})")

                        if product.get("official_code"):
                            st.success(f"✓ 품번 매칭: {product['official_code']}")
                        else:
                            st.warning("⚠️ 품번 미매칭")

                    with col3:
                        if st.button("✅ 승인", key=f"approve_{product['id']}"):
                            db.approve_product(product["id"])
                            st.rerun()

                        if st.button("❌ 숨김", key=f"hide_{product['id']}"):
                            db.hide_product(product["id"])
                            st.rerun()

                    st.divider()

    # 탭 2: 승인된 상품
    with tab2:
        st.subheader("승인된 상품 목록")

        # 매장 필터
        store_options = ["전체"] + [v["name"] for v in STORE_CATEGORIES.values()]
        selected_store = st.selectbox("매장 선택", store_options)

        if selected_store == "전체":
            # 모든 매장 상품 조회
            all_products = []
            for store_key in STORE_CATEGORIES.keys():
                products = db.get_products_by_store(store_key, approved_only=True, limit=50)
                all_products.extend(products)
            # 조회수 순 정렬
            all_products.sort(key=lambda x: x.get("source_view_count", 0), reverse=True)
            approved = all_products[:50]
        else:
            # 선택된 매장만
            store_key = [k for k, v in STORE_CATEGORIES.items() if v["name"] == selected_store][0]
            approved = db.get_products_by_store(store_key, approved_only=True, limit=50)

        if not approved:
            st.info("승인된 상품이 없습니다.")
        else:
            # 그리드 레이아웃
            cols = st.columns(3)
            for i, product in enumerate(approved):
                with cols[i % 3]:
                    with st.container():
                        if product.get("official_image_url"):
                            st.image(product["official_image_url"], use_container_width=True)

                        st.markdown(f"**{product['name']}**")
                        st.write(f"💰 {product.get('price', '?')}원")

                        if product.get("official_code"):
                            st.caption(f"품번: {product['official_code']}")

                        if product.get("official_product_url"):
                            st.link_button("🔗 매장 보기", product["official_product_url"])

                        st.divider()

    # 탭 3: 수집된 영상
    with tab3:
        st.subheader("수집된 YouTube 영상")

        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT v.*, COUNT(p.id) as product_count
            FROM videos v
            LEFT JOIN products p ON v.video_id = p.video_id
            GROUP BY v.video_id
            ORDER BY v.view_count DESC
            LIMIT 30
        """)
        videos = [dict(row) for row in cursor.fetchall()]

        if not videos:
            st.info("수집된 영상이 없습니다. 파이프라인을 실행하세요.")
            st.code("python crawler/pipeline.py")
        else:
            for video in videos:
                with st.container():
                    col1, col2 = st.columns([1, 3])

                    with col1:
                        if video.get("thumbnail_url"):
                            st.image(video["thumbnail_url"], use_container_width=True)

                    with col2:
                        st.markdown(f"**{video['title']}**")
                        st.write(f"📺 {video['channel_title']} | 👁️ {video.get('view_count', 0):,}회")
                        st.write(f"📅 {video.get('published_at', '')[:10]} | 상태: {video.get('status', 'pending')}")
                        st.write(f"🛍️ 추출된 상품: {video.get('product_count', 0)}개")

                        video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
                        st.link_button("🎬 영상 보기", video_url)

                    st.divider()

    # 탭 4: 상세 통계
    with tab4:
        st.subheader("📊 상세 통계 대시보드")

        detailed_stats = get_detailed_stats()

        # 주요 지표
        st.markdown("### 📈 주요 지표")
        metric_cols = st.columns(5)
        metric_cols[0].metric("총 영상", f"{detailed_stats['total_videos']:,}")
        metric_cols[1].metric("총 상품", f"{detailed_stats['total_products']:,}")
        metric_cols[2].metric("승인됨", f"{detailed_stats['approved_products']:,}")
        metric_cols[3].metric("품번 매칭", f"{detailed_stats['matched_products']:,}")
        metric_cols[4].metric("숨김 처리", f"{detailed_stats['hidden_products']:,}")

        st.markdown("---")

        # 차트 섹션
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("### 📁 카테고리별 분포")
            if detailed_stats["by_category"]:
                cat_df = pd.DataFrame(
                    list(detailed_stats["by_category"].items()),
                    columns=["카테고리", "상품수"]
                )
                st.bar_chart(cat_df.set_index("카테고리"))
            else:
                st.info("데이터가 없습니다.")

        with chart_col2:
            st.markdown("### 💰 가격대별 분포")
            if detailed_stats["by_price_range"]:
                price_df = pd.DataFrame(
                    list(detailed_stats["by_price_range"].items()),
                    columns=["가격대", "상품수"]
                )
                st.bar_chart(price_df.set_index("가격대"))
            else:
                st.info("데이터가 없습니다.")

        st.markdown("---")

        # 채널 및 일별 통계
        channel_col, daily_col = st.columns(2)

        with channel_col:
            st.markdown("### 🎬 인기 채널 TOP 10")
            if detailed_stats["by_channel"]:
                for channel, count in detailed_stats["by_channel"].items():
                    st.write(f"• {channel}: {count}개 상품")
            else:
                st.info("데이터가 없습니다.")

        with daily_col:
            st.markdown("### 📅 일별 수집 현황 (최근 7일)")
            if detailed_stats["daily_products"]:
                daily_df = pd.DataFrame(
                    list(detailed_stats["daily_products"].items()),
                    columns=["날짜", "수집수"]
                )
                st.line_chart(daily_df.set_index("날짜"))
            else:
                st.info("데이터가 없습니다.")

    # 탭 5: 관리 도구
    with tab5:
        st.subheader("⚙️ 관리 도구")

        # 데이터 내보내기
        st.markdown("### 📤 데이터 내보내기")
        export_col1, export_col2, export_col3 = st.columns(3)

        with export_col1:
            json_data = export_products_to_json()
            st.download_button(
                label="📄 JSON 다운로드",
                data=json_data,
                file_name=f"products_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
            st.caption(f"승인된 상품 {detailed_stats['approved_products']}개")

        with export_col2:
            csv_data = export_products_to_csv()
            st.download_button(
                label="📊 CSV 다운로드",
                data=csv_data,
                file_name=f"products_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            st.caption("엑셀 호환 형식")

        with export_col3:
            if st.button("🔄 S3 업로드"):
                st.info("S3 업로드 기능은 별도 스크립트로 실행하세요.")
                st.code("python crawler/upload_to_s3.py")

        st.markdown("---")

        # 벌크 작업
        st.markdown("### 🔧 벌크 작업")

        bulk_work_col1, bulk_work_col2 = st.columns(2)

        with bulk_work_col1:
            st.markdown("#### 품번 매칭된 상품 일괄 승인")
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM products
                WHERE is_approved = 0 AND is_hidden = 0
                AND official_code IS NOT NULL AND official_code != ''
            """)
            matched_pending = cursor.fetchone()[0]
            st.write(f"대기 중인 품번 매칭 상품: {matched_pending}개")

            if st.button("✅ 품번 매칭 상품 일괄 승인", disabled=matched_pending == 0):
                cursor.execute("""
                    UPDATE products SET is_approved = 1
                    WHERE is_approved = 0 AND is_hidden = 0
                    AND official_code IS NOT NULL AND official_code != ''
                """)
                db.conn.commit()
                st.success(f"{matched_pending}개 상품 승인 완료!")
                st.rerun()

        with bulk_work_col2:
            st.markdown("#### 미매칭 상품 일괄 숨김")
            cursor.execute("""
                SELECT COUNT(*) FROM products
                WHERE is_approved = 0 AND is_hidden = 0
                AND (official_code IS NULL OR official_code = '')
            """)
            unmatched_pending = cursor.fetchone()[0]
            st.write(f"대기 중인 미매칭 상품: {unmatched_pending}개")

            if st.button("❌ 미매칭 상품 일괄 숨김", disabled=unmatched_pending == 0):
                cursor.execute("""
                    UPDATE products SET is_hidden = 1
                    WHERE is_approved = 0 AND is_hidden = 0
                    AND (official_code IS NULL OR official_code = '')
                """)
                db.conn.commit()
                st.warning(f"{unmatched_pending}개 상품 숨김 처리!")
                st.rerun()

        st.markdown("---")

        # 데이터 정리
        st.markdown("### 🗑️ 데이터 정리")
        cleanup_col1, cleanup_col2 = st.columns(2)

        with cleanup_col1:
            st.markdown("#### 중복 상품 정리")
            cursor.execute("""
                SELECT name, COUNT(*) as cnt
                FROM products
                WHERE is_approved = 1
                GROUP BY name, store_key
                HAVING cnt > 1
            """)
            duplicates = cursor.fetchall()
            st.write(f"중복 상품 그룹: {len(duplicates)}개")

            if duplicates and st.button("🔄 중복 제거 (최신 유지)"):
                # 각 중복 그룹에서 가장 최신 것만 남기고 나머지 숨김
                for name, _ in duplicates:
                    cursor.execute("""
                        UPDATE products SET is_hidden = 1
                        WHERE name = ? AND is_approved = 1
                        AND id NOT IN (
                            SELECT id FROM products
                            WHERE name = ? AND is_approved = 1
                            ORDER BY created_at DESC
                            LIMIT 1
                        )
                    """, (name, name))
                db.conn.commit()
                st.success("중복 상품 정리 완료!")
                st.rerun()

        with cleanup_col2:
            st.markdown("#### 오래된 숨김 상품 삭제")
            cursor.execute("""
                SELECT COUNT(*) FROM products
                WHERE is_hidden = 1
                AND created_at < date('now', '-30 days')
            """)
            old_hidden = cursor.fetchone()[0]
            st.write(f"30일 이상 숨김 상품: {old_hidden}개")

            if old_hidden > 0 and st.button("🗑️ 오래된 숨김 상품 삭제"):
                cursor.execute("""
                    DELETE FROM products
                    WHERE is_hidden = 1
                    AND created_at < date('now', '-30 days')
                """)
                db.conn.commit()
                st.success(f"{old_hidden}개 상품 삭제 완료!")
                st.rerun()

        st.markdown("---")

        # 시스템 정보
        st.markdown("### 💻 시스템 정보")
        db_path = crawler_path / "data" / "shopping_helper.db"
        if db_path.exists():
            db_size = db_path.stat().st_size / (1024 * 1024)  # MB
            st.write(f"데이터베이스 크기: {db_size:.2f} MB")
            st.write(f"데이터베이스 경로: {db_path}")


if __name__ == "__main__":
    main()
