/**
 * Scenia adapter — replaces Scenia's db.ts with Iris API-backed storage.
 *
 * Implements the same interface Scenia's internal DB module uses:
 * - getAppData(): loads all roadmap data for the active set
 * - saveAppData(data): atomically writes all roadmap data for the active set
 *
 * This is the primary integration point between Scenia and Iris.
 */

import { API_BASE_URL } from '$lib/config.js';
import { getAuthHeaders } from './auth.js';
import { apiToScenia, sceniaToApi } from './transforms.js';
import type { SceniaBulkData } from './transforms.js';

export type { SceniaBulkData };

export class SceniaAdapter {
	private setId: string;

	constructor(setId: string) {
		this.setId = setId;
	}

	/**
	 * Load all roadmap data for the active set.
	 * Returns Scenia-native typed data (not Iris API shapes).
	 */
	async getAppData(): Promise<Record<string, unknown>> {
		const response = await fetch(
			`${API_BASE_URL}/api/scenia/data?set_id=${encodeURIComponent(this.setId)}`,
			{
				method: 'GET',
				headers: getAuthHeaders(),
			},
		);

		if (!response.ok) {
			throw new Error(`Failed to load Scenia data: ${response.status}`);
		}

		const apiData = await response.json();
		return apiToScenia(apiData) as unknown as Record<string, unknown>;
	}

	/**
	 * Save all roadmap data atomically for the active set.
	 * Accepts Scenia-native typed data, converts to Iris API shape.
	 */
	async saveAppData(data: Record<string, unknown>): Promise<void> {
		const payload = sceniaToApi(data, this.setId);

		const response = await fetch(
			`${API_BASE_URL}/api/scenia/data?set_id=${encodeURIComponent(this.setId)}`,
			{
				method: 'PUT',
				headers: getAuthHeaders(),
				body: JSON.stringify(payload),
			},
		);

		if (!response.ok) {
			throw new Error(`Failed to save Scenia data: ${response.status}`);
		}
	}

	/**
	 * Update the active set ID (e.g., when user switches sets).
	 */
	setActiveSet(setId: string): void {
		this.setId = setId;
	}

	/**
	 * Get the Iris URL for an element (for "View in Iris" links).
	 */
	getIrisUrl(elementId: string): string {
		return `/elements/${elementId}`;
	}
}

/**
 * Check if the Scenia extension is enabled.
 */
export async function isSceniaEnabled(): Promise<boolean> {
	try {
		const response = await fetch(`${API_BASE_URL}/api/extensions/scenia`, {
			headers: getAuthHeaders(),
		});
		if (!response.ok) return false;
		const data = await response.json();
		return data.is_enabled === true;
	} catch {
		return false;
	}
}
