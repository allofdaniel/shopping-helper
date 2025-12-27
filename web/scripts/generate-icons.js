/**
 * PWA 아이콘 생성 스크립트
 *
 * 실행 방법:
 * 1. npm install sharp (필요시)
 * 2. node scripts/generate-icons.js
 */

const fs = require('fs');
const path = require('path');

// SVG 아이콘 (장바구니 + 하트)
const svgIcon = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#f97316"/>
      <stop offset="100%" style="stop-color:#ea580c"/>
    </linearGradient>
  </defs>

  <!-- 배경 -->
  <rect width="512" height="512" rx="96" fill="url(#bg)"/>

  <!-- 장바구니 -->
  <g fill="none" stroke="white" stroke-width="24" stroke-linecap="round" stroke-linejoin="round">
    <!-- 카트 바디 -->
    <path d="M128 160 L168 160 L200 320 L400 320 L440 192 L184 192"/>

    <!-- 카트 바퀴 -->
    <circle cx="224" cy="384" r="28" fill="white"/>
    <circle cx="376" cy="384" r="28" fill="white"/>
  </g>

  <!-- 하트 (꿀템 표시) -->
  <path fill="#fef08a" d="M340 130
    Q340 100, 370 100
    Q400 100, 400 130
    Q400 160, 370 190
    Q340 160, 340 130
    M400 130
    Q400 100, 430 100
    Q460 100, 460 130
    Q460 160, 400 210
    Q340 160, 340 130"/>
</svg>
`;

// 더 간단한 SVG 아이콘 (원 + 쇼핑카트)
const simpleSvgIcon = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#fb923c"/>
      <stop offset="100%" style="stop-color:#ea580c"/>
    </linearGradient>
  </defs>

  <!-- 둥근 배경 -->
  <rect width="512" height="512" rx="108" fill="url(#bgGrad)"/>

  <!-- 간단한 쇼핑 아이콘 -->
  <text x="256" y="320"
        font-family="Arial, sans-serif"
        font-size="280"
        text-anchor="middle"
        fill="white">🛒</text>
</svg>
`;

// 이모지 기반 간단한 버전
const emojiSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="108" fill="#f97316"/>
  <text x="256" y="370" font-family="Apple Color Emoji, Segoe UI Emoji, sans-serif"
        font-size="300" text-anchor="middle" fill="white">🛒</text>
</svg>
`;

const publicDir = path.join(__dirname, '..', 'public');

// public 폴더 생성
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

// SVG 파일 저장
fs.writeFileSync(path.join(publicDir, 'icon.svg'), svgIcon.trim());
console.log('Created: icon.svg');

// 아이콘 사이즈
const sizes = [72, 96, 128, 144, 152, 192, 384, 512];

console.log(`
PWA 아이콘 생성 완료!

다음 단계:
1. icon.svg 파일을 온라인 도구로 PNG 변환하거나
2. sharp 패키지를 설치해서 변환하세요:
   npm install sharp

또는 https://realfavicongenerator.net 같은 사이트에서
icon.svg를 업로드하면 모든 사이즈의 아이콘을 생성해줍니다.

필요한 아이콘 사이즈: ${sizes.join(', ')}px
`);

// OG 이미지 생성용 SVG
const ogImageSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="ogBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#fff7ed"/>
      <stop offset="100%" style="stop-color:#ffedd5"/>
    </linearGradient>
  </defs>

  <!-- 배경 -->
  <rect width="1200" height="630" fill="url(#ogBg)"/>

  <!-- 장식 원들 -->
  <circle cx="100" cy="530" r="200" fill="#fed7aa" opacity="0.5"/>
  <circle cx="1100" cy="100" r="150" fill="#fdba74" opacity="0.4"/>

  <!-- 아이콘 -->
  <rect x="80" y="200" width="200" height="200" rx="40" fill="#f97316"/>
  <text x="180" y="340" font-size="120" text-anchor="middle">🛒</text>

  <!-- 텍스트 -->
  <text x="320" y="280" font-family="Arial, sans-serif" font-size="72" font-weight="bold" fill="#1f2937">
    꿀템장바구니
  </text>
  <text x="320" y="360" font-family="Arial, sans-serif" font-size="36" fill="#6b7280">
    유튜버 추천 오프라인 매장 꿀템 모음
  </text>

  <!-- 매장 태그들 -->
  <rect x="320" y="400" width="100" height="40" rx="20" fill="#ef4444"/>
  <text x="370" y="428" font-family="Arial, sans-serif" font-size="18" fill="white" text-anchor="middle">다이소</text>

  <rect x="440" y="400" width="110" height="40" rx="20" fill="#3b82f6"/>
  <text x="495" y="428" font-family="Arial, sans-serif" font-size="18" fill="white" text-anchor="middle">코스트코</text>

  <rect x="570" y="400" width="90" height="40" rx="20" fill="#eab308"/>
  <text x="615" y="428" font-family="Arial, sans-serif" font-size="18" fill="white" text-anchor="middle">이케아</text>

  <rect x="680" y="400" width="110" height="40" rx="20" fill="#22c55e"/>
  <text x="735" y="428" font-family="Arial, sans-serif" font-size="18" fill="white" text-anchor="middle">올리브영</text>
</svg>
`;

fs.writeFileSync(path.join(publicDir, 'og-image.svg'), ogImageSvg.trim());
console.log('Created: og-image.svg');
