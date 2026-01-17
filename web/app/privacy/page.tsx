export const metadata = {
  title: '개인정보처리방침 | 꿀템장바구니',
  description: '꿀템장바구니 앱의 개인정보처리방침입니다.',
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">개인정보처리방침</h1>
        
        <p className="text-gray-600 mb-4">
          최종 수정일: 2026년 1월 17일
        </p>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">1. 수집하는 정보</h2>
          <p className="text-gray-700 leading-relaxed">
            꿀템장바구니(이하 &quot;앱&quot;)는 사용자의 개인정보를 수집하지 않습니다. 
            앱은 오프라인에서도 작동하는 PWA(Progressive Web App)로, 모든 데이터는 
            사용자의 기기에 로컬로 저장됩니다.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">2. 로컬 저장 데이터</h2>
          <p className="text-gray-700 leading-relaxed mb-2">
            앱은 다음 정보를 사용자의 기기에 로컬로 저장합니다:
          </p>
          <ul className="list-disc list-inside text-gray-700 space-y-1 ml-4">
            <li>최근 검색어 기록</li>
            <li>앱 설정 (다크모드 등)</li>
            <li>장바구니 데이터</li>
          </ul>
          <p className="text-gray-700 leading-relaxed mt-2">
            이 데이터는 외부 서버로 전송되지 않으며, 사용자가 브라우저 데이터를 
            삭제하면 함께 삭제됩니다.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">3. 외부 서비스</h2>
          <p className="text-gray-700 leading-relaxed">
            앱은 상품 정보를 검색하기 위해 외부 쇼핑 API를 사용합니다. 
            검색 요청 시 입력한 검색어만 해당 서비스로 전송되며, 
            개인 식별 정보는 전송되지 않습니다.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">4. 쿠키 및 추적</h2>
          <p className="text-gray-700 leading-relaxed">
            앱은 광고 목적의 쿠키나 사용자 추적 도구를 사용하지 않습니다.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">5. 어린이 개인정보</h2>
          <p className="text-gray-700 leading-relaxed">
            앱은 만 13세 미만 어린이를 대상으로 하지 않으며, 
            의도적으로 어린이의 개인정보를 수집하지 않습니다.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">6. 정책 변경</h2>
          <p className="text-gray-700 leading-relaxed">
            본 개인정보처리방침은 변경될 수 있으며, 변경 시 앱 내 또는 
            이 페이지를 통해 공지합니다.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">7. 문의</h2>
          <p className="text-gray-700 leading-relaxed">
            개인정보처리방침에 관한 문의사항이 있으시면 아래 이메일로 연락해 주세요.
          </p>
          <p className="text-gray-700 mt-2">
            이메일: caesarkorean@gmail.com
          </p>
        </section>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <a 
            href="/" 
            className="text-orange-500 hover:text-orange-600 font-medium"
          >
            ← 앱으로 돌아가기
          </a>
        </div>
      </div>
    </main>
  );
}
