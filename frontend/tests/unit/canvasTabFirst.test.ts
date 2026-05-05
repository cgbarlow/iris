// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 — items #9 + #10:
 *   #10 Canvas tab should appear FIRST (left-most) in the tab strip.
 *   #9  Smart-tab default for Text views: when `data.content` is non-empty
 *       the page should land on Canvas (it currently falls back to
 *       Details because the hasContent predicate only checks
 *       canvasNodes / sequence participants).
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/[id]/+page.svelte'),
	'utf-8',
);

describe('Tab order (#10) — Canvas tab is first', () => {
	it('the first role="tab" button drives activeTab = canvas', () => {
		const firstTab = PAGE.match(/role="tab"[\s\S]{0,400}?activeTab\s*=\s*['"](\w+)['"]/);
		expect(firstTab).toBeTruthy();
		expect(firstTab![1]).toBe('canvas');
	});
});

describe('Smart-tab default (#9) — Text views with content land on Canvas', () => {
	it('hasContent considers diagram.data.content for Text views', () => {
		// The smart-tab block in loadDiagram. After the fix it must include
		// a check on diagram.data?.content (markdown source) for Text.
		const block = PAGE.match(/Smart default tab[\s\S]{0,400}/)?.[0]
			?? PAGE.match(/!userSelectedTab[\s\S]{0,400}/)?.[0]
			?? '';
		expect(block).toMatch(/data\.?\?\.\s*content|data\?\.\s*content|data\.content/);
		expect(block).toMatch(/text|canvasType\s*===\s*['"]text['"]|diagram_type\s*===\s*['"]text['"]/);
	});
});
