import { createBdd } from 'playwright-bdd';
import { expect } from '@playwright/test';

const { When, Then } = createBdd();

When('I change the name to {string}', async ({ page }, newName: string) => {
	await page.getByLabel('Name').clear();
	await page.getByLabel('Name').fill(newName);
});

When('I confirm deletion', async ({ page }) => {
	await page.getByRole('button', { name: 'Delete' }).last().click();
});

Then('{string} should appear in the entity list', async ({ page }, name: string) => {
	await expect(page.getByText(name)).toBeVisible();
});

Then('the entity name should be {string}', async ({ page }, name: string) => {
	await expect(page.getByRole('heading', { name })).toBeVisible();
});
