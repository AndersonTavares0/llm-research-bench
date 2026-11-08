// website/scripts/validate_accessibility.mjs
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3457;
const BASE_URL = `http://localhost:${PORT}`;

async function run() {
  console.log('🚀 Launching Next.js server for WCAG 2.2 AA automated audit...');
  const server = spawn('npx', ['next', 'start', '-p', String(PORT)], {
    cwd: path.join(__dirname, '..'),
    stdio: 'pipe'
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

  console.log('✓ Server listening at', BASE_URL);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  const page = await context.newPage();

  const routes = [
    { name: 'Home Page', path: '/' },
    { name: 'Model Explorer', path: '/models' },
    { name: 'Benchmark Explorer', path: '/benchmarks' },
    { name: 'Model Comparison', path: '/compare' },
    { name: 'Experiments Deep-Dive', path: '/experiments' },
    { name: 'Research Methodology & RQs', path: '/methodology' }
  ];

  let totalViolations = 0;
  const auditReport = [];

  try {
    for (const route of routes) {
      const url = `${BASE_URL}${route.path}`;
      console.log(`\n🔍 Auditing ${route.name} (${route.path})...`);
      await page.goto(url, { waitUntil: 'networkidle' });

      // Run axe-core with WCAG 2.0, 2.1, 2.2 Level A and AA standards
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
        .analyze();

      const violations = accessibilityScanResults.violations;
      totalViolations += violations.length;

      auditReport.push({
        Route: route.name,
        Path: route.path,
        Passes: accessibilityScanResults.passes.length,
        Inapplicable: accessibilityScanResults.inapplicable.length,
        Violations: violations.length,
        Status: violations.length === 0 ? '✅ 0 VIOLATIONS' : `❌ ${violations.length} VIOLATIONS`
      });

      if (violations.length > 0) {
        console.error(`❌ Found ${violations.length} accessibility violations on ${route.name}:`);
        violations.forEach((v, idx) => {
          console.error(`  ${idx + 1}. [${v.id}] ${v.help} (Impact: ${v.impact})`);
          console.error(`     Help URL: ${v.helpUrl}`);
          v.nodes.forEach((n) => {
            console.error(`     Target: ${n.target.join(' ')}`);
            console.error(`     Snippet: ${n.html}`);
          });
        });
      } else {
        console.log(`  ✅ Clean! 0 violations (${accessibilityScanResults.passes.length} rules passed)`);
      }
    }

    console.log('\n======================================================');
    console.log('📊 ACCESSIBILITY AUDIT SUMMARY (WCAG 2.2 AA)');
    console.table(auditReport);
    console.log('======================================================');

    if (totalViolations > 0) {
      throw new Error(`Accessibility audit failed with ${totalViolations} total violations.`);
    }

    console.log('🎉 ALL 6 ROUTES PASSED WCAG 2.2 LEVEL AA AUDIT WITH 0 VIOLATIONS!');
  } finally {
    await browser.close();
    server.kill();
  }
}

run().catch((err) => {
  console.error('Audit execution error:', err.message);
  process.exit(1);
});
