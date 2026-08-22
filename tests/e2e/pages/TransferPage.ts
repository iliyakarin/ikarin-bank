import { Page, Locator } from '@playwright/test';

export class TransferPage {
  readonly page: Page;
  readonly recipientInput: Locator;
  readonly amountInput: Locator;
  readonly descriptionInput: Locator;
  readonly sendButton: Locator;
  readonly successMessage: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.recipientInput = page.locator('input[placeholder="name@example.com"]');
    this.amountInput = page.locator('input[placeholder="0.00"]');
    this.descriptionInput = page.locator('textarea[placeholder="What is this for?"]');
    this.sendButton = page.locator('button:has-text("Send Instantly")');
    this.successMessage = page.locator('text=Transfer initiated successfully').or(page.locator('text=Transfer completed'));
    this.errorMessage = page.locator('text=Transfer failed').or(page.locator('text=Insufficient funds')).or(page.locator('text=Error'));
  }

  async goto() {
    await this.page.goto('/client/send');
  }

  async initiateTransfer(recipient: string, amount: string, desc: string) {
    await this.recipientInput.fill(recipient);
    await this.amountInput.fill(amount);
    if (desc) {
      await this.descriptionInput.fill(desc);
    }
    await this.sendButton.click();
  }
}
