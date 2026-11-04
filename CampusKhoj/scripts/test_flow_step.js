const puppeteer = require('puppeteer-core');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));

  // Login
  await page.goto('http://127.0.0.1:3000/student-portal/login.html', { waitUntil: 'networkidle0' });
  await page.type('#prn', '1251150269');
  await page.type('#password', 'Student@2026!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 1500));
  console.log('Logged in URL:', page.url());

  // Report lost
  await page.goto('http://127.0.0.1:3000/student-portal/report-lost.html', { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => document.getElementById('category-id').options.length > 1);
  await page.waitForFunction(() => document.getElementById('location-id').options.length > 1);

  await page.type('#item-name', 'Logitech MX Master 3S Mouse');
  await page.select('#category-id', '1');
  await page.select('#location-id', '101');
  const today = new Date().toISOString().split('T')[0];
  await page.evaluate((d) => { document.getElementById('date-lost').value = d; }, today);
  await page.type('#description', 'Dark grey ergonomic wireless mouse with thumb wheel');

  console.log('About to click submit...');
  await page.click('button[type="submit"]');
  
  for (let i = 0; i < 10; i++) {
    await new Promise(r => setTimeout(r, 500));
    console.log(`Tick ${i} URL:`, page.url());
    if (page.url().includes('item-detail.html')) break;
  }

  await browser.close();
})();
