import { Page, Locator, expect } from '@playwright/test';

export class TransferPage {
  readonly page: Page;
  readonly recipientInput: Locator;
  readonly amountInput: Locator;
  readonly descriptionInput: Locator;
  readonly sendButton: Locator;
  readonly confirmationModal: Locator;
  readonly confirmButton: Locator;
  readonly successMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.recipientInput = page.locator('input[type="email"]');
    this.amountInput = page.locator('input[type="number"]');
    this.descriptionInput = page.locator('textarea[placeholder="What is this for?"]');
    this.sendButton = page.locator('button:has-text("Send Instantly")');
    this.confirmationModal = page.locator('h3:has-text("Confirm Instant Transfer")');
    this.confirmButton = page.locator('button:has-text("Send Now")');
    this.successMessage = page.locator('text=Transaction ID:');
  }

  async goto() {
    await this.page.goto('/client/send');
  }

  async initiateTransfer(recipient: string, amount: string, desc: string) {
    await this.recipientInput.fill(recipient);
    await this.amountInput.fill(amount);
    await this.descriptionInput.fill(desc);
    await this.sendButton.click();
  }

  async confirmTransfer() {
    await this.confirmButton.click();
  }
}
