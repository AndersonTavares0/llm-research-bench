import { chromium } from 'playwright';

// Helper function to calculate relative luminance
function luminance(r, g, b) {
  const a = [r, g, b].map(v => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
}

function parseRgb(rgbStr) {
  const match = rgbStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) return [0, 0, 0];
  return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3])];
}

function contrast(rgb1, rgb2) {
  const lum1 = luminance(...parseRgb(rgb1));
  const lum2 = luminance(...parseRgb(rgb2));
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  return (brightest + 0.05) / (darkest + 0.05);
}

async function auditContrast() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1100 } });
  await page.goto('file:///home/anderson/Documents/Github/llm-research-bench/website/specimen.html');

  const elementsData = await page.evaluate(() => {
    const textSelectors = [
      'h1.editorial-title',
      '.meta-lead',
      '.section-heading',
      '.swatch-name',
      '.swatch-contrast',
      'table.specimen-table th',
      '.model-name',
      '.badge-tag',
      '.metric-cell span',
      '.editorial-callout h3',
      '.editorial-callout p'
    ];

    const results = [];
    for (const sel of textSelectors) {
      const els = document.querySelectorAll(sel);
      for (const el of els) {
        const s = window.getComputedStyle(el);
        let bg = s.backgroundColor;
        let parent = el.parentElement;
        while ((bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') && parent) {
          bg = window.getComputedStyle(parent).backgroundColor;
          parent = parent.parentElement;
        }

        results.push({
          selector: sel,
          text: el.innerText.slice(0, 30),
          color: s.color,
          bg: bg,
          fontSize: s.fontSize,
          fontWeight: s.fontWeight
        });
      }
    }
    return results;
  });

  console.log(`Audited ${elementsData.length} text elements in visual specimen.`);

  let failures = 0;
  for (const item of elementsData) {
    const ratio = contrast(item.color, item.bg);
    const minRequired = parseFloat(item.fontSize) >= 18 || (parseFloat(item.fontSize) >= 14 && parseInt(item.fontWeight) >= 600) ? 3.0 : 4.5;
    const pass = ratio >= minRequired;
    if (!pass) {
      console.warn(`[FAIL] ${item.selector} ("${item.text}"): ${ratio.toFixed(2)}:1 (Requires ${minRequired}:1) - text: ${item.color}, bg: ${item.bg}`);
      failures++;
    }
  }

  if (failures === 0) {
    console.log('✅ ALL specimen text elements achieve 100% WCAG 2.2 AA contrast compliance!');
  } else {
    console.log(`❌ Found ${failures} contrast issues.`);
  }

  await browser.close();
}

auditContrast().catch(console.error);
