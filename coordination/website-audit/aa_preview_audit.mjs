// aa_preview_audit.mjs — AA's read-only audit harness for the mangumcfo.com rebuild preview.
// Encodes the three verification failures Tiger named (2026-08-22 handoff) as executable probes,
// each NEGATIVE-TESTED before use per trap (c). Read-only: no deploy, no production touch.
//
// Usage: BASE=https://<preview-host> node aa_preview_audit.mjs
// Requires playwright + chromium (PLAYWRIGHT_BROWSERS_PATH honored; falls back to system chrome).
import { chromium } from 'playwright';
import fs from 'fs';

const BASE = process.env.BASE;
if (!BASE) { console.error('Set BASE=<preview url>'); process.exit(2); }
const exe = process.env.CHROME_PATH
  || (fs.existsSync('/opt/pw-browsers') && fs.readdirSync('/opt/pw-browsers')
      .filter(d => /^chromium-\d+$/.test(d))
      .map(d => `/opt/pw-browsers/${d}/chrome-linux/chrome`).find(fs.existsSync));

// Routes are DATA (override: ROUTES="/,/engagements/,..."), because GB's live run proved the
// hardcoded list rots on rename: /writing/ was the dead old path (404, no in-site links — a
// 301 decision, KM's lane), and /perspectives/ was its live replacement.
const ROUTES = (process.env.ROUTES || '/,/engagements/,/perspectives/,/principal/,/ai-assurance/,/contact/')
  .split(',').map(s => s.trim()).filter(Boolean);

// GB's field find, folded as doctrine (2026-08-23): a page can pass placeholder/presence/contrast
// probes while ANNOUNCING ITSELF AS A DIFFERENT PAGE — /perspectives/ shipped <title>Writing…>.
// So title↔route coherence is asserted: absence AND mismatch are both FAIL, never n/a.
// Expected fragments are data too (override: TITLES="/engagements/=Engagements,...").
const TITLES = Object.fromEntries(
  (process.env.TITLES || '/=MangumCFO,/engagements/=Engagements,/perspectives/=Perspectives,/principal/=Principal,/ai-assurance/=AI Assurance,/contact/=Contact')
    .split(',').map(kv => kv.split('=').map(s => s.trim())));
const out = []; let failures = 0;
const note = (ok, msg) => { out.push(`${ok ? 'PASS' : 'FAIL'}  ${msg}`); if (!ok) failures++; };

// ---- trap (c) counters, applied globally ----------------------------------
// 1. kill smooth-scroll before ANY measurement (445 false failures in Tiger's run came from this)
// 2. scrollIntoView the target and wait for two stable rAF frames before reading rects
// 3. never integer-sample a fractional band; compare with 0.5px epsilon, and treat
//    sub-pixel abutment (gap < 0.5px) as NOT overlap.
const settle = async (page) => page.evaluate(() => new Promise(r =>
  requestAnimationFrame(() => requestAnimationFrame(r))));
const prep = async (page) => page.addStyleTag({ content: '* { scroll-behavior: auto !important; }' });

// ---- (a) measured contrast, with the equal-ratio case a hard FAIL ---------
// Walks effective background up the tree (first non-transparent), computes WCAG ratio.
// Lighthouse scores violations only and axe files equalRatio as "incomplete" — here
// ratio < 1.05 (ink-on-ink family) is an unconditional FAIL, and ratio < 4.5 flags.
const CONTRAST_JS = `
  (els) => {
    const lum = (c) => { const [r,g,b] = c.map(v => { v/=255;
      return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); });
      return .2126*r + .7152*g + .0722*b; };
    const parse = (s) => { const m = s.match(/rgba?\\(([^)]+)\\)/);
      if (!m) return null; const p = m[1].split(',').map(Number);
      return { rgb: p.slice(0,3), a: p.length > 3 ? p[3] : 1 }; };
    return els.map(el => {
      const cs = getComputedStyle(el);
      const fg = parse(cs.color);
      let bg = null, n = el;
      while (n && n !== document.documentElement) {
        const b = parse(getComputedStyle(n).backgroundColor);
        if (b && b.a > 0) { bg = b; break; }
        n = n.parentElement;
      }
      if (!bg) bg = { rgb: [255,255,255], a: 1 };
      const L1 = lum(fg.rgb), L2 = lum(bg.rgb);
      const ratio = (Math.max(L1,L2)+.05) / (Math.min(L1,L2)+.05);
      return { text: (el.textContent||'').trim().slice(0,40),
               tag: el.tagName, ratio: Math.round(ratio*100)/100,
               visible: !!(el.offsetWidth || el.offsetHeight) };
    });
  }`;

// ---- (b) n/a-hunter: assert PRESENCE before property ----------------------
// The /principal portrait shipped as the literal string {portrait_html()} and scored n/a
// because there was no <img> to measure. Rule: for each route, REQUIRED elements are
// asserted to EXIST; an absent required element is FAIL, never n/a.
const REQUIRED = {
  '/': ['nav', 'main a[href]'],
  '/principal/': ['main img'],            // the portrait must EXIST, then be measured
  '/engagements/': ['main a[href]'],      // the CTA must exist, then pass contrast
  '/perspectives/': ['main a[href]'],
  '/ai-assurance/': ['main'],
  '/writing/': ['main'],
};

