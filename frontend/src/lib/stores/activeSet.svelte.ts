/** Active set store using Svelte 5 runes — persisted in sessionStorage so the selected set filter survives navigation. */

const STORAGE_KEY = 'iris-active-set';

interface StoredActiveSet {
	id: string;
	name: string;
}

function loadFromSession(): StoredActiveSet | null {
	if (typeof sessionStorage === 'undefined') return null;
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		return JSON.parse(raw) as StoredActiveSet;
	} catch {
		return null;
	}
}

function saveToSession(data: StoredActiveSet | null): void {
	if (typeof sessionStorage === 'undefined') return;
	if (data && data.id) {
		sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
	} else {
		sessionStorage.removeItem(STORAGE_KEY);
	}
}

const initial = loadFromSession();

let activeSetId = $state<string>(initial?.id ?? '');
let activeSetName = $state<string>(initial?.name ?? '');

export function getActiveSetId(): string {
	return activeSetId;
}

export function getActiveSetName(): string {
	return activeSetName;
}

export function setActiveSet(id: string, name: string): void {
	activeSetId = id;
	activeSetName = name;
	saveToSession({ id, name });
}

export function clearActiveSet(): void {
	activeSetId = '';
	activeSetName = '';
	saveToSession(null);
}
