// Make site/og.png (1280x640) and docs/viewer.png (1600 wide). Run: npm run shots
import { chromium } from 'playwright';
import { serve } from '../tests/serve.mjs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const server = await serve();
const browser = await chromium.launch();
try {
  async function shot(w, h, hue, file, scale) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: scale, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    await page.addInitScript((v) => localStorage.setItem('hue', v), hue);
    await page.goto(server.url + '/?g=acid-techno');
    await page.waitForFunction(() => window.__tree && window.__tree.ready);
    await page.click('#lvl');
    await page.fill('#q', 'acid techno');
    await page.locator('#hits button').first().click();
    await page.waitForTimeout(400);
    await page.mouse.click(5, h - 5); // close the search list
    await page.screenshot({ path: path.join(root, file), type: 'png' });
    await ctx.close();
  }
  await shot(1280, 640, 'slate', 'site/og.png', 1);
  await shot(1600, 900, 'chalk', 'docs/viewer.png', 1);
} finally {
  await browser.close();
  server.stop();
}
