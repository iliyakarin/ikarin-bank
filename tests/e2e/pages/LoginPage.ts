import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly registerLink: Locator;
  readonly mfaInput: Locator;
  readonly verifyMfaButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.locator('input[type="email"]');
    this.passwordInput = page.locator('input[type="password"]');
    this.loginButton = page.locator('button:has-text("Sign In")');
    this.registerLink = page.locator('a:has-text("Sign Up")');
    this.mfaInput = page.locator('input[name="mfa_code"]');
    this.verifyMfaButton = page.locator('button:has-text("Verify")');
  }

  async goto() {
    await this.page.goto('/auth/login');
  }

  async login(email: string, pass: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(pass);
    await this.loginButton.click();
  }

  async verifyMFA(code: string) {
    await this.mfaInput.fill(code);
    await this.verifyMfaButton.click();
  }
}
