import { chromium } from 'playwright';

async function captureSpecimen() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1400, height: 1100 },
    deviceScaleFactor: 2 // High DPI retina capture for crisp inspection
  });

  const specimenUrl = 'file:///home/anderson/Documents/Github/llm-research-bench/website/specimen.html';
  console.log(`Navigating to ${specimenUrl}...`);
  await page.goto(specimenUrl, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  const screenshotPath = '/home/anderson/.gemini/antigravity-cli/brain/4826fcc1-567b-44c1-8e85-c0948f0cf924/screenshots/visual_specimen.png';
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`Specimen screenshot saved to ${screenshotPath}`);

  // Inspect font sizes, layout integrity, and check for overflow
  const diagnostics = await page.evaluate(() => {
    const docWidth = document.documentElement.scrollWidth;
    const winWidth = window.innerWidth;
    const hasHorizontalOverflow = docWidth > winWidth;

    const cards = Array.from(document.querySelectorAll('.swatch-card')).length;
    const tableRows = Array.from(document.querySelectorAll('tbody tr')).length;

    return {
      docWidth,
      winWidth,
      hasHorizontalOverflow,
      cardsCount: cards,
      rowsCount: tableRows
    };
  });

  console.log('Diagnostics:', JSON.stringify(diagnostics, null, 2));
  await browser.close();
}

captureSpecimen().catch(console.error);
