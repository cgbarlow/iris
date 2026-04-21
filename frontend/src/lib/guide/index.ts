/**
 * User-guide content registry (SPEC-122-A, expanded in v4.2.0).
 *
 * Each section's markdown is imported via Vite's `?raw` query so Svelte
 * renders it at runtime through `marked` + DOMPurify (protocol #7).
 * Order here drives the in-guide nav bar and the next/previous
 * navigation at the foot of each section.
 *
 * Sections flow: orientation → content surfaces → authoring →
 * discovery → references. Sign-in-only material is inline within the
 * relevant section so anonymous visitors can still discover what's
 * possible behind login.
 */

import gettingStarted from './getting-started.md?raw';
import dashboard from './dashboard.md?raw';
import collectionsSets from './collections-sets.md?raw';
import packagesDiagrams from './packages-diagrams.md?raw';
import canvasEditing from './canvas-editing.md?raw';
import notations from './notations.md?raw';
import comments from './comments.md?raw';
import knowledgeGraph from './knowledge-graph.md?raw';
import search from './search.md?raw';
import askAi from './ask-ai.md?raw';
import bookmarks from './bookmarks.md?raw';
import importsData from './imports-data.md?raw';
import roadmapScenia from './roadmap-scenia.md?raw';
import themesAccessibility from './themes-accessibility.md?raw';
import keyboardShortcuts from './keyboard-shortcuts.md?raw';
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
	{ slug: 'canvas-editing', title: 'Canvas Editing', markdown: canvasEditing },
	{ slug: 'notations', title: 'Notations', markdown: notations },
	{ slug: 'comments', title: 'Comments', markdown: comments },
	{ slug: 'knowledge-graph', title: 'Knowledge Graph', markdown: knowledgeGraph },
	{ slug: 'search', title: 'Search', markdown: search },
	{ slug: 'ask-ai', title: 'Ask AI', markdown: askAi },
	{ slug: 'bookmarks', title: 'Bookmarks', markdown: bookmarks },
	{ slug: 'imports-data', title: 'Imports & Data', markdown: importsData },
	{ slug: 'roadmap-scenia', title: 'Roadmap (Scenia)', markdown: roadmapScenia },
	{ slug: 'themes-accessibility', title: 'Themes & Accessibility', markdown: themesAccessibility },
	{ slug: 'keyboard-shortcuts', title: 'Keyboard Shortcuts', markdown: keyboardShortcuts },
	{ slug: 'admin', title: 'Admin & Permissions', markdown: admin },
];

export const GUIDE_BY_SLUG: Record<string, GuideSection> = Object.fromEntries(
	GUIDE_SECTIONS.map((s) => [s.slug, s]),
);

export const DEFAULT_SECTION = GUIDE_SECTIONS[0].slug;
