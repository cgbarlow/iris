/**
 * Shared helpers for Playwright E2E tests.
 *
 * Each helper interacts with the Iris backend API or the login page
 * to seed data and authenticate before tests run.
 */

import type { Page } from '@playwright/test';

const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'TestPassword12345';

const API_BASE = 'http://localhost:8000';

/** Sleep helper for rate-limit back-off. */
function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Wrapper around fetch that retries on HTTP 429 (rate limit) with exponential back-off.
 */
async function fetchWithRetry(
	url: string,
	init: RequestInit,
	maxRetries = 5,
): Promise<Response> {
	let res: Response | undefined;
	for (let attempt = 0; attempt <= maxRetries; attempt++) {
		res = await fetch(url, init);
		if (res.status !== 429) return res;
		const delay = Math.min(1000 * 2 ** attempt, 15_000);
		await sleep(delay);
	}
	return res!;
}

/**
 * Create the initial admin user via POST /api/auth/setup.
 * This is idempotent — if setup was already completed (HTTP 400), it is silently ignored.
 */
export async function seedAdmin(baseURL?: string): Promise<void> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/auth/setup`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username: ADMIN_USERNAME, password: ADMIN_PASSWORD }),
	});
	// 200 = created, 400 = already exists — both are fine
	if (!res.ok && res.status !== 400) {
		throw new Error(`seedAdmin failed: ${res.status} ${await res.text()}`);
	}
}

/**
 * Obtain a JWT access token for the given credentials.
 */
export async function getAuthToken(
	baseURL?: string,
	username = ADMIN_USERNAME,
	password = ADMIN_PASSWORD,
): Promise<string> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/auth/login`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username, password }),
	});
	if (!res.ok) {
		throw new Error(`getAuthToken failed: ${res.status} ${await res.text()}`);
	}
	const body = await res.json();
	return body.access_token as string;
}

/**
 * Fill the login form on the /login page and submit it, then wait for
 * navigation to the dashboard (/).
 */
