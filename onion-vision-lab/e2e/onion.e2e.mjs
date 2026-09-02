/**
 * Browser e2e (Playwright + @sparticuz/chromium binary - the sandbox has no
 * Playwright CDN access):
 *   1. load app on :5174 (hero)
 *   2. upload the real 52-onion tray photo through the UI
 *      -> expect results, engine "REMOTE INFERENCE API", zero page errors
 *   3. new scan -> upload a distractor image -> expect 0 detections
 *   4. download PDF report button exists and triggers a download
 *
 * Run: node e2e/onion.e2e.mjs   (frontend :5174 + API :8788 must be up)
 */
import { chromium } from '@playwright/test';
import sparticuz from '@sparticuz/chromium';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const APP = 'http://localhost:5174';
const TRAY = path.join(ROOT, 'scan_demo_52_onions.jpg');
const DISTRACTOR = path.join(ROOT, 'e2e', 'distractor.png');
const SHOTS = '/tmp/e2e-shots';
fs.mkdirSync(SHOTS, { recursive: true });

export async function launchBrowser() {
  // sandbox has no playwright CDN access: use the @sparticuz/chromium binary
  const executablePath = await sparticuz.executablePath();
  return chromium.launch({
    executablePath,
    args: [...sparticuz.args, '--no-sandbox', '--disable-gpu'],
  });
}

const results = [];
const check = (name, ok, extra = '') => {
  results.push({ name, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? '  [' + extra + ']' : ''}`);
};

const run = async () => {
  const browser = await launchBrowser();
  const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text());
  });

  // ---- 1. hero loads ----
  await page.goto(APP, { waitUntil: 'networkidle' });
  await page.waitForSelector('text=ONION VISION LAB', { timeout: 20000 });
  await page.screenshot({ path: `${SHOTS}/01-hero.png` });
  check('hero page loads', true);

  // ---- 2. begin inspection -> upload tray photo via file input ----
  await page.click('text=begin inspection');
  await page.waitForSelector('text=Scan onions');
  const input = await page.$('input[type=file]');
  await input.setInputFiles(TRAY);
  await page.waitForSelector('text=Inspection results', { timeout: 60000 });
  await page.screenshot({ path: `${SHOTS}/02-tray-results.png`, fullPage: true });

  const engineText = await page.textContent('body');
  const remoteOk = engineText.includes('REMOTE INFERENCE API');
  const onionCards = await page.locator('text=/onion-\\d+/').count();
  check('engine label is REMOTE INFERENCE API', remoteOk);
  check(`results rendered (onion ids on page: ${onionCards})`, onionCards > 0, String(onionCards));

  // spot-check a detection circle exists on the canvas overlay
  const circles = await page.locator('button[aria-label^="onion-"]').count();
  check(`tracking circles rendered (${circles})`, circles > 0, String(circles));

  // ---- 3. disclaimers visible ----
  const disclaimers = await page.textContent('body');
  check(
    'internal-quality disclaimer present',
    disclaimers.includes('internal quality cannot be determined') ||
      disclaimers.includes('Internal quality cannot be determined'),
  );

  // ---- 4. PDF button triggers download ----
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 20000 }),
    page.click('text=PDF report'),
  ]);
  check('PDF report downloads', Boolean(download));

  // ---- 5. distractor image -> 0 detections ----
  await page.click('text=new scan');
  await page.waitForSelector('text=Scan onions');
  const input2 = await page.$('input[type=file]');
  await input2.setInputFiles(DISTRACTOR);
  await page.waitForSelector('text=Inspection results', { timeout: 60000 });
  await page.screenshot({ path: `${SHOTS}/03-distractor.png`, fullPage: true });
  const body = await page.textContent('body');
  const zeroDet = body.includes('No onions detected in this image');
  const onionIdsAfter = await page.locator('button[aria-label^="onion-"]').count();
  check('distractor image -> 0 detections', zeroDet && onionIdsAfter === 0, `circles=${onionIdsAfter}`);

  // ---- error accounting ----
  const hardConsole = consoleErrors.filter((t) => !t.includes('favicon'));
  console.log('\npageErrors:', pageErrors);
  console.log('consoleErrors:', consoleErrors);
  check('zero page errors', pageErrors.length === 0, pageErrors.slice(0, 2).join(' | '));
  check('zero unexpected console errors', hardConsole.length === 0, hardConsole.slice(0, 2).join(' | '));

  await browser.close();
  const failed = results.filter((r) => !r.ok);
  console.log(`\n==== e2e: ${results.length - failed.length}/${results.length} passed ====`);
  if (failed.length) process.exit(1);
};

run().catch((e) => {
  console.error('e2e crashed:', e);
  process.exit(1);
});
