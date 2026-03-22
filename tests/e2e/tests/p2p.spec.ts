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
    
    await expect(page).toHaveURL(/.*client/);
    await transferPage.goto();
  });

  test('User can perform a successful P2P transfer', async ({ page }) => {
    const amount = "100.00";
    const recipient = 'recipient@karinbank.com';
    
    // 1. Initiate Transfer
    await transferPage.initiateTransfer(recipient, amount, "Test P2P Transfer");
    
    // 2. Confirm in Modal
    await expect(transferPage.confirmationModal).toBeVisible();
    await transferPage.confirmButton.click();
    
    // 3. Verify Success
    await expect(transferPage.successMessage).toBeVisible({ timeout: 15000 });
    
    // 4. Audit Check
    await page.goto('/client/transactions');
    await expect(page.locator(`text=${recipient}`).first()).toBeVisible();
    await expect(page.locator(`text=${amount}`).first()).toBeVisible();
  });

  test('Transfer should fail if insufficient funds', async ({ page }) => {
    const recipient = 'recipient@karinbank.com'; // Use existing recipient to avoid vendor lookup timeout
    await transferPage.initiateTransfer(recipient, "999999.00", "Broke transfer");
    await transferPage.confirmButton.click();
    await expect(page.locator('text=Insufficient funds')).toBeVisible();
  });
});
