import { createBdd } from 'playwright-bdd';
import { expect } from '@playwright/test';
import { seedAdmin, loginAsAdmin, createModel, createEntity, getAuthToken } from '../../e2e/fixtures';

const { Given, When, Then } = createBdd();

Given('I am logged in as an admin', async ({ page }) => {
	await seedAdmin();
	await loginAsAdmin(page);
});

Given('a model named {string} of type {string} exists', async ({ page }, name: string, type: string) => {
	const token = await getAuthToken();
	await createModel(undefined, token, { name, model_type: type });
});

Given('a model named {string} exists', async ({ page }, name: string) => {
	const token = await getAuthToken();
	await createModel(undefined, token, { name, model_type: 'component' });
});

Given('an entity named {string} exists', async ({ page }, name: string) => {
	const token = await getAuthToken();
	await createEntity(undefined, token, { name, entity_type: 'component' });
});

When('I navigate to model {string}', async ({ page }, name: string) => {
	await page.goto('/models');
	await page.getByRole('link', { name }).first().click();
	await page.waitForURL(/\/models\//);
});

When('I navigate to entity {string}', async ({ page }, name: string) => {
	await page.goto('/entities');
	await page.getByRole('link', { name }).first().click();
	await page.waitForURL(/\/entities\//);
});

When('I click the {string} tab', async ({ page }, tabName: string) => {
	await page.getByRole('tab', { name: tabName }).click();
});

When('I click {string}', async ({ page }, buttonText: string) => {
	await page.getByRole('button', { name: buttonText }).click();
});

When('I reload the page', async ({ page }) => {
	await page.reload();
});

When('I navigate to the models list', async ({ page }) => {
	await page.goto('/models');
});

When('I navigate to the entities list', async ({ page }) => {
	await page.goto('/entities');
});

When('I navigate to settings', async ({ page }) => {
	await page.goto('/settings');
});

Then('I should see {string}', async ({ page }, text: string) => {
	await expect(page.getByText(text)).toBeVisible();
});

Then('I should not see {string}', async ({ page }, text: string) => {
	await expect(page.getByText(text)).not.toBeVisible();
});

Then('I should be on the models list page', async ({ page }) => {
	await expect(page).toHaveURL('/models');
});

Then('I should be on the entities list page', async ({ page }) => {
	await expect(page).toHaveURL('/entities');
});
