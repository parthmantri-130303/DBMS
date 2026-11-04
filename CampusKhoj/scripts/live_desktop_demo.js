/**
 * CampusKhoj Live Desktop Visual Demo
 * Launches a real, visible, non-headless Chrome window on the user's screen
 * and drives the full student and admin demonstration live!
 */

const puppeteer = require('puppeteer-core');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://localhost:3000';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

(async () => {
  console.log('Launching visible Chrome browser on desktop...');
  
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: false, // VISIBLE GUI WINDOW ON USER'S MONITOR!
    defaultViewport: null,
    args: [
      '--start-maximized',
      '--no-default-browser-check',
      '--no-first-run'
    ]
  });

  const pages = await browser.pages();
  const page = pages.length > 0 ? pages[0] : await browser.newPage();

  console.log('Act 1: Opening Student Portal...');
  await page.goto(`${BASE_URL}/student-portal/login.html`, { waitUntil: 'networkidle0' });
  await sleep(1500);

  // Type credentials with realistic human typing delay
  console.log('Typing student PRN and password...');
  await page.type('#prn', '1251150269', { delay: 120 });
  await sleep(600);
  await page.type('#password', 'Student@2026!', { delay: 100 });
  await sleep(800);

  console.log('Clicking Sign In...');
  await page.click('button[type="submit"]');
  await sleep(2500);

  console.log('Act 2: Exploring Campus Sections...');
  // Click Campuses in bottom navigation
  await page.goto(`${BASE_URL}/student-portal/campuses.html`, { waitUntil: 'networkidle0' });
  await sleep(2000);

  console.log('Switching to Bibwewadi Campus tab...');
  const bibBtn = await page.$('#seg-bib');
  if (bibBtn) {
    await bibBtn.click();
    await sleep(2000);
  }

  console.log('Switching back to Kondhwa Campus tab...');
  const konBtn = await page.$('#seg-kon');
  if (konBtn) {
    await konBtn.click();
    await sleep(1500);
  }

  console.log('Act 3: Opening Report Lost Item page...');
  await page.goto(`${BASE_URL}/student-portal/report-lost.html`, { waitUntil: 'networkidle0' });
  await sleep(2500);

  console.log('Act 4: Opening Admin Portal in second tab...');
  const adminPage = await browser.newPage();
  await adminPage.goto(`${BASE_URL}/admin-portal/login.html`, { waitUntil: 'networkidle0' });
  await sleep(1500);

  console.log('Typing staff credentials...');
  await adminPage.type('#username', 'admin_kon', { delay: 120 });
  await sleep(600);
  const staffPwd = process.env.KHOJ_TEST_STAFF_PASSWORD || 'Staff@CampusKhoj2026!';
  await adminPage.type('#password', staffPwd, { delay: 100 });
  await sleep(800);

  console.log('Signing in to Admin Security Control Center...');
  await adminPage.click('button[type="submit"]');
  await sleep(3000);

  console.log('Navigating to All Items Inventory & CSV export...');
  await adminPage.goto(`${BASE_URL}/admin-portal/items.html`, { waitUntil: 'networkidle0' });
  await sleep(2500);

  console.log('Navigating to Claims Review Station...');
  await adminPage.goto(`${BASE_URL}/admin-portal/claims.html`, { waitUntil: 'networkidle0' });
  await sleep(2500);

  console.log('\n============================================================');
  console.log(' Live Visual Demo Complete! Leaving Chrome open for you.   ');
  console.log('============================================================\n');

  // Do NOT close browser! Leave it open for the user to interact with directly!
})();
