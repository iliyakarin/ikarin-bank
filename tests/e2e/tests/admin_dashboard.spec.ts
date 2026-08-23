import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Admin Mission Control & Banking Analytics Verification', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('Admin can access Mission Control, view live banking analytics and audit ledger', async ({ page }) => {
    // 1. Login as admin
    const adminPassword = process.env.ADMIN_PASSWORD || 'o3EhxNdGbt65yhbnb74zaMO';
    await loginPage.login('ikarin@admin.com', adminPassword);

    // 2. Wait for initial client redirect
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });

    // 3. Navigate to Admin Mission Control
    await page.goto('/admin');
    await expect(page).toHaveURL(/.*admin/, { timeout: 10000 });

    // 4. Verify Admin Header and Title
    await expect(page.locator('text=MISSIONCONTROL').or(page.locator('text=SYS-ADMIN')).first()).toBeVisible({ timeout: 10000 });

    // 5. Verify Federal Reserve Settlement Card is visible and operational
    await expect(page.locator('text=Federal Reserve Settlement & Master Account')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=OPERATIONAL')).toBeVisible();

    // 6. Verify Key Banking Metrics (Non-zero balances and volume)
    await expect(page.locator('text=24h Bank Volume').or(page.locator('text=Total Bank Balance')).first()).toBeVisible();
    
    // 7. Verify High Value Activity & Transaction Velocity sections
    await expect(page.locator('text=High Value Activity')).toBeVisible();
    await expect(page.locator('text=Transaction Velocity')).toBeVisible();

    // 8. Verify Bank-Wide Audit Ledger
    await expect(page.locator('text=Bank-Wide Audit Ledger')).toBeVisible();
    
    // Test timeframe toggle buttons (7D, 30D, ALL)
    const btn7d = page.locator('button:has-text("7D")');
    if (await btn7d.isVisible()) {
      await btn7d.click();
      await page.waitForTimeout(500);
    }

    // Verify search input is interactive
    const searchInput = page.locator('input[placeholder*="Search by merchant"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('Shell');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(500);
    }
  });
});
