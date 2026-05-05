// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #27 — DocRef "Import failed" while the import actually
 * succeeded. Root cause: the import endpoint ran the full CSV download
 * and per-chunk INSERT inside the request thread; on Render's edge the
 * request reliably timed out after ~100s, the frontend caught it and
 * displayed "Import failed" — but the asyncio task on the backend
 * continued and committed.
 *
 * Fix: the endpoint is now fire-and-forget (HTTP 202 + asyncio.create_task)
 * and the frontend polls /documents while any document is in the
 * `importing` state.
 */

const SELECTOR = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/components/DocRefSelector.svelte'),
	'utf-8',
);
const ROUTER = readFileSync(
	resolve(import.meta.dirname, '../../../backend/app/docref/router.py'),
	'utf-8',
);

describe('DocRef async import (issue #27)', () => {
	it('frontend optimistically marks the clicked document as importing', () => {
		const m = SELECTOR.match(/async function importDocument\(doc[\s\S]*?\n\t\}/);
		expect(m).toBeTruthy();
		expect(m![0]).toMatch(/status:\s*'importing'/);
	});

	it('frontend schedules a poll while any document is still importing', () => {
		expect(SELECTOR).toMatch(/function schedulePollIfImporting\(/);
		const m = SELECTOR.match(/function schedulePollIfImporting\([\s\S]*?\n\t\}/);
		expect(m![0]).toMatch(/status\s*===\s*'importing'/);
		expect(m![0]).toMatch(/setTimeout/);
		// Picked 3 s — a full minute of polling cost is negligible vs. the 100 s
		// edge timeout we're working around.
		expect(m![0]).toMatch(/3000/);
	});

	it('frontend cleans up the poll timer on teardown', () => {
		expect(SELECTOR).toMatch(/clearTimeout\(pollTimer\)/);
	});

	it('backend returns 202 immediately and runs the import as a background task', () => {
		expect(ROUTER).toMatch(/status_code=202/);
		expect(ROUTER).toMatch(/start_import_document/);
		expect(ROUTER).toMatch(/asyncio\.create_task/);
	});
});
