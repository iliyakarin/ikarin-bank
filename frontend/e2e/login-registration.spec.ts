import { test, expect } from '@playwright/test';

test.describe('Auth Flow', () => {
    const randomEmail = `testuser_${Math.floor(Math.random() * 100000)}@example.com`;
    const password = 'TestPassword123!';

    test('should register and then login', async ({ page }) => {
        // 1. Registration
        await page.goto('/auth/register');

        await page.fill('input[placeholder="John"]', 'Test');
        await page.fill('input[placeholder="Doe"]', 'User');
        await page.fill('input[type="email"]', randomEmail);
        await page.fill('input[placeholder="••••••••••••••••"]', password);

        const registerButton = page.locator('button:has-text("Register Now")');
        await expect(registerButton).toBeEnabled({ timeout: 10000 });
        await registerButton.click();

        await expect(page).toHaveURL(/\/auth\/login/);

        // 2. Login
        await page.fill('input[type="email"]', randomEmail);
        await page.fill('input[type="password"]', password);

        const signInButton = page.locator('button:has-text("Sign In")');
        await expect(signInButton).toBeEnabled({ timeout: 10000 });
        await signInButton.click();

        await expect(page).toHaveURL(/\/client/);
        await expect(page.locator('text=Welcome')).toBeVisible();
    });

    test('should show custom error on human-bot verification failure', async ({ page }) => {
        await page.goto('/auth/login');
        // This test is left as a placeholder or for future mocking
    });
});
