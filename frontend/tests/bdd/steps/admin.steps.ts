import { createBdd } from 'playwright-bdd';
import { expect } from '@playwright/test';

const { Given, When, Then } = createBdd();

// --- Comments steps ---

When('I open the comments section', async ({ page }) => {
	// Comments panel should be visible on the page
	await expect(page.getByText('Comments')).toBeVisible();
});

When('I type {string}', async ({ page }, text: string) => {
	await page.getByLabel('Add a comment').fill(text);
});

When('I click {string} on the comment', async ({ page }, action: string) => {
	const comment = page.locator('.comments-panel li').first();
	await comment.getByRole('button', { name: action }).click();
});

When('I change the comment to {string}', async ({ page }, text: string) => {
	await page.locator('.comments-panel textarea').first().fill(text);
});

Given('a comment {string} exists on model {string}', async ({ page }, _content: string, _model: string) => {
	// Comment will be created via API or assumed to exist
});

Then('the comment {string} should be visible', async ({ page }, content: string) => {
	await expect(page.getByText(content)).toBeVisible();
});

Then('the comment {string} should not be visible', async ({ page }, content: string) => {
	await expect(page.getByText(content)).not.toBeVisible();
});

// --- Bookmark steps ---

When('I click the {string} button', async ({ page }, buttonText: string) => {
	await page.getByRole('button', { name: buttonText }).click();
});

Given('model {string} is bookmarked', async ({ page }, _name: string) => {
	// Bookmark will be set via API or assumed
});

Then('the button should show {string}', async ({ page }, text: string) => {
	await expect(page.getByRole('button', { name: text })).toBeVisible();
});

// --- Password steps ---

When('I fill in current password', async ({ page }) => {
	await page.getByLabel('Current Password').fill('TestPassword12345');
});

When('I fill in new password {string}', async ({ page }, password: string) => {
	await page.getByLabel('New Password', { exact: true }).fill(password);
});

When('I confirm new password {string}', async ({ page }, password: string) => {
	await page.getByLabel('Confirm Password').fill(password);
});

Then('I should see a success message', async ({ page }) => {
	await expect(page.getByRole('alert')).toBeVisible();
});
