import { createBdd } from 'playwright-bdd';
import { expect } from '@playwright/test';
import { getAuthToken, createModel } from '../../e2e/fixtures';

const { Given, When, Then } = createBdd();

Given('models of different types exist', async () => {
	const token = await getAuthToken();
	await createModel(undefined, token, { name: 'Simple Model', model_type: 'simple' });
	await createModel(undefined, token, { name: 'UML Diagram', model_type: 'uml' });
	await createModel(undefined, token, { name: 'ArchiMate View', model_type: 'archimate' });
});

When('I fill in model name {string}', async ({ page }, name: string) => {
	await page.getByLabel('Name').fill(name);
});

When('I select model type {string}', async ({ page }, type: string) => {
	await page.getByLabel('Model Type').selectOption({ label: type });
});

When('I change the model name to {string}', async ({ page }, newName: string) => {
	await page.getByLabel('Name').clear();
	await page.getByLabel('Name').fill(newName);
});

When('I filter by type {string}', async ({ page }, type: string) => {
	await page.getByLabel('Filter by type').selectOption({ label: type });
});

Then('{string} should appear in the model list', async ({ page }, name: string) => {
	await expect(page.getByText(name)).toBeVisible();
});

Then('only UML models should be visible', async ({ page }) => {
	const items = page.locator('a[href*="/models/"]');
	const count = await items.count();
	for (let i = 0; i < count; i++) {
		await expect(items.nth(i)).toContainText('uml');
	}
});

Then('the model name should be {string}', async ({ page }, name: string) => {
	await expect(page.getByRole('heading', { name })).toBeVisible();
});
