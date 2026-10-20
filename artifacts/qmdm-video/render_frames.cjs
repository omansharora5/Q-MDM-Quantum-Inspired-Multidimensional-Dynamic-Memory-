const fs = require('fs');
const path = require('path');
const PW = require('C:/Users/dell/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright');

const root = path.resolve(__dirname);
const frames = path.resolve(__dirname, '../../.work/qmdm-video/frames');
const fps = 24;
const totalFrames = 20 * fps;
fs.mkdirSync(frames, { recursive: true });

(async () => {
  const browser = await PW.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto(`file://${root.replaceAll('\\', '/')}/index.html?render=1`, { waitUntil: 'load' });
  await page.waitForFunction(() => Boolean(window.QMDMVideo));
  for (let frame = 0; frame < totalFrames; frame += 1) {
    await page.evaluate(time => window.QMDMVideo.setTime(time), frame / fps);
    const filename = path.join(frames, `frame-${String(frame).padStart(4, '0')}.png`);
    await page.screenshot({ path: filename, type: 'png' });
  }
  await browser.close();
  console.log(JSON.stringify({ frames, fps, totalFrames }));
})();
