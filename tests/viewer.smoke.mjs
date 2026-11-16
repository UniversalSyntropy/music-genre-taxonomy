// Browser smoke test for the tree viewer. Runs in chromium and webkit.
// Usage: node tests/viewer.smoke.mjs   (needs _site: npm run build:site)
import { chromium, webkit } from 'playwright';
import { serve } from './serve.mjs';

const server = await serve();
const BASE = server.url;
let failures = 0;
const fail = (m) => { failures++; console.log('  FAIL ' + m); };
const ok = (c, m) => { if (!c) fail(m); else console.log('  ok   ' + m); };

const HUES = { chalk: 'rgb(244, 242, 236)', frost: 'rgb(232, 240, 247)', slate: 'rgb(25, 25, 26)', dusk: 'rgb(16, 22, 42)' };
const HOSTS = { Wikipedia: 'www.wikidata.org', Wikidata: 'www.wikidata.org', MusicBrainz: 'musicbrainz.org', Discogs: 'www.discogs.com', 'Beatport search': 'www.beatport.com' };

// A page that records console errors, page errors and non-local requests.
async function newPage(ctx, errs) {
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
  page.on('request', (r) => {
    const u = r.url();
    if (!u.startsWith(BASE + '/') && !u.startsWith('data:') && !u.startsWith('blob:') && u !== 'about:blank') errs.push('external request: ' + u);
  });
  return page;
}
const ready = (page) => page.waitForFunction(() => window.__tree && window.__tree.ready, null, { timeout: 20000 });
const cardName = (page) => page.locator('#card h2').innerText();

