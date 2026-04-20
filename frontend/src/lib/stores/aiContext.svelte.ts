/** AI context store — holds items pinned from search results for use in Iris AI.
 *
 * Persisted in sessionStorage so context survives navigation but not tab close.
 * Cleared only via clearAiContext() (triggered by the Reset button on the Iris AI page).
 */

const STORAGE_KEY = 'iris-ai-context';

export interface AiContextItem {
	id: string;
	result_type: 'element' | 'diagram' | 'package' | 'set' | 'collection';
	name: string;
	set_id: string | null;
	set_name: string | null;
}

function loadFromSession(): AiContextItem[] {
	if (typeof sessionStorage === 'undefined') return [];
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return [];
		return JSON.parse(raw) as AiContextItem[];
	} catch {
		return [];
	}
}

function saveToSession(items: AiContextItem[]): void {
	if (typeof sessionStorage === 'undefined') return;
	if (items.length > 0) {
		sessionStorage.setItem(STORAGE_KEY, JSON.stringify(items));
	} else {
		sessionStorage.removeItem(STORAGE_KEY);
	}
}

let items = $state<AiContextItem[]>(loadFromSession());

export function getAiContextItems(): AiContextItem[] {
	return items;
}

export function getAiContextCount(): number {
	return items.length;
}

export function addAiContextItem(item: AiContextItem): void {
	if (items.some((i) => i.id === item.id)) return; // already added
	items = [...items, item];
	saveToSession(items);
}

export function removeAiContextItem(id: string): void {
	items = items.filter((i) => i.id !== id);
	saveToSession(items);
}

export function clearAiContext(): void {
	items = [];
	saveToSession(items);
}
