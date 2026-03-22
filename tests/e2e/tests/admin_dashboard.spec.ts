import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Admin Dashboard Verification', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('Admin should see dashboard with balance after login', async ({ page }) => {
    // 1. Login as admin
    // Note: seed_admin.py uses 'password123' as default password
    await loginPage.login('ikarin@admin.com', 'password123');

    // 2. Wait for dashboard redirection
    // Increased timeout for initial data loading
    await expect(page).toHaveURL(/.*client/, { timeout: 10000 });

    // 5. Verify balance is displayed
    // seed_admin.py seeds 1,000,000 cents = $10000.00
    // formatCurrency does not add commas
    await expect(page.locator('text=$10000.00')).toBeVisible();
  });
});
