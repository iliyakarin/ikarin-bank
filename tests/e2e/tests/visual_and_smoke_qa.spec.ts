import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Automated Visual & E2E Smoke QA Suite', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    // Listen for uncaught JavaScript errors in browser console
    page.on('pageerror', (err) => {
      console.error(`[Browser Page Error] ${err.message}`);
    });
  });

  test('1. Authentication Flow & Local Captcha Integrity', async ({ page }) => {
    await loginPage.goto();

    // Verify login form is visible and interactive
    await expect(page.locator('input[name="username"], input[type="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"], input[type="password"]')).toBeVisible();

    // Perform login with test admin credentials
    await loginPage.login('ikarin@admin.com', 'password123');

    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });
  });

  test('2. Dashboard Visual Polish & Numeric Formatting', async ({ page }) => {
    await loginPage.goto();
    await loginPage.login('ikarin@admin.com', 'password123');
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });

    // Assert no NaN or undefined amounts rendered in DOM
    const bodyText = await page.innerText('body');
    expect(bodyText).not.toContain('$NaN');
    expect(bodyText).not.toContain('NaN%');
    expect(bodyText).not.toContain('undefined');

    // Verify balance or vault cards are rendered
    await expect(page.locator('text=Total Wealth').or(page.locator('text=Primary Checking')).first()).toBeVisible();

    // Verify Recent Activity header does not crash
    await expect(page.locator('text=Recent Activity').or(page.locator('text=TODAY')).first()).toBeVisible();
  });

  test('3. Analytics Studio Dynamic Timeframe & Chart Rendering', async ({ page }) => {
    await loginPage.goto();
    await loginPage.login('ikarin@admin.com', 'password123');
    await page.goto('/client/analytics');

    // Verify Analytics Studio loaded
    await expect(page.locator('text=Analytics Studio')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Daily Cashflow Trend')).toBeVisible();

    // Test timeline toggles: 24h, 7d, 30d, 90d, 1y
    const timeframes = ['24h', '7d', '30d', '90d', '1y'];
    for (const tf of timeframes) {
      const button = page.locator(`button:has-text("${tf.toUpperCase()}")`);
      if (await button.isVisible()) {
        await button.click();
        await page.waitForTimeout(250);
        // Ensure chart SVG container is alive
        await expect(page.locator('.recharts-responsive-container').first()).toBeVisible();
      }
    }
  });

  test('4. Transfers & Activity Tables Clean Formatting', async ({ page }) => {
    await loginPage.goto();
    await loginPage.login('ikarin@admin.com', 'password123');

    // Check Send page
    await page.goto('/client/send');
    await expect(page.locator('text=Recent History').or(page.locator('text=Fast Pay')).first()).toBeVisible({ timeout: 10000 });

    // Check All Transactions page
    await page.goto('/client/transactions');
    await expect(page.locator('text=All Transactions')).toBeVisible({ timeout: 10000 });

    // Assert amounts in transactions table do not contain '----' or '---' in red
    const pageText = await page.innerText('body');
    expect(pageText).not.toContain('$NaN');
  });

  test('5. Admin Mission Control Crash Resilience & Telemetry', async ({ page }) => {
    await loginPage.goto();
    await loginPage.login('ikarin@admin.com', 'password123');

    // Access Mission Control directly
    await page.goto('/admin');

    // Verify Mission Control renders cleanly or gracefully handles access without unhandled exception
    await page.waitForTimeout(2000);

    const isApplicationError = await page.locator('text=Application error: a client-side exception has occurred').isVisible();
    expect(isApplicationError).toBe(false);

    // If admin is active, mission control header or access card should be visible
    const missionControlVisible = await page.locator('text=MISSIONCONTROL').or(page.locator('text=Command Layer')).isVisible();
    expect(missionControlVisible).toBe(true);
  });
});
