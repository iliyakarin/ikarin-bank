import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Authorization & Registration Flow', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('User can fill all registration fields without resetting and register successfully', async ({ page }) => {
    // 1. Navigate to registration
    await loginPage.registerLink.click();
    await expect(page).toHaveURL('/auth/register');

    const testEmail = `qa_user_${Date.now()}@example.com`;
    const testPassword = 'Password123!';

    // 2. Fill registration fields sequentially
    const firstNameInput = page.locator('input[placeholder="John"]');
    const lastNameInput = page.locator('input[placeholder="Doe"]');
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[placeholder="••••••••••••••••"]');
    const registerButton = page.locator('button[type="submit"]');

    await firstNameInput.fill('Iliya');
    // Verify first name is populated
    expect(await firstNameInput.inputValue()).toBe('Iliya');

    await lastNameInput.fill('Karin');
    // Verify first name is NOT reset after typing last name
    expect(await firstNameInput.inputValue()).toBe('Iliya');
    expect(await lastNameInput.inputValue()).toBe('Karin');

    await emailInput.fill(testEmail);
    // Verify first and last names are NOT reset after typing email
    expect(await firstNameInput.inputValue()).toBe('Iliya');
    expect(await lastNameInput.inputValue()).toBe('Karin');
    expect(await emailInput.inputValue()).toBe(testEmail);

    await passwordInput.fill(testPassword);
    // Verify all fields remain intact
    expect(await firstNameInput.inputValue()).toBe('Iliya');
    expect(await lastNameInput.inputValue()).toBe('Karin');
    expect(await emailInput.inputValue()).toBe(testEmail);
    expect(await passwordInput.inputValue()).toBe(testPassword);

    // 3. Register button should be enabled (once captcha auto-resolves on IP/local)
    await page.waitForTimeout(500);
    await expect(registerButton).toBeEnabled();
    await registerButton.click();

    // 4. Redirects to login
    await expect(page).toHaveURL('/auth/login', { timeout: 15000 });

    // 5. Login with newly created credentials
    await loginPage.login(testEmail, testPassword);
    await expect(page).toHaveURL(/.*client/, { timeout: 15000 });
  });

  test('Login should fail with invalid credentials', async ({ page }) => {
    await loginPage.login('invalid@example.com', 'wrongpassword');
    await expect(page.locator('text=Invalid email or password')).toBeVisible();
  });
});
