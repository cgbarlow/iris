/**
 * Semantic icon search for the frontend IconPicker (ADR-091-B/C).
 *
 * TypeScript port of backend SemanticIconMatcher scoring logic.
 * Shared algorithm: weighted tokens, head-noun emphasis, synonym
 * expansion, stemming, and multi-signal scoring — ensuring the
 * same search quality in the edit-mode icon picker as during import.
 */

import type { IconTagEntry } from './iconTags';

// ── Domain-specific synonyms (mirrors backend _SYNONYMS) ──

const SYNONYMS: Record<string, string[]> = {
	stakeholder: ['person', 'actor', 'human'],
	organisation: ['organization', 'company', 'enterprise'],
	application: ['app', 'software'],
	service: ['server', 'cloud', 'api', 'cog'],
	it: ['technology', 'computer'],
	process: ['workflow', 'flow', 'automation'],
	function: ['service', 'capability', 'operation'],
	role: ['person', 'actor', 'responsibility'],
	actor: ['person', 'stakeholder', 'human'],
	gateway: ['shield', 'lock', 'security', 'firewall'],
	security: ['shield', 'lock', 'security'],
	driver: ['power', 'energy', 'motivation'],
	goal: ['target', 'objective', 'aim'],
	flow: ['workflow', 'process', 'automation'],
	landscape: ['layout', 'grid', 'overview', 'dashboard'],
	inventory: ['list', 'catalog', 'registry'],
	owner: ['person', 'user', 'responsible'],
	domain: ['boxes', 'group', 'collection', 'cluster'],
	principle: ['direction', 'guidance', 'compass'],
	requirement: ['checklist', 'requirement', 'compliance'],
	constraint: ['warning', 'caution', 'risk'],
	capability: ['component', 'building block', 'ability'],
	deliverable: ['package', 'parcel', 'box'],
	work_package: ['package', 'parcel', 'box'],
	plateau: ['milestone', 'checkpoint', 'marker'],
	gap: ['error', 'failed', 'gap'],
	assessment: ['question', 'help', 'assessment'],
	outcome: ['target', 'achievement', 'goal'],
	project: ['folder', 'project', 'plan'],
	unknown: ['question', 'help', 'unknown'],
};

const NOISE_WORDS = new Set([
	'the', 'of', 'and', 'for', 'in', 'on', 'to', 'an', 'is', 'it', 'by',
]);

interface WeightedToken {
	text: string;
	weight: number;
}

/** Minimal English stemmer: strip common plural/verb suffixes. */
function stem(word: string): string {
	if (word.length <= 3) return word;
	if (word.endsWith('ies') && word.length > 4) return word.slice(0, -3) + 'y';
	if (word.endsWith('ses') || word.endsWith('zes') || word.endsWith('xes')) return word.slice(0, -2);
	if (word.endsWith('s') && !word.endsWith('ss')) return word.slice(0, -1);
	return word;
}

/** Split text into lowercase stemmed tokens. */
function tokenize(text: string): string[] {
	if (!text) return [];
	// Remove ArchiMate prefixes
	text = text.replace(/archimate[_\s]*/gi, '');
	// Split on whitespace, underscores, hyphens, slashes
	const tokens = text.split(/[\s_\-/]+/);
	// Further split camelCase
	const expanded: string[] = [];
	for (const token of tokens) {
		const parts = token.replace(/([a-z])([A-Z])/g, '$1 $2').split(' ');
		expanded.push(...parts);
	}
	return expanded
		.filter((t) => t.length > 1 && !NOISE_WORDS.has(t.toLowerCase()))
		.map((t) => stem(t.toLowerCase()));
}

/** Build weighted tokens with head-noun emphasis (last word = 3x). */
function buildWeightedTokens(query: string): WeightedToken[] {
	const nameTokens = tokenize(query);
	if (!nameTokens.length) return [];

	const weighted: WeightedToken[] = nameTokens.map((text, i) => ({
		text,
		weight: i === nameTokens.length - 1 ? 3.0 : 1.0,
	}));

	// Expand with synonyms — synonyms inherit the source weight
	const expanded = [...weighted];
	for (const wt of weighted) {
		const syns = SYNONYMS[wt.text];
		if (syns) {
			for (const syn of syns) {
				expanded.push({ text: syn, weight: wt.weight });
			}
		}
	}
	return expanded;
}

/** Score an icon entry against weighted search tokens (mirrors backend _score). */
function scoreEntry(tokens: WeightedToken[], entry: IconTagEntry): number {
	let score = 0;
	const stemmedTags = new Set(entry.tags.map(stem));
	const tagWords = new Set<string>();
	for (const tag of entry.tags) {
		for (const word of tag.split(' ')) {
			tagWords.add(stem(word.toLowerCase()));
		}
	}
	const nameSegments = new Set(entry.name.split('-').map(stem));

	for (const { text, weight } of tokens) {
		if (stemmedTags.has(text)) {
			score += 5.0 * weight;
		} else if (tagWords.has(text)) {
			score += 3.0 * weight;
		} else if (nameSegments.has(text)) {
			score += 4.0 * weight;
		} else if (text.length >= 4) {
			for (const tag of entry.tags) {
				if (tag.includes(text)) {
					score += 0.5 * weight;
					break;
				}
			}
		}
	}
	return score;
}

export interface ScoredIcon {
	entry: IconTagEntry;
	score: number;
}

/**
 * Rank icons by semantic relevance to the search query.
 *
 * Uses the same algorithm as the backend SemanticIconMatcher:
 * tokenization, stemming, head-noun weighting, synonym expansion,
 * and multi-signal scoring against icon tags and name segments.
 *
 * Returns all icons sorted by score (highest first), with unscored
 * icons at the end in original order.
 */
export function semanticSearch(query: string, icons: IconTagEntry[]): ScoredIcon[] {
	const trimmed = query.trim();
	if (!trimmed) {
		return icons.map((entry) => ({ entry, score: 0 }));
	}

	const tokens = buildWeightedTokens(trimmed);
	if (!tokens.length) {
		return icons.map((entry) => ({ entry, score: 0 }));
	}

	const scored = icons.map((entry) => ({
		entry,
		score: scoreEntry(tokens, entry),
	}));

	// Stable sort: scored icons first (by score desc), then unscored in original order
	scored.sort((a, b) => b.score - a.score);
	return scored;
}
