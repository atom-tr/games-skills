#!/usr/bin/env node
/**
 * redeem_deltaforce.js — Delta Force (Garena) gift code redeemer
 *
 * Usage:
 *   node redeem_deltaforce.js <CODE> [--headless]
 *
 * Requires:
 *   - GARENA_COOKIE env var (copy from browser DevTools → Application → Cookies)
 *     e.g. export GARENA_COOKIE="token=xxx; _ga=xxx"
 *   OR run in headed mode (--no-headless) to login manually on first run.
 *
 * Exit codes:
 *   0 = success
 *   1 = error (code invalid/expired/already used)
 *   2 = script/browser error
 */

import puppeteer from "puppeteer";

const REDEEM_URL = "https://redeem.df.garena.sg/vi/cdkgarena.html";
const SELECTORS = {
  // The active input field (state-after.show is the logged-in state)
  input:  '.state.state-after.show input.exc-input',
  button: '.state.state-after.show a.btn-exchange',
  // Result messages — common Garena patterns
  resultSuccess: '.alert-success, .swal2-success, .modal-success, [class*="success"]',
  resultError:   '.alert-danger,  .swal2-error,   .modal-error,   [class*="error"]',
  // SweetAlert2 (common on Garena pages)
  swal:          '.swal2-popup',
  swalContent:   '.swal2-html-container, .swal2-content',
  swalConfirm:   '.swal2-confirm',
};

const args = process.argv.slice(2);
const code = args.find(a => !a.startsWith('--'));
const headless = !args.includes('--no-headless');

if (!code) {
  console.error('Usage: node redeem_deltaforce.js <CODE> [--no-headless]');
  process.exit(2);
}

(async () => {
  const browser = await puppeteer.launch({
    headless,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  await page.setUserAgent(
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  );

  // Inject saved cookies if provided via env var
  const cookieStr = process.env.GARENA_COOKIE;
  if (cookieStr) {
    const cookieDomain = 'redeem.df.garena.sg';
    const cookies = cookieStr.split(';').map(pair => {
      const [name, ...rest] = pair.trim().split('=');
      return { name: name.trim(), value: rest.join('=').trim(), domain: cookieDomain, path: '/' };
    });
    await page.setCookie(...cookies);
  }

  try {
    console.log(`[*] Navigating to ${REDEEM_URL}`);
    await page.goto(REDEEM_URL, { waitUntil: 'networkidle2', timeout: 30000 });

    // Check if login wall is shown (state-after.show not present = not logged in)
    const inputVisible = await page.$(SELECTORS.input);
    if (!inputVisible) {
      console.error('[!] Not logged in. Re-run with --no-headless to login manually,');
      console.error('    then copy cookies from DevTools into GARENA_COOKIE env var.');
      await browser.close();
      process.exit(2);
    }

    console.log(`[*] Entering code: ${code}`);
    await page.click(SELECTORS.input);
    await page.evaluate((sel) => {
      document.querySelector(sel).value = '';  // clear any existing value
    }, SELECTORS.input);
    await page.type(SELECTORS.input, code, { delay: 50 });

    console.log('[*] Clicking redeem button...');
    await page.click(SELECTORS.button);

    // Wait for SweetAlert2 or any result modal
    let resultText = '';
    try {
      await page.waitForSelector(SELECTORS.swal, { timeout: 10000 });
      resultText = await page.$eval(
        SELECTORS.swalContent,
        el => el.innerText.trim()
      ).catch(() => '');

      // Take screenshot for debugging
      await page.screenshot({ path: `/tmp/df_redeem_${code}.png` });
      console.log(`[*] Screenshot saved: /tmp/df_redeem_${code}.png`);

      // Dismiss the modal
      const confirmBtn = await page.$(SELECTORS.swalConfirm);
      if (confirmBtn) await confirmBtn.click();

    } catch {
      // Fallback: read any visible alert/toast
      resultText = await page.evaluate(() => {
        const el = document.querySelector('.alert, .toast, [class*="result"], [class*="msg"]');
        return el ? el.innerText.trim() : '';
      });
    }

    console.log(`[result] ${resultText}`);

    // Determine success/failure from result text
    const errorKeywords = ['invalid', 'expired', 'used', 'không hợp lệ', 'đã dùng', 'hết hạn', 'không tìm thấy', 'error', 'fail'];
    const successKeywords = ['success', 'thành công', 'nhận được', 'reward', 'redeemed', 'ok'];

    const lower = resultText.toLowerCase();
    const isError   = errorKeywords.some(k => lower.includes(k));
    const isSuccess = successKeywords.some(k => lower.includes(k));

    if (isSuccess) {
      console.log(`[SUCCESS] Code ${code} redeemed successfully.`);
      process.exitCode = 0;
    } else if (isError) {
      console.log(`[ERROR] Code ${code} failed: ${resultText}`);
      process.exitCode = 1;
    } else {
      // Unknown result — print it, exit 0 so agent can judge
      console.log(`[UNKNOWN] Result unclear: "${resultText}" — check screenshot.`);
      process.exitCode = 0;
    }

  } catch (err) {
    console.error(`[FATAL] ${err.message}`);
    await page.screenshot({ path: `/tmp/df_redeem_error.png` }).catch(() => {});
    process.exitCode = 2;
  } finally {
    await browser.close();
  }
})();
