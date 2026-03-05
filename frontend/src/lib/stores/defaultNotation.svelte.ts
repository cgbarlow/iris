/** Default notation user preference stored in localStorage (ADR-081). */

const STORAGE_KEY = 'iris-default-notation';

export function getDefaultNotation(): string {
	return localStorage?.getItem(STORAGE_KEY) ?? 'simple';
}

export function setDefaultNotation(value: string): void {
	localStorage?.setItem(STORAGE_KEY, value);
}
