const { chromium } = require('C:/Users/sicco/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { pathToFileURL } = require('url');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('CONSOLE ' + m.text()); });

  await page.goto(pathToFileURL(process.cwd() + '/output/剑三生活技艺工作台.html').href);
  await page.waitForTimeout(1500);

  const kpi = await page.evaluate(() => ({
    tabs: [...document.querySelectorAll('#segType button')].map(b => b.textContent),
    meta: document.getElementById('metaCount').textContent,
    rows: document.querySelectorAll('#tProfit tbody tr').length,
    kpis: [...document.querySelectorAll('#kpis .kpi')].map(x => x.innerText.replace(/\n/g, ' ')),
    pve: document.querySelectorAll('#tPve tbody tr').length,
  }));
  console.log('INIT', JSON.stringify(kpi, null, 1));
  fs.mkdirSync('qa', { recursive: true });
  await page.screenshot({ path: 'qa/craft-profit.png', fullPage: false });

  for (const t of ['founding', 'tailoring', 'cooking', 'medicine']) {
    await page.click(`#segType button[data-v="${t}"]`);
    await page.waitForTimeout(400);
    const info = await page.evaluate(() => {
      const rows = [...document.querySelectorAll('#tProfit tbody tr')].slice(0, 6).map(tr =>
        [...tr.querySelectorAll('td')].map(td => td.innerText.trim()).filter(Boolean).slice(0, 8).join(' | '));
      return { n: document.querySelectorAll('#tProfit tbody tr').length, rows };
    });
    console.log('TAB', t, info.n, info.rows.slice(0, 3));
  }
  await page.screenshot({ path: 'qa/craft-tailoring.png' });

  // 定位筛选
  for (const k of ['gear', 'mat', 'pve', 'all']) {
    await page.click(`#segKind button[data-v="${k}"]`);
    await page.waitForTimeout(300);
    const n = await page.evaluate(() => document.querySelectorAll('#tProfit tbody tr').length);
    console.log('KIND', k, n);
  }
  // BOM 展开
  await page.click('#segType button[data-v="founding"]');
  await page.waitForTimeout(300);
  await page.click('#tProfit tbody tr:first-child .rname');
  await page.waitForTimeout(400);
  const bom = await page.evaluate(() => ({
    on: document.getElementById('bomModal').classList.contains('on'),
    title: document.getElementById('bomTitle').innerText,
    rows: document.querySelectorAll('#bomBody .bomrow').length,
  }));
  console.log('BOM', JSON.stringify(bom));
  await page.screenshot({ path: 'qa/craft-bom.png' });
  await page.click('#bomClose');

  // 升级路径：4 系各跑一次
  await page.click('nav button[data-tab="path"]');
  for (const t of ['cooking', 'medicine', 'founding', 'tailoring']) {
    await page.click(`#segPType button[data-v="${t}"]`);
    await page.click('#btnPlan');
    await page.waitForTimeout(400);
    const n = await page.evaluate(() => ({
      steps: document.querySelectorAll('#pPath .pstep').length,
      kpi: [...document.querySelectorAll('#pKpis .kpi')].map(x => x.innerText.replace(/\n/g, ' ')),
    }));
    console.log('PATH', t, JSON.stringify(n));
  }
  await page.screenshot({ path: 'qa/craft-path.png' });

  // 计划页
  await page.click('nav button[data-tab="profit"]');
  await page.click('#segType button[data-v="all"]');
  await page.waitForTimeout(300);
  await page.evaluate(() => document.querySelector('#tProfit .qin').value = 5);
  await page.evaluate(() => document.querySelector('#tProfit .qin').dispatchEvent(new Event('change')));
  await page.waitForTimeout(500);
  const sum = await page.evaluate(() => document.getElementById('sumBar').innerText.replace(/\n/g, ' '));
  console.log('SUM', sum);
  await page.click('nav button[data-tab="plan"]');
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'qa/craft-plan.png' });

  console.log('ERRORS', errors.length ? errors : 'none');
  await browser.close();
})();
