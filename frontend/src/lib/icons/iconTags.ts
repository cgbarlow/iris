/**
 * Icon tag index for semantic matching (ADR-091-B).
 *
 * AUTO-GENERATED from Lucide metadata.
 * Run: node scripts/sync-lucide-metadata.mjs
 *
 * Maps icon names to search tags/keywords and categories. Used by:
 * - Backend SemanticIconMatcher during EA import
 * - Frontend IconPicker for search and category filtering
 */

import iconTagsJson from './iconTags.json';

export interface IconTagEntry {
	name: string;
	tags: string[];
	category: string;
}

/** All Lucide icons with their tags and categories. */
export const ICON_TAGS: IconTagEntry[] = iconTagsJson as IconTagEntry[];

/** Flat lookup: icon name → tags for quick matching. */
export const ICON_TAG_INDEX: Record<string, string[]> = Object.fromEntries(
	ICON_TAGS.map((entry) => [entry.name, entry.tags]),
);

/** All unique categories in the tag index. */
export const ICON_CATEGORIES = [...new Set(ICON_TAGS.map((e) => e.category))].sort();

/** JSON-serializable version for backend consumption. */
export function getIconTagsJSON(): string {
	return JSON.stringify(ICON_TAGS);
}
