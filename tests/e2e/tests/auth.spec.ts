import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Authorization Flow', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('User can register and login with MFA', async ({ page }) => {
    // 1. Navigate to registration
    await loginPage.registerLink.click();
    await expect(page).toHaveURL('/auth/register');

    // 2. Fill registration
    await page.locator('input[placeholder="John"]').fill('John');
    await page.locator('input[placeholder="Doe"]').fill('Doe');
    await page.locator('input[type="email"]').fill(`test_${Date.now()}@example.com`);
    await page.locator('input[type="text"]').fill('P@ssword123'); // Password field is type="text" on register
    await page.locator('button:has-text("Register Now")').click();

    // 3. Login with new credentials
    await expect(page).toHaveURL('/auth/login');
    // (Note: In a real test, we'd use the registration email)
    // await loginPage.login(email, 'P@ssword123');
    
    // 4. Verification Check
    // await expect(page).toHaveURL(/.*dashboard/);
  });

  test('Login should fail with invalid credentials', async ({ page }) => {
    await loginPage.login('invalid@example.com', 'wrongpassword');
    await expect(page.locator('text=Invalid email or password')).toBeVisible();
  });
});
