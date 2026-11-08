import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

async function inspectSite(url, name) {
  console.log(`\n=================== Inspecting ${name} (${url}) ===================`);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(4000); // Wait for fonts and client render

    const screenshotPath = `/home/anderson/.gemini/antigravity-cli/brain/4826fcc1-567b-44c1-8e85-c0948f0cf924/screenshots/ref_${name}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`Saved screenshot to ${screenshotPath}`);

    const analysis = await page.evaluate(() => {
      // 1. Get CSS variables on root
      const rootStyles = getComputedStyle(document.documentElement);
      const bodyStyles = getComputedStyle(document.body);

      // Collect all css variables
      const cssVars = {};
      for (let sheet of document.styleSheets) {
        try {
          for (let rule of sheet.cssRules) {
            if (rule.selectorText === ':root' || rule.selectorText === 'html' || rule.selectorText === 'body') {
              for (let i = 0; i < rule.style.length; i++) {
                const name = rule.style[i];
                if (name.startsWith('--')) {
                  cssVars[name] = rule.style.getPropertyValue(name).trim();
                }
              }
            }
          }
        } catch (e) {}
      }

      // Collect computed colors and fonts from key elements
      const elementsToSample = ['body', 'h1', 'h2', 'h3', 'p', 'a', 'table', 'th', 'td', 'nav', 'button', 'input', 'code'];
      const sampledTypography = {};
      for (const sel of elementsToSample) {
        const el = document.querySelector(sel);
        if (el) {
          const s = getComputedStyle(el);
          sampledTypography[sel] = {
            fontFamily: s.fontFamily,
            fontSize: s.fontSize,
            fontWeight: s.fontWeight,
            lineHeight: s.lineHeight,
            letterSpacing: s.letterSpacing,
            color: s.color,
            backgroundColor: s.backgroundColor
          };
        }
      }

      // Collect all unique text colors and background colors used on the page
      const allElements = Array.from(document.querySelectorAll('*')).slice(0, 400);
      const textColors = new Set();
      const bgColors = new Set();
      const borderColors = new Set();
      const fontFamilies = new Set();

      for (const el of allElements) {
        const s = getComputedStyle(el);
        if (s.color && s.color !== 'rgba(0, 0, 0, 0)') textColors.add(s.color);
        if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'transparent') bgColors.add(s.backgroundColor);
        if (s.borderColor && s.borderColor !== 'rgba(0, 0, 0, 0)' && s.borderWidth !== '0px') borderColors.add(s.borderColor);
        if (s.fontFamily) fontFamilies.add(s.fontFamily);
      }

      return {
        title: document.title,
        bodyBg: bodyStyles.backgroundColor,
        bodyColor: bodyStyles.color,
        bodyFont: bodyStyles.fontFamily,
        cssVars: Object.entries(cssVars).slice(0, 40),
        sampledTypography,
        textColors: Array.from(textColors).slice(0, 20),
        bgColors: Array.from(bgColors).slice(0, 20),
        borderColors: Array.from(borderColors).slice(0, 20),
        fontFamilies: Array.from(fontFamilies)
      };
    });

    console.log(JSON.stringify(analysis, null, 2));
    return analysis;
  } catch (err) {
    console.error(`Error inspecting ${url}:`, err.message);
  } finally {
    await browser.close();
  }
}

async function run() {
  await inspectSite('https://artificialanalysis.ai/leaderboards/models', 'artificial_analysis');
  await inspectSite('https://epoch.ai/', 'epoch_ai');
  await inspectSite('https://epoch.ai/blog', 'epoch_ai_blog');
}

run();
