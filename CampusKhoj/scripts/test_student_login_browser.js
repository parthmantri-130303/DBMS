const puppeteer = require('puppeteer-core');
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,900']
  });
  const page = await browser.newPage();
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));

  console.log('Navigating to login.html...');
  await page.goto('http://127.0.0.1:3000/student-portal/login.html', { waitUntil: 'networkidle0' });
  
  console.log('Typing credentials...');
  await page.type('#prn', '1251150269');
  await page.type('#password', '1251150269');
  
  console.log('Clicking submit...');
  await page.click('button[type="submit"]');

  console.log('Waiting for URL change...');
  await page.waitForFunction(() => window.location.href.includes('change-password.html'), { timeout: 8000 });
  console.log('SUCCESS! Current URL:', page.url());
  
  await browser.close();
})();

