/** Active collection store using Svelte 5 runes — persisted in sessionStorage so the selected collection filter survives navigation. */

const STORAGE_KEY = 'iris-active-collection';

interface StoredActiveCollection {
	id: string;
	name: string;
}

function loadFromSession(): StoredActiveCollection | null {
	if (typeof sessionStorage === 'undefined') return null;
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		return JSON.parse(raw) as StoredActiveCollection;
	} catch {
		return null;
	}
}

function saveToSession(data: StoredActiveCollection | null): void {
	if (typeof sessionStorage === 'undefined') return;
	if (data && data.id) {
		sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
	} else {
		sessionStorage.removeItem(STORAGE_KEY);
	}
}

const initial = loadFromSession();

let activeCollectionId = $state<string>(initial?.id ?? '');
let activeCollectionName = $state<string>(initial?.name ?? '');

export function getActiveCollectionId(): string {
	return activeCollectionId;
}

export function getActiveCollectionName(): string {
	return activeCollectionName;
}

export function setActiveCollection(id: string, name: string): void {
	activeCollectionId = id;
	activeCollectionName = name;
	saveToSession({ id, name });
}

export function clearActiveCollection(): void {
	activeCollectionId = '';
	activeCollectionName = '';
	saveToSession(null);
}
