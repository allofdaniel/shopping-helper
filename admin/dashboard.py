"""
꿀템장바구니 - 관리자 대시보드
Streamlit 기반 상품 검수 및 승인 인터페이스
"""
import sys
import os
from pathlib import Path

# 크롤러 모듈 경로 추가 (절대 경로 사용)
crawler_path = Path(__file__).resolve().parent.parent / "crawler"
sys.path.insert(0, str(crawler_path))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(crawler_path / ".env")

import streamlit as st
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
    tab1, tab2, tab3 = st.tabs(["📝 승인 대기", "✅ 승인된 상품", "🎬 수집된 영상"])

    # 탭 1: 승인 대기 상품
    with tab1:
        st.subheader("승인 대기 상품")
        pending = db.get_pending_products(limit=50)

        if not pending:
            st.info("승인 대기 중인 상품이 없습니다.")
        else:
            for product in pending:
                with st.container():
                    col1, col2, col3 = st.columns([1, 3, 1])

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
                        st.write(f"💰 {product.get('price', '?')}원 | 📁 {product.get('category', '기타')}")
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


if __name__ == "__main__":
    main()
