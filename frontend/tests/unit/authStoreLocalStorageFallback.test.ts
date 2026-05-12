/**
 * v5.17.0 (ADR-162) — auth store falls back to localStorage when
 * sessionStorage is empty, then re-seeds sessionStorage so the
 * current tab caches the data going forward.
 *
 * Fixes the symptom where a new browser window opened from Claude's
 * pairing-page link saw the user as anonymous even when sibling tabs
 * had the auth state — sessionStorage is per-tab; localStorage is
 * shared. The store wrote to BOTH on save but only read from sessionStorage.
 *
 * Tests are pure logic on the loadFromSession contract; we keep an
 * inline copy of the helper to avoid pulling in the Svelte rune
 * runtime for a unit test. Keep in sync with
 * `frontend/src/lib/stores/auth.svelte.ts`.
 */
import { describe, it, expect, beforeEach } from 'vitest';

const STORAGE_KEY = 'iris_auth';

interface StoredAuth {
	accessToken: string;
	refreshToken: string;
	user: { id: string; username: string; role: string; is_active: boolean };
}

class MemoryStorage implements Storage {
	private store = new Map<string, string>();
	get length(): number { return this.store.size; }
	clear(): void { this.store.clear(); }
	getItem(k: string): string | null { return this.store.get(k) ?? null; }
	key(i: number): string | null { return Array.from(this.store.keys())[i] ?? null; }
	removeItem(k: string): void { this.store.delete(k); }
	setItem(k: string, v: string): void { this.store.set(k, v); }
}

// Inline copy of loadFromSession with the v5.17.0 fallback behaviour.
function loadFromSession(
	sessionStorage: Storage,
	localStorage: Storage,
): StoredAuth | null {
	try {
		let raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) {
			raw = localStorage.getItem(STORAGE_KEY);
			if (raw) sessionStorage.setItem(STORAGE_KEY, raw);
		}
		if (!raw) return null;
		return JSON.parse(raw) as StoredAuth;
	} catch {
		return null;
	}
}

describe('loadFromSession — cross-tab localStorage fallback', () => {
	let ss: MemoryStorage;
	let ls: MemoryStorage;

	beforeEach(() => {
		ss = new MemoryStorage();
		ls = new MemoryStorage();
	});

	const sample: StoredAuth = {
		accessToken: 'tok',
		refreshToken: 'ref',
		user: { id: 'u1', username: 'admin', role: 'Architect', is_active: true },
	};

	it('reads sessionStorage when present (unchanged behaviour)', () => {
		ss.setItem(STORAGE_KEY, JSON.stringify(sample));
		expect(loadFromSession(ss, ls)).toEqual(sample);
	});

	it('falls back to localStorage when sessionStorage is empty', () => {
		ls.setItem(STORAGE_KEY, JSON.stringify(sample));
		const result = loadFromSession(ss, ls);
		expect(result).toEqual(sample);
	});

	it('re-seeds sessionStorage on localStorage fallback', () => {
		ls.setItem(STORAGE_KEY, JSON.stringify(sample));
		loadFromSession(ss, ls);
		expect(ss.getItem(STORAGE_KEY)).toBe(JSON.stringify(sample));
	});

	it('returns null when both stores are empty', () => {
		expect(loadFromSession(ss, ls)).toBeNull();
	});

	it('returns null on corrupt JSON (and does not throw)', () => {
		ls.setItem(STORAGE_KEY, 'not json');
		expect(loadFromSession(ss, ls)).toBeNull();
	});
});
