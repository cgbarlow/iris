/** Visit history store — tracks recently visited Collections, Sets, Packages, Diagrams, and Elements.
 *
 * Persisted in localStorage so history survives page refreshes.
 */

const STORAGE_KEY = 'iris-visit-history';
const MAX_ENTRIES = 200;

export interface VisitEntry {
	id: string;
	type: 'collection' | 'set' | 'package' | 'diagram' | 'element';
	name: string;
	detail?: string;
	collectionName?: string;
	setId?: string;
	setName?: string;
	packageName?: string;
	description?: string;
	href: string;
	visitedAt: string;
}

function loadFromStorage(): VisitEntry[] {
	if (typeof localStorage === 'undefined') return [];
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return [];
		return JSON.parse(raw) as VisitEntry[];
	} catch {
		return [];
	}
}

function saveToStorage(entries: VisitEntry[]): void {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
}

let entries = $state<VisitEntry[]>(loadFromStorage());

export function getVisitHistory(): VisitEntry[] {
	return entries;
}

export function recordVisit(entry: Omit<VisitEntry, 'visitedAt'>): void {
	// Remove previous visit to the same item
	const filtered = entries.filter((e) => !(e.id === entry.id && e.type === entry.type));
	// Add at the front
	entries = [{ ...entry, visitedAt: new Date().toISOString() }, ...filtered].slice(0, MAX_ENTRIES);
	saveToStorage(entries);
}

export function clearVisitHistory(): void {
	entries = [];
	saveToStorage(entries);
}