async function run(name, type) {
  console.log(`\n== ${name} ==`);
  const browser = await type.launch();
  const errs = [];
  try {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: 'light' });
    const page = await newPage(ctx, errs);
    await page.goto(BASE + '/');
    await ready(page);

    // tree renders
    await page.click('#lvl');
    const labels = await page.locator('#nodes g.node text').count();
    ok(labels > 100, `tree shows ${labels} node labels after "Open one more level"`);
    await page.click('#shut');
    ok((await page.locator('#nodes g.node').count()) < labels, '"Close all" shrinks the tree');

    // search, then CLICK a result
    for (const [typed, want] of [['K Pop', 'K-pop'], ['kpop', 'K-pop'], ['drum & bass', 'Drum n Bass'], ['Drum and Bass', 'Drum n Bass'], ['ye ye', 'Yé-Yé'], ['r&b', 'R&b']]) {
      await page.fill('#q', typed);
      ok((await page.locator('#hits button span').first().textContent()) === want, `search "${typed}" lists ${want} first`);
    }
    await page.fill('#q', 'techno');
    const hit = page.locator('#hits button').filter({ hasText: /^Techno/ }).first();
    await hit.waitFor();
    await hit.click();
    await page.locator('#card:not([hidden])').waitFor();
    ok((await cardName(page)) === 'Techno', 'clicking a search result shows the Techno card');
    const par = await page.locator('#card dl').innerText();
    ok(/Parents/.test(par) && /Electronic/.test(par), 'card lists its parents (Electronic)');
    ok(page.url().endsWith('?g=techno'), 'URL updated to ?g=techno');
    {
      const parts = await page.locator('#crumbs button, #crumbs b').allTextContents();
      ok(parts[0] === 'All genres' && parts.length >= 3 && parts[parts.length - 1] === 'Techno', `breadcrumb ends at Techno (${parts.join(' > ')})`);
      await page.locator('#crumbs button').nth(1).click();
      ok((await cardName(page)) === parts[1], `breadcrumb click selects ${parts[1]}`);
      await page.fill('#q', 'techno'); await page.locator('#hits button').first().click();
    }
    ok(await page.locator('#nodes g.node.sel').count() === 1, 'the selected node is drawn');
    ok(await page.locator('#card a.page').getAttribute('href') === 'genre/techno.html', 'card links to the genre page');

    // card links
    const links = await page.locator('#card .links a').evaluateAll((as) => as.map((a) => ({ t: a.textContent.replace(' ↗', ''), h: a.href, target: a.target, rel: a.rel })));
    ok(links.length >= 4, `card has ${links.length} external links`);
    for (const l of links) {
      const u = new URL(l.h);
      ok(l.target === '_blank' && /noopener/.test(l.rel) && u.protocol === 'https:' && u.host === HOSTS[l.t], `link ${l.t} -> ${u.host}`);
    }

    // keyboard: results reachable
    await page.fill('#q', 'ambient');
    await page.focus('#q');
    await page.keyboard.press('ArrowDown');
    ok(await page.evaluate(() => document.activeElement.closest('#hits') !== null), 'ArrowDown moves focus into the results');
    await page.keyboard.press('Enter');
    ok((await cardName(page)).toLowerCase().startsWith('ambient'), 'Enter on a result opens its card');

    { // tree start view: root at one third of the width; then the point cloud view
      const p2 = await ctx.newPage();
      await p2.goto(BASE + '/'); await p2.waitForFunction(() => window.__tree && window.__tree.ready); await p2.waitForTimeout(300);
      const rx = await p2.evaluate(() => { const r = document.querySelector('#nodes g.node[aria-label^="All genres"] circle').getBoundingClientRect(); return (r.left + r.right) / 2 / window.innerWidth; });
      ok(Math.abs(rx - 1 / 3) < 0.01, `tree root is at one third of the width (${rx.toFixed(3)})`);
      ok((await cardName(p2)) === 'Pop', 'default genre is Pop');
      await p2.selectOption('#mode', 'cloud'); await p2.waitForTimeout(900);
      const c = await p2.evaluate(() => { const b = document.querySelector('#cloud').getBoundingClientRect(), s = document.querySelector('#svg').getBoundingClientRect();
        return { n: document.querySelectorAll('#cloud circle.dot').length, dx: (b.left + b.right) / 2 - (s.left + s.right) / 2, dy: (b.top + b.bottom) / 2 - (s.top + s.bottom) / 2,
          treeHidden: getComputedStyle(document.querySelector('#nodes')).display === 'none', sel: document.querySelectorAll('#cloud circle.dot.sel').length }; });
      ok(c.n === 2450 && c.treeHidden, `point cloud shows 2,450 dots and hides the tree (${c.n})`);
      ok(Math.abs(c.dx) < 3 && Math.abs(c.dy) < 3, `point cloud centre is at the page centre (${c.dx.toFixed(1)}, ${c.dy.toFixed(1)})`);
      ok(c.sel === 1, 'point cloud marks the selected genre');
      const vis = () => p2.evaluate(() => Array.from(document.querySelectorAll('#cloud circle.dot.root')).filter((e) => getComputedStyle(e).display !== 'none').length);
      ok((await vis()) === 1, 'root genres are hidden at the start; the selected root (Pop) still shows');
      await p2.check('#roots'); await p2.waitForTimeout(500);
      { const v = await vis(); ok(v > 20 && v < 100, `the "Show root genres" box shows the root genres that have sub-genres (${v})`); }
      await p2.uncheck('#roots'); await p2.waitForTimeout(500);
      await p2.fill('#q', 'K Pop'); await p2.locator('#hits button').first().click(); await p2.waitForTimeout(800);
      ok((await cardName(p2)) === 'K-pop' && (await p2.locator('#cloud text.lab.sel').textContent()) === 'K-pop', 'search works in the point cloud');
      await p2.locator('#cloud circle.dot.tag:not(.root):not(.sel)').first().dispatchEvent('click');
      ok((await cardName(p2)) !== 'K-pop', 'a click on a dot opens its card');
      ok(p2.url().includes('view=cloud'), 'the address keeps view=cloud');
      await p2.goto(BASE + '/?g=techno&view=cloud'); await p2.waitForFunction(() => window.__tree && window.__tree.ready); await p2.waitForTimeout(700);
      ok((await p2.inputValue('#mode')) === 'cloud' && (await cardName(p2)) === 'Techno', '?g=techno&view=cloud opens the cloud on Techno');
      await p2.selectOption('#mode', 'tree');
      ok(await p2.evaluate(() => getComputedStyle(document.querySelector('#nodes')).display !== 'none' && getComputedStyle(document.querySelector('#cloud')).display === 'none'), 'tree view comes back');
      await p2.close();
    }
    { // follow selection and the zoom slider
      const p3 = await ctx.newPage();
      await p3.goto(BASE + '/'); await p3.waitForFunction(() => window.__tree && window.__tree.ready);
      const K = () => p3.evaluate(() => d3.zoomTransform(document.querySelector('#svg')).k);
      const X = () => p3.evaluate(() => { const t = d3.zoomTransform(document.querySelector('#svg')); return Math.round(t.x) + ',' + Math.round(t.y); });
      ok((await p3.isChecked('#follow')) && (await p3.isVisible('#zoomLvl')), 'Follow selection is on at the start and the zoom slider shows');
      await p3.fill('#q', 'techno'); await p3.locator('#hits button').first().click(); await p3.waitForTimeout(900);
      let k = await K(); ok(Math.abs(k - 1.29) < 0.05, `follow zooms to the slider default (${k.toFixed(2)}x)`);
      await p3.evaluate(() => { const e = document.getElementById('zoomLvl'); e.value = 100; e.dispatchEvent(new Event('input', { bubbles: true })); }); await p3.waitForTimeout(600);
      k = await K(); ok(Math.abs(k - 3) < 0.05, `slider at the top end gives 3x (${k.toFixed(2)}x)`);
      const before = await X();
      await p3.locator('#nodes g.node', { hasText: 'Moombahton' }).first().dispatchEvent('click'); await p3.waitForTimeout(600);
      ok((await cardName(p3)) === 'Moombahton' && (await X()) !== before, 'a click on a genre moves the view to it');
      await p3.uncheck('#follow');
      ok(!(await p3.isVisible('#zoomLvl')), 'Follow off hides the slider');
      const still = await X();
      await p3.locator('#nodes g.node', { hasText: 'Nortec' }).first().dispatchEvent('click'); await p3.waitForTimeout(600);
      ok((await cardName(p3)) === 'Nortec' && (await X()) === still, 'Follow off: a click selects but does not move the view');
      await p3.close();
    }
    // hues (start in dark so Auto = Slate and every pick differs from the last)
    await page.emulateMedia({ colorScheme: 'dark' });
    let last = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    for (const [h, bg] of Object.entries(HUES)) {
      await page.selectOption('#hue', h);
      const now = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      ok(now === bg && now !== last, `hue ${h}: background ${now}`);
      last = now;
    }
    await page.selectOption('#hue', '');
    await page.emulateMedia({ colorScheme: 'light' });
    ok((await page.evaluate(() => getComputedStyle(document.body).backgroundColor)) === HUES.chalk, 'Auto in light = Chalk');
    await page.emulateMedia({ colorScheme: 'dark' });
    ok((await page.evaluate(() => getComputedStyle(document.body).backgroundColor)) === HUES.slate, 'Auto in dark = Slate');
    await page.emulateMedia({ colorScheme: 'light' });
    await page.evaluate(() => localStorage.clear());

    // deep links
    await page.goto(BASE + '/?g=acid-house');
    await ready(page);
    await page.locator('#card:not([hidden])').waitFor();
    ok((await cardName(page)) === 'Acid House', 'deep link ?g=acid-house shows Acid House');
    await page.goto(BASE + '/?g=' + encodeURIComponent('yé-yé'));
    await ready(page);
    await page.locator('#card:not([hidden])').waitFor();
    ok((await page.locator('#card code').innerText()) === 'yé-yé', 'non-ASCII deep link yé-yé works');
    await page.goto(BASE + '/?g=no-such-genre');
    await ready(page);
    ok(await page.locator('#card').isHidden(), 'unknown ?g= leaves the card closed');

    // wheel zoom
    await page.goto(BASE + '/');
    await ready(page);
    const t0 = await page.locator('#view').getAttribute('transform');
    await page.mouse.move(640, 400);
    await page.mouse.wheel(0, -400);
    await page.waitForTimeout(300);
    const t1 = await page.locator('#view').getAttribute('transform');
    ok(t0 !== t1, 'wheel changes the zoom transform');
    await page.mouse.move(300, 500);
    await page.mouse.down();
    await page.mouse.move(380, 540, { steps: 5 });
    await page.mouse.up();
    ok((await page.locator('#view').getAttribute('transform')) !== t1, 'mouse drag pans the tree');

    // genre page
    const r = await page.goto(BASE + '/genre/techno.html');
    ok(r.status() === 200, 'genre page loads');
    const ld = await page.locator('script[type="application/ld+json"]').evaluateAll((s) => s.map((x) => JSON.parse(x.textContent)));
    ok(ld.some((j) => j['@type'] === 'DefinedTerm' && j.name === 'Techno') && ld.some((j) => j['@type'] === 'BreadcrumbList'), 'JSON-LD parses (DefinedTerm, BreadcrumbList)');
    ok((await page.locator('h1').innerText()) === 'Techno', 'genre page h1');
    await page.click('text=Open in the tree viewer');
    await ready(page);
    await page.locator('#card:not([hidden])').waitFor();
    ok(page.url().endsWith('/?g=techno') && (await cardName(page)) === 'Techno', '"Open in the tree viewer" opens Techno');
    const r2 = await page.goto(BASE + '/genre/' + encodeURIComponent('yé-yé') + '.html');
    ok(r2.status() === 200, 'non-ASCII genre page loads');
    const r3 = await page.goto(BASE + '/genre/');
    ok(r3.status() === 200 && (await page.locator('main li a').count()) > 2000, 'genre index lists all genres');

    // sitemap
    const sm = await (await fetch(BASE + '/sitemap.xml')).text();
    const n = (sm.match(/<loc>/g) || []).length;
    ok(n === 2452, `sitemap.xml holds ${n} URLs`);

    // data failure message (its own errors are expected)
    const bad = await ctx.newPage();
    await bad.route('**/data/taxonomy.json', (rt) => rt.abort());
    await bad.goto(BASE + '/');
    await bad.locator('#msg.on').waitFor();
    ok(/could not be loaded/.test(await bad.locator('#msg').innerText()), 'failed fetch shows a clear message');
    await bad.close();
    await ctx.close();

    // mobile
    const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
    const m = await newPage(mctx, errs);
    await m.goto(BASE + '/');
    await ready(m);
    const noOverflow = () => m.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth);
    ok(await noOverflow(), 'mobile: no horizontal overflow');
    for (const sel of ['#q', '#hue', '#fit', '#lvl', '#shut']) {
      const b = await m.locator(sel).boundingBox();
      ok(b && b.height >= 43.5 && b.x >= 0 && b.x + b.width <= 390.5, `mobile: ${sel} is ${Math.round(b.height)} px high and inside the screen`);
    }
    await m.fill('#q', 'techno');
    const mh = m.locator('#hits button').filter({ hasText: /^Techno/ }).first();
    await mh.waitFor();
    await mh.tap();
    await m.locator('#card:not([hidden])').waitFor();
    const cb = await m.locator('#card').boundingBox();
    ok(cb.x >= 0 && cb.x + cb.width <= 390.5 && cb.y + cb.height <= 844.5 && cb.y > 150, `mobile: card is a bottom sheet (${Math.round(cb.width)}x${Math.round(cb.height)})`);
    ok((await cardName(m)) === 'Techno', 'mobile: card shows Techno after a tap');
    const lb = await m.locator('#card .links a').evaluateAll((as) => as.map((a) => a.getBoundingClientRect().height));
    ok(lb.every((h) => h >= 43.5), 'mobile: card links are at least 44 px high');
    const xb = await m.locator('#card .x').boundingBox();
    ok(xb.height >= 43.5 && xb.width >= 43.5, 'mobile: close button is 44 px');
    ok(await noOverflow(), 'mobile: no horizontal overflow with the card open');
    await mctx.close();

    ok(errs.length === 0, `no console errors, page errors or external requests${errs.length ? ': ' + errs.join(' | ') : ''}`);
  } catch (e) {
    fail(`${name}: ${e.message}`);
    if (errs.length) console.log('  collected: ' + errs.join(' | '));
  } finally {
    await browser.close();
  }
}

try {
  await run('chromium', chromium);
  await run('webkit', webkit);
} finally {
  server.stop();
}
console.log(failures ? `\n${failures} FAILED` : '\nALL PASSED');
process.exit(failures ? 1 : 0);