export async function loginAsAdmin(page: Page): Promise<void> {
	await page.goto('/login');
	await page.getByLabel('Username').fill(ADMIN_USERNAME);
	await page.getByLabel('Password').fill(ADMIN_PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await page.waitForURL('/', { timeout: 15_000 });
	await page.getByRole('heading', { name: 'Dashboard' }).waitFor({ timeout: 10_000 });
}

/**
 * Create an entity via the API and return the response body.
 */
export async function createEntity(
	baseURL: string | undefined,
	token: string,
	data: {
		name: string;
		entity_type: string;
		description?: string;
		data?: Record<string, unknown>;
	},
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/entities`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			entity_type: data.entity_type,
			name: data.name,
			description: data.description ?? '',
			data: data.data ?? {},
		}),
	});
	if (!res.ok) {
		throw new Error(`createEntity failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Create an element via POST /api/elements and return the response body.
 * (The element domain is `/api/elements` with `element_type`; the older
 * `createEntity` helper targets a route that no longer exists.)
 */
export async function createElement(
	baseURL: string | undefined,
	token: string,
	data: {
		name: string;
		element_type: string;
		description?: string;
		data?: Record<string, unknown>;
		set_id?: string;
		package_id?: string;
		notation?: string;
		metadata?: Record<string, unknown>;
	},
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/elements`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			element_type: data.element_type,
			name: data.name,
			description: data.description ?? '',
			data: data.data ?? {},
			set_id: data.set_id ?? null,
			package_id: data.package_id ?? null,
			notation: data.notation ?? 'simple',
			metadata: data.metadata ?? null,
		}),
	});
	if (!res.ok) {
		throw new Error(`createElement failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Create a model via the API and return the response body.
 */
export async function createModel(
	baseURL: string | undefined,
	token: string,
	data: {
		name: string;
		model_type: string;
		description?: string;
		data?: Record<string, unknown>;
	},
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/models`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			model_type: data.model_type,
			name: data.name,
			description: data.description ?? '',
			data: data.data ?? {},
		}),
	});
	if (!res.ok) {
		throw new Error(`createModel failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Create a collection via the API and return the response body.
 */
export async function createCollection(
	baseURL: string | undefined,
	token: string,
	data: { name: string; description?: string },
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/collections`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			name: data.name,
			description: data.description ?? '',
		}),
	});
	if (!res.ok) {
		throw new Error(`createCollection failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Create a set via the API and return the response body.
 */
export async function createSet(
	baseURL: string | undefined,
	token: string,
	data: { name: string; description?: string; collection_id?: string },
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/sets`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			name: data.name,
			description: data.description ?? '',
			collection_id: data.collection_id ?? null,
		}),
	});
	if (!res.ok) {
		throw new Error(`createSet failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Create a diagram via the API and return the response body.
 */
export async function createDiagram(
	baseURL: string | undefined,
	token: string,
	data: {
		diagram_type: string;
		notation: string;
		name: string;
		description?: string;
		data?: Record<string, unknown>;
		set_id?: string;
		parent_package_id?: string;
		metadata?: Record<string, unknown>;
	},
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/diagrams`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			diagram_type: data.diagram_type,
			notation: data.notation,
			name: data.name,
			description: data.description ?? '',
			data: data.data ?? {},
			set_id: data.set_id ?? null,
			parent_package_id: data.parent_package_id ?? null,
			metadata: data.metadata ?? null,
		}),
	});
	if (!res.ok) {
		throw new Error(`createDiagram failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Create a package via the API and return the response body.
 */
export async function createPackage(
	baseURL: string | undefined,
	token: string,
	data: {
		name: string;
		set_id: string;
		parent_package_id?: string;
		description?: string;
	},
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/packages`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			name: data.name,
			description: data.description ?? '',
			set_id: data.set_id,
			parent_package_id: data.parent_package_id ?? null,
		}),
	});
	if (!res.ok) {
		throw new Error(`createPackage failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Create a relationship via the API and return the response body.
 */
export async function createRelationship(
	baseURL: string | undefined,
	token: string,
	data: {
		source_entity_id: string;
		target_entity_id: string;
		relationship_type: string;
		label?: string;
		description?: string;
		data?: Record<string, unknown>;
	},
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/relationships`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			source_entity_id: data.source_entity_id,
			target_entity_id: data.target_entity_id,
			relationship_type: data.relationship_type,
			label: data.label ?? null,
			description: data.description ?? '',
			data: data.data ?? {},
		}),
	});
	if (!res.ok) {
		throw new Error(`createRelationship failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Create a user via the admin API.
 * Requires an admin token. Silently ignores 409 (user already exists).
 */
export async function createUser(
	token: string,
	data: { username: string; password: string; role?: string },
	baseURL?: string,
): Promise<Record<string, unknown>> {
	const origin = baseURL ?? API_BASE;
	const res = await fetchWithRetry(`${origin}/api/users`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			username: data.username,
			password: data.password,
			role: data.role ?? 'viewer',
		}),
	});
	// 201 = created, 409 = already exists — both are fine
	if (!res.ok && res.status !== 409) {
		throw new Error(`createUser failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as Record<string, unknown>;
}

/**
 * Fill the login form and submit it with arbitrary credentials.
 */
export async function loginAs(page: Page, username: string, password: string): Promise<void> {
	await page.goto('/login');
	await page.getByLabel('Username').fill(username);
	await page.getByLabel('Password').fill(password);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await page.waitForURL('/', { timeout: 15_000 });
	await page.getByRole('heading', { name: 'Dashboard' }).waitFor({ timeout: 10_000 });
}

export { ADMIN_USERNAME, ADMIN_PASSWORD };

// v5.5.0 (issue #46/#37 reopen): the UAT verification harness signs in as a
// dedicated tester account that already exists on iris-uat.chrisbarlow.nz.
// These are sandbox credentials for the UAT site only — same convention as
// the admin constants above.
export const TESTER_USERNAME = 'tester@test.local';
export const TESTER_PASSWORD = 'riddlemetest863!';

/**
 * Sign in as the dedicated UAT tester account, then wait for the dashboard.
 * Mirrors {@link loginAsAdmin} but for the UAT-targeted Playwright project.
 */
export async function loginAsTester(page: Page): Promise<void> {
	await page.goto('/login');
	await page.getByLabel('Username').fill(TESTER_USERNAME);
	await page.getByLabel('Password').fill(TESTER_PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await page.waitForURL('/', { timeout: 30_000 });
	await page.getByRole('heading', { name: 'Dashboard' }).waitFor({ timeout: 15_000 });
}