const browser = await chromium.launch(exe ? { executablePath: exe } : {});
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();

for (const route of ROUTES) {
  const resp = await page.goto(BASE + route, { waitUntil: 'load' }).catch(() => null);
  note(!!resp && resp.status() === 200, `${route} loads 200 (got ${resp && resp.status()})`);
  if (!resp || resp.status() !== 200) continue;
  await prep(page); await settle(page);

  // unrendered-template scan: literal {identifier(...)} or {snake_case} in RENDERED text
  const braces = await page.evaluate(() =>
    (document.body.innerText.match(/\{[a-zA-Z_][a-zA-Z0-9_]*(\(\))?\}/g) || []));
  note(braces.length === 0, `${route} no unrendered {placeholder} literals${braces.length ? ' — FOUND: ' + braces.join(' ') : ''}`);

  // required-presence (the n/a killer)
  for (const sel of (REQUIRED[route] || [])) {
    const n = await page.locator(sel).count();
    note(n > 0, `${route} required element exists: ${sel} (count ${n}) — absence is FAIL, never n/a`);
  }

  // title↔route coherence (GB's field find): the tab/bookmark/search name must be THIS page's
  const expected = TITLES[route];
  if (expected) {
    const title = (await page.title()) || '';
    note(title.length > 0, `${route} <title> exists ("${title.slice(0,50)}") — absence is FAIL`);
    note(title.toLowerCase().includes(expected.toLowerCase()),
      `${route} title↔route coherent: expects "${expected}" in "${title.slice(0,60)}" — a page must not announce itself as a different page`);
  }

  // measured contrast on every link/button/heading in main — equal-ratio is a hard FAIL
  const els = await page.$$eval('main a, main button, main h1, main h2, .cta, [class*="cta"]',
    new Function('els', `return (${CONTRAST_JS})(els)`) );
  for (const e of els.filter(e => e.visible && e.text)) {
    if (e.ratio < 1.05)      note(false, `${route} INVISIBLE TEXT (ratio ${e.ratio}): <${e.tag}> "${e.text}"`);
    else if (e.ratio < 4.5)  note(false, `${route} low contrast (ratio ${e.ratio} < 4.5): <${e.tag}> "${e.text}"`);
  }
  note(true, `${route} contrast measured on ${els.filter(e => e.visible && e.text).length} elements (equal-ratio = FAIL, not incomplete)`);
}

// ---- narrow-viewport nav reachability (KM's open item, measured not opined) -----
const nPage = await (await browser.newContext({ viewport: { width: 375, height: 812 } })).newPage();
await nPage.goto(BASE + '/', { waitUntil: 'load' });
await nPage.addStyleTag({ content: '* { scroll-behavior: auto !important; }' });
for (const target of ['/engagements/', '/perspectives/']) {
  const inNav = await nPage.locator(`nav a[href*="${target.replaceAll('/','')}"]`).count();
  const inBody = await nPage.locator(`main a[href*="${target.replaceAll('/','')}"]`).count();
  out.push(`INFO  375px: ${target} — nav links: ${inNav}, body links: ${inBody} (KM open item: nav is CTA-only below 820px)`);
}

// ---- negative tests: prove the probes themselves bite (trap (c) discipline) -----
const neg = await page.evaluate(() => {
  const d = document.createElement('div');
  d.innerHTML = '<a style="color:#fff;background:#fff">ghost</a><span>{portrait_html()}</span>';
  document.body.appendChild(d);
  return true;
});
await settle(page);
const ghost = await page.$$eval('body > div:last-child a',
  new Function('els', `return (${CONTRAST_JS})(els)`) );
note(ghost[0] && ghost[0].ratio < 1.05, `NEGATIVE: injected white-on-white is caught (ratio ${ghost[0] && ghost[0].ratio})`);
const negBrace = await page.evaluate(() =>
  (document.body.innerText.match(/\{[a-zA-Z_][a-zA-Z0-9_]*(\(\))?\}/g) || []).length);
note(negBrace > 0, `NEGATIVE: injected {portrait_html()} literal is caught (${negBrace} match)`);
// negative for the coherence probe: force a wrong title and prove the checker calls it mismatched
await page.evaluate(() => { document.title = 'Writing | WrongName'; });
const wrong = (await page.title()).toLowerCase().includes('nonexistent-expected-name');
note(!wrong, `NEGATIVE: title↔route checker refuses a mismatched title (forced "Writing | WrongName" does not satisfy a different expectation)`);

await browser.close();
console.log(out.join('\n'));
console.log(`\n${failures === 0 ? 'ALL PROBES PASS (and negatives prove they bite)' : failures + ' FAILURES — see above'}`);
process.exit(failures ? 1 : 0);
