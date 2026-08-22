import { test, expect } from '@playwright/test';
import { TransferPage } from '../pages/TransferPage';
import { LoginPage } from '../pages/LoginPage';

test.describe('P2P Transfer Flow', () => {
  let transferPage: TransferPage;
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    transferPage = new TransferPage(page);

    // Login first
    await loginPage.goto();
    await loginPage.login('testuser@karinbank.com', 'TestPass123!');
    
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });
    await transferPage.goto();
  });

  test('User can perform a successful P2P transfer', async ({ page }) => {
    const amount = "10.00";
    const recipient = 'recipient@karinbank.com';
    
    // 1. Initiate Transfer
    await transferPage.initiateTransfer(recipient, amount, "Test P2P Transfer");
    
    // 2. Verify Success notification
    await expect(transferPage.successMessage).toBeVisible({ timeout: 15000 });
    
    // 3. Audit Check on Transactions page
    await page.goto('/client/transactions');
    await expect(page.locator(`text=${recipient}`).first()).toBeVisible({ timeout: 10000 });
  });

  test('Transfer should fail if insufficient funds', async ({ page }) => {
    const recipient = 'recipient@karinbank.com';
    await transferPage.initiateTransfer(recipient, "99999999.00", "Broke transfer");
    await expect(transferPage.errorMessage).toBeVisible({ timeout: 15000 });
  });
});
