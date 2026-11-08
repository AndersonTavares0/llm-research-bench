// website/scripts/validate_e2e.mjs
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOTS_DIR = path.join(__dirname, '../public/screenshots');
fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

const PORT = 3456;
const BASE_URL = `http://localhost:${PORT}`;

async function run() {
  console.log('🚀 Starting Next.js production server for E2E validation...');
  const server = spawn('npx', ['next', 'start', '-p', String(PORT)], {
    cwd: path.join(__dirname, '..'),
    stdio: 'pipe'
  });

  server.stdout.on('data', (d) => {
    const msg = d.toString();
    if (msg.includes('Ready') || msg.includes('started')) {
      console.log('Next.js server ready:', msg.trim());
    }
  });

  // Wait for server to be responsive
  let serverReady = false;
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch(BASE_URL);
      if (res.ok) {
        serverReady = true;
        break;
      }
    } catch (e) {
      // wait
    }
    await new Promise((r) => setTimeout(r, 500));
  }

  if (!serverReady) {
    server.kill();
    throw new Error('Server failed to start within 15 seconds');
  }

  console.log('✓ Server is listening at', BASE_URL);

  const browser = await chromium.launch({ headless: true });
  const results = [];

  try {
    // 1. Desktop Context (1440x900)
    const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await desktopContext.newPage();

    console.log('--- Validating Desktop Experience ---');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForSelector('canvas', { timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '01_desktop_home.png'), fullPage: true });
    results.push({ viewport: 'Desktop (1440x900)', page: 'Home', status: 'PASS' });

    await page.goto(`${BASE_URL}/models`, { waitUntil: 'networkidle' });
    await page.waitForSelector('table', { timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '02_desktop_models.png'), fullPage: true });
    results.push({ viewport: 'Desktop (1440x900)', page: 'Model Explorer', status: 'PASS' });

    await page.goto(`${BASE_URL}/benchmarks`, { waitUntil: 'networkidle' });
    await page.waitForSelector('table', { timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '03_desktop_benchmarks.png'), fullPage: true });
    results.push({ viewport: 'Desktop (1440x900)', page: 'Benchmark Explorer', status: 'PASS' });

    await page.goto(`${BASE_URL}/compare`, { waitUntil: 'networkidle' });
    await page.waitForSelector('table', { timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '04_desktop_compare.png'), fullPage: true });
    results.push({ viewport: 'Desktop (1440x900)', page: 'Model Comparison', status: 'PASS' });

    await page.goto(`${BASE_URL}/experiments`, { waitUntil: 'networkidle' });
    await page.waitForSelector('canvas', { timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '05_desktop_experiments.png'), fullPage: true });
    results.push({ viewport: 'Desktop (1440x900)', page: 'Experiments', status: 'PASS' });

    await page.goto(`${BASE_URL}/methodology`, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '06_desktop_methodology.png'), fullPage: true });
    results.push({ viewport: 'Desktop (1440x900)', page: 'Methodology & RQs', status: 'PASS' });

    await desktopContext.close();

    // 2. Mobile Context (iPhone 14 / 390x844)
    console.log('--- Validating Mobile Experience ---');
    const mobileContext = await browser.newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true
    });
    const mobilePage = await mobileContext.newPage();

    await mobilePage.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await mobilePage.waitForSelector('canvas', { timeout: 10000 });
    await mobilePage.screenshot({ path: path.join(SCREENSHOTS_DIR, '07_mobile_home.png'), fullPage: true });
    results.push({ viewport: 'Mobile (390x844)', page: 'Home', status: 'PASS' });

    await mobilePage.goto(`${BASE_URL}/models`, { waitUntil: 'networkidle' });
    await mobilePage.waitForSelector('table', { timeout: 10000 });
    await mobilePage.screenshot({ path: path.join(SCREENSHOTS_DIR, '08_mobile_models.png'), fullPage: true });
    results.push({ viewport: 'Mobile (390x844)', page: 'Model Explorer', status: 'PASS' });

    await mobilePage.goto(`${BASE_URL}/benchmarks`, { waitUntil: 'networkidle' });
    await mobilePage.waitForSelector('table', { timeout: 10000 });
    await mobilePage.screenshot({ path: path.join(SCREENSHOTS_DIR, '09_mobile_benchmarks.png'), fullPage: true });
    results.push({ viewport: 'Mobile (390x844)', page: 'Benchmark Explorer', status: 'PASS' });

    await mobileContext.close();

    console.log('\n========================================');
    console.log('🎉 ALL DESKTOP & MOBILE TESTS PASSED!');
    console.table(results);
    console.log('========================================');
  } finally {
    await browser.close();
    server.kill();
  }
}

run().catch((err) => {
  console.error('E2E validation failed:', err);
  process.exit(1);
});
