const fs = require('fs');
const path = require('path');
const PW = require(process.env.QMDM_PLAYWRIGHT || 'playwright');

const root = path.resolve(__dirname);
const frames = path.resolve(__dirname, '../../.work/qmdm-video/frames');
const fps = 24;
const totalFrames = 20 * fps;
const endFrame = Math.min(totalFrames, Number(process.env.QMDM_END || totalFrames));
if (!Number.isInteger(endFrame) || endFrame < 1) throw new Error('QMDM_END must be a positive integer');
fs.mkdirSync(frames, { recursive: true });

(async () => {
  const browser = await PW.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto(`file://${root.replaceAll('\\', '/')}/index.html?render=1`, { waitUntil: 'load' });
  await page.waitForFunction(() => Boolean(window.QMDMVideo));
  for (let frame = 0; frame < endFrame; frame += 1) {
    const filename = path.join(frames, `frame-${String(frame).padStart(4, '0')}.png`);
    // shortcut: resume trusts unchanged sources; rebuild all frames after editing the story.
    if (process.env.QMDM_RESUME === '1' && fs.existsSync(filename)) continue;
    await page.evaluate(time => window.QMDMVideo.setTime(time), frame / fps);
    await page.screenshot({ path: filename, type: 'png' });
  }
  await browser.close();
  console.log(JSON.stringify({ frames, fps, totalFrames }));
})();
