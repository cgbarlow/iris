/**
 * User-guide content registry (SPEC-122-A).
 *
 * Each section's markdown is imported via Vite's `?raw` query so Svelte
 * renders it at runtime through `marked` + DOMPurify (protocol #7).
 * Order here drives the in-guide nav bar and the next/previous
 * navigation at the foot of each section.
 */

import gettingStarted from './getting-started.md?raw';
import dashboard from './dashboard.md?raw';
import collectionsSets from './collections-sets.md?raw';
import packagesDiagrams from './packages-diagrams.md?raw';
import knowledgeGraph from './knowledge-graph.md?raw';
import search from './search.md?raw';
import askAi from './ask-ai.md?raw';
import bookmarks from './bookmarks.md?raw';
import admin from './admin.md?raw';

export interface GuideSection {
	slug: string;
	title: string;
	markdown: string;
}

export const GUIDE_SECTIONS: GuideSection[] = [
	{ slug: 'getting-started', title: 'Getting Started', markdown: gettingStarted },
	{ slug: 'dashboard', title: 'Dashboard', markdown: dashboard },
	{ slug: 'collections-sets', title: 'Collections & Sets', markdown: collectionsSets },
	{ slug: 'packages-diagrams', title: 'Packages & Diagrams', markdown: packagesDiagrams },
	{ slug: 'knowledge-graph', title: 'Knowledge Graph', markdown: knowledgeGraph },
	{ slug: 'search', title: 'Search', markdown: search },
	{ slug: 'ask-ai', title: 'Ask AI', markdown: askAi },
	{ slug: 'bookmarks', title: 'Bookmarks', markdown: bookmarks },
	{ slug: 'admin', title: 'Admin', markdown: admin },
];

export const GUIDE_BY_SLUG: Record<string, GuideSection> = Object.fromEntries(
	GUIDE_SECTIONS.map((s) => [s.slug, s]),
);

export const DEFAULT_SECTION = GUIDE_SECTIONS[0].slug;
