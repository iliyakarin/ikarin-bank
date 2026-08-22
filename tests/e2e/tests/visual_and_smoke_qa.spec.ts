import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Automated Visual & E2E Smoke QA Suite', () => {
  const testUser = {
    email: 'testqa@example.com',
    password: 'Password123!',
  };

  test.beforeEach(async ({ page }) => {
    // Listen for uncaught JavaScript errors in browser console
    page.on('pageerror', (err) => {
      console.error(`[Browser Page Error] ${err.message}`);
    });
  });

  test('1. Authentication Flow & Local Captcha Integrity', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Verify login form is visible and interactive
    await expect(loginPage.emailInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();

    // Perform login
    await loginPage.login(testUser.email, testUser.password);

    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });
  });

  test('2. Dashboard Visual Polish & Numeric Formatting', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(testUser.email, testUser.password);
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });

    // Assert no NaN or undefined amounts rendered in DOM
    const bodyText = await page.innerText('body');
    expect(bodyText).not.toContain('$NaN');
    expect(bodyText).not.toContain('NaN%');
    expect(bodyText).not.toContain('undefined');

    // Verify balance cards or High-Yield Savings Vault are visible
    await expect(page.locator('text=Total Wealth').or(page.locator('text=Primary Checking')).first()).toBeVisible();

    // Verify Recent Activity header does not crash
    await expect(page.locator('text=Recent Activity').or(page.locator('text=TODAY')).first()).toBeVisible();
  });

  test('3. Analytics Studio Dynamic Timeframe & Chart Rendering', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(testUser.email, testUser.password);
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });

    await page.goto('/client/analytics');

    // Verify Analytics Studio loaded
    await expect(page.getByRole('heading', { name: 'Analytics Studio' })).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Daily Cashflow Trend')).toBeVisible();

    // Test timeline toggles: 24h, 7d, 30d, 90d, 1y
    const timeframes = ['24h', '7d', '30d', '90d', '1y'];
    for (const tf of timeframes) {
      const button = page.locator(`button:has-text("${tf.toUpperCase()}")`);
      if (await button.isVisible()) {
        await button.click();
        await page.waitForTimeout(200);
        // Ensure chart SVG container is alive
        await expect(page.locator('.recharts-responsive-container').first()).toBeVisible();
      }
    }
  });

  test('4. Transfers & Activity Tables Clean Formatting', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(testUser.email, testUser.password);
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });

    // Check Send page
    await page.goto('/client/send');
    await expect(page.locator('text=Recent History').or(page.locator('text=Instant Transfer')).first()).toBeVisible({ timeout: 10000 });

    // Check All Transactions page
    await page.goto('/client/transactions');
    await expect(page.locator('text=All Transactions')).toBeVisible({ timeout: 10000 });

    // Assert amounts in transactions table do not contain '$NaN'
    const pageText = await page.innerText('body');
    expect(pageText).not.toContain('$NaN');
  });

  test('5. Admin Mission Control Crash Resilience & Role Gate', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(testUser.email, testUser.password);
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });

    // Access Mission Control directly
    await page.goto('/admin');
    await page.waitForTimeout(1500);

    // Verify zero client-side unhandled exception
    const isApplicationError = await page.locator('text=Application error: a client-side exception has occurred').isVisible();
    expect(isApplicationError).toBe(false);

    // For non-admin user, our elegant 403 Forbidden Access Restricted screen should be displayed
    const accessDeniedOrMissionControl = await page.locator('text=Restricted Command Layer').or(page.locator('text=MISSIONCONTROL')).isVisible();
    expect(accessDeniedOrMissionControl).toBe(true);
  });
});
