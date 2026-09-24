// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * ADR-251: comments need sign-in (read and write), so anonymous visitors
 * must not see the comments UI or trigger comment requests — they used to
 * get a "Failed to load comments" panel from the 401.
 * (The end-to-end behaviour is covered in tests/e2e/anonymous-readonly.spec.ts.)
 */

const read = (p: string) => readFileSync(resolve(import.meta.dirname, '../../src', p), 'utf-8');
const PANEL = read('lib/components/CommentsPanel.svelte');
const VIEW = read('routes/views/[id]/+page.svelte');

describe('CommentsPanel is hidden and silent for anonymous visitors', () => {
	it('imports isAnonymous from the auth store', () => {
		expect(PANEL).toMatch(/import \{[^}]*\bisAnonymous\b[^}]*\} from '\$lib\/stores\/auth\.svelte\.js'/);
	});
	it('only renders for signed-in users', () => {
		expect(PANEL).toMatch(/const writable = \$derived\(!isAnonymous\(\) && canWrite\(collectionId\)\)/);
	});
	it('does not fetch comments when anonymous', () => {
		expect(PANEL).toMatch(/if \(targetId && !isAnonymous\(\)\) loadComments\(\)/);
	});
});

describe('Diagram view hides comment toggles for anonymous visitors', () => {
	it('derives commentsAvailable from the auth store', () => {
		expect(VIEW).toMatch(/const commentsAvailable = \$derived\(!isAnonymous\(\)\)/);
	});
	it('gates every "Toggle comments" / Comments button on commentsAvailable', () => {
		const toggles = [...VIEW.matchAll(/onclick=\{toggleCommentsSidebar\}/g)].length;
		const gated = [...VIEW.matchAll(/\{#if [^}]*commentsAvailable[^}]*\}\s*<button\s+onclick=\{toggleCommentsSidebar\}/g)].length;
		expect(toggles).toBeGreaterThan(0);
		expect(gated).toBe(toggles);
	});
	it('skips the comment-count request when anonymous', () => {
		const fn = VIEW.match(/async function loadCommentCount[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/if \(isAnonymous\(\)\)/);
	});
});
