/**
 * SVG를 PNG로 변환하는 스크립트
 * 실행: node scripts/convert-icons.js
 */

const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const publicDir = path.join(__dirname, '..', 'public');
const svgPath = path.join(publicDir, 'icon.svg');
const ogSvgPath = path.join(publicDir, 'og-image.svg');

const sizes = [72, 96, 128, 144, 152, 192, 384, 512];

async function generateIcons() {
  console.log('PWA 아이콘 생성 중...\n');

  // SVG 파일 읽기
  const svgBuffer = fs.readFileSync(svgPath);

  // 각 사이즈별 PNG 생성
  for (const size of sizes) {
    const outputPath = path.join(publicDir, `icon-${size}.png`);

    await sharp(svgBuffer)
      .resize(size, size)
      .png()
      .toFile(outputPath);

    console.log(`✅ Created: icon-${size}.png`);
  }

  // OG 이미지 생성 (1200x630)
  if (fs.existsSync(ogSvgPath)) {
    const ogSvgBuffer = fs.readFileSync(ogSvgPath);
    const ogOutputPath = path.join(publicDir, 'og-image.png');

    await sharp(ogSvgBuffer)
      .resize(1200, 630)
      .png()
      .toFile(ogOutputPath);

    console.log('✅ Created: og-image.png');
  }

  console.log('\n🎉 모든 아이콘 생성 완료!');
}

generateIcons().catch(console.error);
