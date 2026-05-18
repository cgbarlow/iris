import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Element clone preserves source set_id (v6.8.7, ADR-198, issue #173 item 1).
 *
 * Bug: the single-element clone button on /elements/{id} sent a
 * `POST /api/elements` body containing only `element_type`, `name`,
 * `description`, `data` — but not `set_id`. The backend's
 * `create_element` defaults to `DEFAULT_SET_ID` when `set_id` is
 * absent, so the "(Copy)" landed in the default set rather than the
 * source's set.
 *
 * (The batch-clone path at /api/batch/elements/clone is unaffected —
 * `batch_clone_elements` in the backend reads and re-inserts the
 * source's `set_id`. The bug is purely the detail-page handler.)
 *
 * Fix: include `set_id: entity.set_id` in the clone POST body.
 *
 * Static-parser style to match the rest of this suite.
 */

const src = readFileSync(
	resolve(__dirname, '../../src/routes/elements/[id]/+page.svelte'),
	'utf-8',
);

function handleCloneBody(): string {
	const start = src.indexOf('async function handleClone(');
	expect(start, 'handleClone not found').toBeGreaterThan(-1);
	const braceStart = src.indexOf('{', start);
	let depth = 0;
	let i = braceStart;
	for (; i < src.length; i++) {
		const ch = src[i];
		if (ch === '{') depth++;
		else if (ch === '}') {
			depth--;
			if (depth === 0) break;
		}
	}
	return src.slice(braceStart, i + 1);
}

describe('Element detail — handleClone preserves source set_id (#173 item 1)', () => {
	const body = handleCloneBody();

	it('still POSTs to /api/elements', () => {
		expect(body).toContain("'/api/elements'");
	});

	it('includes set_id: entity.set_id in the request body', () => {
		expect(body).toMatch(/set_id:\s*entity\.set_id/);
	});

	it('still includes the basic fields', () => {
		expect(body).toMatch(/element_type:\s*entity\.element_type/);
		expect(body).toMatch(/name:\s*`\$\{entity\.name\}\s*\(Copy\)`/);
		expect(body).toMatch(/data:\s*entity\.data/);
	});
});
