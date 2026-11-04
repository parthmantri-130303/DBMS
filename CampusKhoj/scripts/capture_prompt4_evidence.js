const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const OUT_DIR = path.join(__dirname, '..', 'demo_screens');

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

const STAFF_PASSWORD = process.env.KHOJ_TEST_STAFF_PASSWORD || 'Staff@CampusKhoj2026!';
const STUDENT_PASSWORD = process.env.KHOJ_TEST_STUDENT_PASSWORD || 'Student@DemoPass2026!';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,900']
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 900 });

    // 1. Admin Login & Locations Management
    console.log('Navigating to Admin Login...');
    await page.goto('http://127.0.0.1:3000/admin-portal/login.html', { waitUntil: 'networkidle0' });
    await page.type('#username', 'admin_kon');
    await page.type('#password', STAFF_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {});

    console.log('Navigating to Admin Locations...');
    await page.goto('http://127.0.0.1:3000/admin-portal/locations.html', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1200));
    await page.screenshot({ path: path.join(OUT_DIR, 'admin_locations_management.png'), fullPage: false });
    console.log('Saved admin_locations_management.png');

    // 2. Admin Messages Log
    console.log('Navigating to Admin Messages...');
    await page.goto('http://127.0.0.1:3000/admin-portal/messages.html', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1200));
    await page.screenshot({ path: path.join(OUT_DIR, 'admin_messages_log.png'), fullPage: false });
    console.log('Saved admin_messages_log.png');

    // 3. Student Login & Two-Step Location Picker
    console.log('Logging in as student...');
    await page.goto('http://127.0.0.1:3000/student-portal/login.html', { waitUntil: 'networkidle0' });
    await page.type('#prn', '1251070075');
    await page.type('#password', STUDENT_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {});

    console.log('Navigating to Report Lost (Two-Step Location Picker)...');
    await page.goto('http://127.0.0.1:3000/student-portal/report-lost.html', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1000));

    // Select Building in Step 1 to show Step 2 populated
    await page.select('#step1-building', 'Building 2');
    await new Promise(r => setTimeout(r, 500));
    await page.screenshot({ path: path.join(OUT_DIR, 'two_step_location_picker.png'), fullPage: false });
    console.log('Saved two_step_location_picker.png');

    // 4. Student Messages Drawer
    console.log('Opening Student Messages Drawer on Home Page...');
    await page.goto('http://127.0.0.1:3000/student-portal/index.html', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1000));
    
    // Click messages drawer trigger
    const msgBtn = await page.$('#nav-btn-messages');
    if (msgBtn) {
      await msgBtn.click();
      await new Promise(r => setTimeout(r, 800));
    }
    await page.screenshot({ path: path.join(OUT_DIR, 'simulated_messages_drawer.png'), fullPage: false });
    console.log('Saved simulated_messages_drawer.png');

  } catch (err) {
    console.error('Evidence capture error:', err);
  } finally {
    await browser.close();
  }
})();

