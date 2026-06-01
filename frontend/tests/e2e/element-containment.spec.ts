/**
 * E2E for ADR-231 — element → element containment (nested elements).
 *
 * Seeds a 3-level capability tree (zone → capability → sub-capability) via
 * the API using the new ``parent_element_id`` axis, then verifies the
 * element detail page renders the "Parent element" link and the "Child
 * elements" list — the browse half of the v1 feature.
 */

import { expect, test } from '@playwright/test';

import {
	createElement,
	createSet,
	getAuthToken,
	loginAsAdmin,
	seedAdmin,
} from './fixtures';

test.describe('Element containment (ADR-231)', () => {
	let zoneId: string;
	let capId: string;
	let subId: string;

	test.beforeAll(async ({ baseURL }) => {
		await seedAdmin(baseURL);
		const token = await getAuthToken(baseURL);
		const set = await createSet(baseURL, token, { name: `Containment ${Date.now()}` });
		const setId = set.id as string;

		zoneId = (await createElement(baseURL, token, {
			name: 'Customer Service Delivery capability zone',
			element_type: 'capability', set_id: setId,
		})).id as string;
		capId = (await createElement(baseURL, token, {
			name: 'Case Management', element_type: 'capability', set_id: setId,
			parent_element_id: zoneId,
		})).id as string;
		subId = (await createElement(baseURL, token, {
			name: 'Triage', element_type: 'capability', set_id: setId,
			parent_element_id: capId,
		})).id as string;
	});

	test('element detail shows child elements and the parent link', async ({ page }) => {
		await loginAsAdmin(page);

		// Zone: has the capability as a child, no parent.
		await page.goto(`/elements/${zoneId}`);
		await expect(page.getByRole('heading', { name: 'Child elements (1)' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Case Management' })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Parent element' })).toHaveCount(0);

		// Capability: parent = zone, child = sub-capability.
		await page.goto(`/elements/${capId}`);
		await expect(page.getByRole('heading', { name: 'Parent element' })).toBeVisible();
		await expect(
			page.getByRole('link', { name: 'Customer Service Delivery capability zone' }),
		).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Child elements (1)' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Triage' })).toBeVisible();

		// Sub-capability: leaf — parent = capability, no children.
		await page.goto(`/elements/${subId}`);
		await expect(page.getByRole('heading', { name: 'Parent element' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Case Management' })).toBeVisible();
		await expect(page.getByRole('heading', { name: /Child elements/ })).toHaveCount(0);
	});
});
