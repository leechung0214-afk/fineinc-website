// Run from the repository root with Node.js and sharp installed.
// Only the background is AI-generated. The official logo is composited verbatim,
// with proportional resizing, no recoloring, tracing, or generative editing.
const sharp = require('sharp');
const path = require('node:path');
process.chdir(path.join(__dirname, '..'));
(async () => {
  const logo = await sharp('assets/fine-logo-white.png').resize({ width: 560 }).toBuffer();
  const typography = Buffer.from(`<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
    <g text-anchor="middle" font-family="DejaVu Sans, sans-serif">
      <text x="600" y="190" font-size="16" letter-spacing="5" fill="#3de0e8">BEYOND THE EVENT.</text>
      <text x="600" y="388" font-size="24" letter-spacing="2" fill="#ffffff">EVENT PRODUCTION COMPANY</text>
      <path d="M570 427H630" stroke="#00b8c8" stroke-width="3"/>
    </g>
  </svg>`);
  await sharp('design/social-background.png').resize(1200, 630, { fit: 'cover' })
    .composite([{ input: logo, left: 320, top: 228 }, { input: typography }])
    .flatten({ background: '#10243a' }).toColourspace('srgb')
    .png({ compressionLevel: 9 }).toFile('assets/fine-social-20261105.png');
})();
