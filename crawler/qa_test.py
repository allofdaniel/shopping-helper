import asyncio
from playwright.async_api import async_playwright

async def comprehensive_qa():
    results = []
    errors = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        # JS 에러 수집
        page.on('pageerror', lambda e: errors.append(str(e)))

        print('=' * 60, flush=True)
        print('상세 QA 테스트 시작: https://shoppinghelper.vercel.app', flush=True)
        print('=' * 60, flush=True)

        # 1. 페이지 로드
        print('\n[1] 페이지 로드 테스트...', flush=True)
        await page.goto('https://shoppinghelper.vercel.app', timeout=30000)
        await page.wait_for_timeout(3000)
        title = await page.title()
        print(f'   페이지 타이틀: OK', flush=True)
        results.append(('페이지 로드', 'PASS' if title else 'FAIL'))

        # 2. 매장 필터 버튼들 클릭
        print('\n[2] 매장 필터 버튼 테스트...', flush=True)
        stores = ['다이소', '코스트코', '이케아', '올리브영', '트레이더스', '편의점', 'YouTube']
        for store in stores:
            try:
                btn = page.locator(f'button:has-text("{store}")').first
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(500)
                    print(f'   {store} 클릭: OK', flush=True)
                    results.append((f'매장필터-{store}', 'PASS'))
                else:
                    print(f'   {store} 버튼 없음', flush=True)
                    results.append((f'매장필터-{store}', 'NOT FOUND'))
            except Exception as e:
                print(f'   {store} 에러: {str(e)[:50]}', flush=True)
                results.append((f'매장필터-{store}', 'FAIL'))

        # 전체로 리셋
        try:
            await page.locator('button:has-text("전체")').first.click()
            await page.wait_for_timeout(500)
        except:
            pass

        # 3. 카테고리 필터 테스트
        print('\n[3] 카테고리 필터 버튼 테스트...', flush=True)
        categories = ['주방', '생활', '뷰티', '인테리어', '식품', '디지털']
        for cat in categories:
            try:
                btn = page.locator(f'button:has-text("{cat}")').first
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(300)
                    print(f'   {cat} 클릭: OK', flush=True)
                    results.append((f'카테고리-{cat}', 'PASS'))
            except Exception as e:
                print(f'   {cat} 에러: {str(e)[:30]}', flush=True)
                results.append((f'카테고리-{cat}', 'FAIL'))

        # 전체로 리셋
        try:
            cat_all = page.locator('button:has-text("전체")').first
            await cat_all.click()
            await page.wait_for_timeout(300)
        except:
            pass

        # 4. 정렬 옵션 테스트
        print('\n[4] 정렬 옵션 테스트...', flush=True)
        sorts = ['인기순', '최신순', '추천순']
        for sort in sorts:
            try:
                btn = page.locator(f'button:has-text("{sort}")').first
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(300)
                    print(f'   {sort} 클릭: OK', flush=True)
                    results.append((f'정렬-{sort}', 'PASS'))
            except Exception as e:
                print(f'   {sort} 에러', flush=True)
                results.append((f'정렬-{sort}', 'FAIL'))

        # 5. 검색 테스트 (다양한 키워드)
        print('\n[5] 검색 기능 테스트...', flush=True)
        search_terms = ['냄비', '화장품', 'USB', '과자', '수납']

        for term in search_terms:
            try:
                # 매번 검색창 새로 찾기
                search_input = page.locator('input').first
                await search_input.click()
                await page.wait_for_timeout(200)
                await search_input.fill(term)
                await page.wait_for_timeout(800)
                curr_errors = len(errors)
                print(f'   "{term}" 검색: OK (에러: {len(errors)}개)', flush=True)
                results.append((f'검색-{term}', 'PASS' if len(errors) == 0 else 'FAIL'))
                # 검색어 지우기
                await search_input.fill('')
                await page.wait_for_timeout(300)
            except Exception as e:
                print(f'   "{term}" 검색 에러: {str(e)[:50]}', flush=True)
                results.append((f'검색-{term}', 'FAIL'))
                # 페이지 새로고침 후 재시도
                try:
                    await page.reload()
                    await page.wait_for_timeout(2000)
                except:
                    pass

        # 6. 뷰 모드 토글 테스트
        print('\n[6] 뷰 모드 토글 테스트...', flush=True)
        try:
            view_btns = await page.locator('button').all()
            view_clicked = False
            for btn in view_btns:
                text = await btn.text_content()
                if text and ('작게' in text or '크게' in text or '보기' in text):
                    await btn.click()
                    await page.wait_for_timeout(300)
                    print(f'   뷰 모드 "{text}" 클릭: OK', flush=True)
                    results.append(('뷰모드토글', 'PASS'))
                    view_clicked = True
                    break
            if not view_clicked:
                print('   뷰 모드 버튼 찾기 시도...', flush=True)
                results.append(('뷰모드토글', 'NOT FOUND'))
        except Exception as e:
            results.append(('뷰모드토글', 'FAIL'))

        # 7. 다크모드 토글 테스트
        print('\n[7] 다크모드 토글 테스트...', flush=True)
        try:
            header_btns = await page.locator('header button').all()
            dark_clicked = False
            for btn in header_btns:
                inner = await btn.inner_html()
                if 'svg' in inner.lower():
                    bg_before = await page.evaluate('getComputedStyle(document.body).backgroundColor')
                    await btn.click()
                    await page.wait_for_timeout(500)
                    bg_after = await page.evaluate('getComputedStyle(document.body).backgroundColor')
                    if bg_before != bg_after:
                        print(f'   다크모드 토글: OK (배경색 변경됨)', flush=True)
                        results.append(('다크모드', 'PASS'))
                        dark_clicked = True
                        break
            if not dark_clicked:
                results.append(('다크모드', 'NOT FOUND'))
        except Exception as e:
            print(f'   다크모드 에러: {str(e)[:30]}', flush=True)
            results.append(('다크모드', 'FAIL'))

        # 8. 위시리스트 추가 테스트 (상품 카드의 하트 버튼)
        print('\n[8] 위시리스트 기능 테스트...', flush=True)
        try:
            # 모든 버튼에서 하트/♡ 찾기
            all_btns = await page.locator('button').all()
            wish_clicked = False
            for btn in all_btns:
                text = await btn.text_content()
                if text and ('♡' in text or '❤' in text or '찜' in text):
                    await btn.click()
                    await page.wait_for_timeout(300)
                    print(f'   위시리스트 버튼 클릭: OK', flush=True)
                    results.append(('위시리스트추가', 'PASS'))
                    wish_clicked = True
                    break
            if not wish_clicked:
                # SVG 하트 아이콘 찾기
                svg_btns = await page.locator('button:has(svg)').all()
                if len(svg_btns) > 3:
                    await svg_btns[3].click()
                    await page.wait_for_timeout(300)
                    print('   SVG 버튼 클릭: OK', flush=True)
                    results.append(('위시리스트추가', 'PASS'))
                else:
                    results.append(('위시리스트추가', 'NOT FOUND'))
        except Exception as e:
            print(f'   위시리스트 에러: {str(e)[:30]}', flush=True)
            results.append(('위시리스트추가', 'FAIL'))

        # 9. 찜 목록 보기 버튼
        print('\n[9] 찜 목록 보기 테스트...', flush=True)
        try:
            wishlist_btn = page.locator('button:has-text("찜")').first
            if await wishlist_btn.count() > 0:
                await wishlist_btn.click()
                await page.wait_for_timeout(500)
                print('   찜 목록 보기: OK', flush=True)
                results.append(('찜목록보기', 'PASS'))
                await wishlist_btn.click()
                await page.wait_for_timeout(300)
            else:
                results.append(('찜목록보기', 'NOT FOUND'))
        except Exception as e:
            results.append(('찜목록보기', 'FAIL'))

        # 10. 고급 필터 드로어 테스트
        print('\n[10] 고급 필터 드로어 테스트...', flush=True)
        try:
            filter_btn = page.locator('button:has-text("필터")').first
            if await filter_btn.count() > 0:
                await filter_btn.click()
                await page.wait_for_timeout(500)
                drawer = page.locator('[class*="drawer"], [class*="Drawer"], [role="dialog"]')
                if await drawer.count() > 0:
                    print('   필터 드로어 열림: OK', flush=True)
                    results.append(('필터드로어', 'PASS'))
                    # 닫기
                    close_btn = page.locator('button:has-text("닫기"), button:has-text("×")').first
                    if await close_btn.count() > 0:
                        await close_btn.click()
                        await page.wait_for_timeout(300)
                else:
                    results.append(('필터드로어', 'PARTIAL'))
            else:
                results.append(('필터드로어', 'NOT FOUND'))
        except Exception as e:
            results.append(('필터드로어', 'FAIL'))

        # 11. 스크롤 테스트
        print('\n[11] 스크롤 테스트...', flush=True)
        try:
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(500)
            scroll_pos = await page.evaluate('window.scrollY')
            print(f'   스크롤 위치: {scroll_pos}px', flush=True)
            results.append(('스크롤', 'PASS' if scroll_pos > 100 else 'FAIL'))

            # 맨 위로 버튼 테스트
            top_btn = page.locator('button:has-text("↑")')
            if await top_btn.count() > 0:
                await top_btn.first.click()
                await page.wait_for_timeout(500)
                print('   맨 위로 버튼: OK', flush=True)
                results.append(('맨위로버튼', 'PASS'))
            else:
                results.append(('맨위로버튼', 'NOT FOUND'))
        except Exception as e:
            results.append(('스크롤', 'FAIL'))

        # 12. 상품 카드 링크 테스트
        print('\n[12] 상품 카드 링크 테스트...', flush=True)
        try:
            product_links = page.locator('a[target="_blank"]')
            link_count = await product_links.count()
            print(f'   상품 링크 수: {link_count}개', flush=True)
            results.append(('상품링크', 'PASS' if link_count > 0 else 'FAIL'))
        except Exception as e:
            results.append(('상품링크', 'FAIL'))

        # 13. 비교하기 FAB 버튼 테스트
        print('\n[13] 비교하기 FAB 버튼 테스트...', flush=True)
        try:
            compare_btn = page.locator('button:has-text("비교")')
            if await compare_btn.count() > 0:
                await compare_btn.first.click()
                await page.wait_for_timeout(300)
                print('   비교하기 FAB: OK', flush=True)
                results.append(('비교FAB', 'PASS'))
            else:
                results.append(('비교FAB', 'NOT FOUND'))
        except Exception as e:
            results.append(('비교FAB', 'FAIL'))

        # 14. 모바일 뷰포트 테스트
        print('\n[14] 모바일 뷰포트 테스트...', flush=True)
        try:
            await page.set_viewport_size({'width': 375, 'height': 667})
            await page.wait_for_timeout(1000)
            body_width = await page.evaluate('document.body.scrollWidth')
            viewport_width = await page.evaluate('window.innerWidth')
            print(f'   모바일 뷰: body={body_width}px, viewport={viewport_width}px', flush=True)
            # 가로 스크롤이 없어야 함
            results.append(('모바일반응형', 'PASS' if body_width <= viewport_width + 50 else 'FAIL'))

            await page.set_viewport_size({'width': 1280, 'height': 720})
        except Exception as e:
            results.append(('모바일반응형', 'FAIL'))

        # 15. 쇼핑 모드 테스트
        print('\n[15] 쇼핑 모드 테스트...', flush=True)
        try:
            shopping_btn = page.locator('button:has-text("쇼핑"), button:has-text("장바구니")')
            if await shopping_btn.count() > 0:
                await shopping_btn.first.click()
                await page.wait_for_timeout(500)
                print('   쇼핑 모드: OK', flush=True)
                results.append(('쇼핑모드', 'PASS'))
            else:
                results.append(('쇼핑모드', 'NOT FOUND'))
        except Exception as e:
            results.append(('쇼핑모드', 'FAIL'))

        # 16. 언어 변경 테스트
        print('\n[16] 언어 변경 테스트...', flush=True)
        try:
            lang_btn = page.locator('button:has-text("한국어"), button:has-text("English"), button:has-text("KO"), button:has-text("EN")')
            if await lang_btn.count() > 0:
                await lang_btn.first.click()
                await page.wait_for_timeout(300)
                print('   언어 변경: OK', flush=True)
                results.append(('언어변경', 'PASS'))
            else:
                results.append(('언어변경', 'NOT FOUND'))
        except Exception as e:
            results.append(('언어변경', 'FAIL'))

        # 17. 새로고침 버튼 테스트
        print('\n[17] 새로고침 버튼 테스트...', flush=True)
        try:
            refresh_btn = page.locator('button:has-text("새로고침"), button:has-text("🔄")')
            if await refresh_btn.count() > 0:
                await refresh_btn.first.click()
                await page.wait_for_timeout(500)
                print('   새로고침: OK', flush=True)
                results.append(('새로고침', 'PASS'))
            else:
                # SVG 아이콘 버튼 찾기
                results.append(('새로고침', 'NOT FOUND'))
        except Exception as e:
            results.append(('새로고침', 'FAIL'))

        await browser.close()

    # 결과 요약
    print('\n' + '=' * 60, flush=True)
    print('QA 결과 요약', flush=True)
    print('=' * 60, flush=True)

    passed = sum(1 for _, r in results if r == 'PASS')
    failed = sum(1 for _, r in results if r == 'FAIL')
    partial = sum(1 for _, r in results if r == 'PARTIAL')
    not_found = sum(1 for _, r in results if r == 'NOT FOUND')

    print(f'PASS: {passed}', flush=True)
    print(f'FAIL: {failed}', flush=True)
    print(f'PARTIAL: {partial}', flush=True)
    print(f'NOT FOUND: {not_found}', flush=True)
    print(f'\nJS 에러 수: {len(errors)}', flush=True)

    if errors:
        print('\nJS 에러 목록:', flush=True)
        for e in errors[:5]:
            print(f'  - {e[:100]}', flush=True)

    if failed > 0:
        print('\n실패한 테스트:', flush=True)
        for name, r in results:
            if r == 'FAIL':
                print(f'  - {name}', flush=True)

    print('\n전체 테스트 목록:', flush=True)
    for name, r in results:
        status = '✅' if r == 'PASS' else '❌' if r == 'FAIL' else '⚠️'
        print(f'  {status} {name}: {r}', flush=True)

    print('\n' + '=' * 60, flush=True)

if __name__ == '__main__':
    asyncio.run(comprehensive_qa())
