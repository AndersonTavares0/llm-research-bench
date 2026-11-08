import { chromium } from 'playwright';
import fs from 'fs';

async function runDesignCritique() {
  const browser = await chromium.launch({ headless: true });
  const contextLight = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2
  });
  const pageLight = await contextLight.newPage();

  const contextDark = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2
  });
  const pageDark = await contextDark.newPage();

  const contextMobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2
  });
  const pageMobile = await contextMobile.newPage();

  const screenshotDir = '/home/anderson/.gemini/antigravity-cli/brain/4826fcc1-567b-44c1-8e85-c0948f0cf924/screenshots';

  console.log('Capturing Desktop Light Mode...');
  await pageLight.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
  await pageLight.screenshot({ path: `${screenshotDir}/critique_desktop_light_home.png`, fullPage: false });
  await pageLight.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
  await pageLight.screenshot({ path: `${screenshotDir}/critique_desktop_light_models.png`, fullPage: false });

  console.log('Capturing Desktop Dark Mode...');
  await pageDark.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
  await pageDark.evaluate(() => {
    document.documentElement.classList.add('dark');
  });
  await pageDark.waitForTimeout(500);
  await pageDark.screenshot({ path: `${screenshotDir}/critique_desktop_dark_home.png`, fullPage: false });
  await pageDark.goto('http://localhost:3000/models', { waitUntil: 'networkidle' });
  await pageDark.evaluate(() => {
    document.documentElement.classList.add('dark');
  });
  await pageDark.waitForTimeout(500);
  await pageDark.screenshot({ path: `${screenshotDir}/critique_desktop_dark_models.png`, fullPage: false });

  console.log('Capturing Mobile Viewport...');
  await pageMobile.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
  await pageMobile.screenshot({ path: `${screenshotDir}/critique_mobile_home.png`, fullPage: false });

  // Extract structural layout data
  const metrics = await pageLight.evaluate(() => {
    const h1 = document.querySelector('h1');
    const table = document.querySelector('table');
    const body = document.body;

    const h1Styles = h1 ? window.getComputedStyle(h1) : null;
    const bodyStyles = window.getComputedStyle(body);

    return {
      h1FontFamily: h1Styles ? h1Styles.fontFamily : null,
      h1FontSize: h1Styles ? h1Styles.fontSize : null,
      h1LineHeight: h1Styles ? h1Styles.lineHeight : null,
      bodyFontFamily: bodyStyles.fontFamily,
      bodyBg: bodyStyles.backgroundColor,
      bodyColor: bodyStyles.color,
      hasHorizontalScroll: document.documentElement.scrollWidth > window.innerWidth
    };
  });

  console.log('DOM Design Metrics:', JSON.stringify(metrics, null, 2));

  await browser.close();
}

runDesignCritique().catch(console.error);
