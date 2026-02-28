import { createBdd } from 'playwright-bdd';
import { expect } from '@playwright/test';
import { getAuthToken, createModel } from '../../e2e/fixtures';

const { Given, When, Then } = createBdd();

Given('models exist in the system', async () => {
	const token = await getAuthToken();
	await createModel(undefined, token, {
		name: 'Gallery Test Model',
		model_type: 'simple',
		description: 'A model for testing gallery view',
		data: {
			nodes: [
				{ id: 'n1', position: { x: 0, y: 0 }, data: { label: 'A' } },
				{ id: 'n2', position: { x: 200, y: 100 }, data: { label: 'B' } },
			],
			edges: [{ id: 'e1', source: 'n1', target: 'n2' }],
		},
	});
	await createModel(undefined, token, {
		name: 'Second Gallery Model',
		model_type: 'uml',
		description: 'Another model for gallery testing',
	});
});

When('I navigate to the models page', async ({ page }) => {
	await page.goto('/models');
	await page.getByRole('heading', { name: 'Models' }).waitFor();
});

When('I click the gallery view toggle', async ({ page }) => {
	await page.getByRole('button', { name: 'Gallery view' }).click();
});

When('I adjust the slider to maximum', async ({ page }) => {
	const slider = page.getByLabel('Card size');
	await slider.fill('400');
});

When('I navigate away and return to models', async ({ page }) => {
	await page.goto('/entities');
	await page.waitForURL('/entities');
	await page.goto('/models');
	await page.getByRole('heading', { name: 'Models' }).waitFor();
});

Then('I should see the models in list view', async ({ page }) => {
	await expect(page.locator('[data-testid="models-list"]')).toBeVisible();
});

Then('the list view toggle should be active', async ({ page }) => {
	const listBtn = page.getByRole('button', { name: 'List view' });
	await expect(listBtn).toHaveAttribute('aria-pressed', 'true');
});

Then('I should see the models as cards', async ({ page }) => {
	await expect(page.locator('[data-testid="models-gallery"]')).toBeVisible();
});

Then('the gallery view toggle should be active', async ({ page }) => {
	const galleryBtn = page.getByRole('button', { name: 'Gallery view' });
	await expect(galleryBtn).toHaveAttribute('aria-pressed', 'true');
});

Then('each card should show the model name', async ({ page }) => {
	const cards = page.locator('[data-testid="models-gallery"] a');
	const count = await cards.count();
	expect(count).toBeGreaterThan(0);
	for (let i = 0; i < count; i++) {
		await expect(cards.nth(i).locator('[data-testid="card-name"]')).toBeVisible();
	}
});

Then('each card should show the model type', async ({ page }) => {
	const cards = page.locator('[data-testid="models-gallery"] a');
	const count = await cards.count();
	expect(count).toBeGreaterThan(0);
	for (let i = 0; i < count; i++) {
		await expect(cards.nth(i).locator('[data-testid="card-type"]')).toBeVisible();
	}
});

Then('I should see the card size slider', async ({ page }) => {
	await expect(page.getByLabel('Card size')).toBeVisible();
});

Then('the cards should be larger', async ({ page }) => {
	const gallery = page.locator('[data-testid="models-gallery"]');
	const style = await gallery.getAttribute('style');
	expect(style).toContain('400px');
});

Then('I should not see the card size slider', async ({ page }) => {
	await expect(page.getByLabel('Card size')).not.toBeVisible();
});

Then('each card should show a preview thumbnail', async ({ page }) => {
	const cards = page.locator('[data-testid="models-gallery"] a');
	const count = await cards.count();
	expect(count).toBeGreaterThan(0);
	for (let i = 0; i < count; i++) {
		await expect(cards.nth(i).locator('[data-testid="model-thumbnail"]')).toBeVisible();
	}
});
