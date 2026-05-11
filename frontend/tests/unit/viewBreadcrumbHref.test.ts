/**
 * @vitest-environment jsdom
 *
 * Tests for the breadcrumb href helper used by /views/[id]/+page.svelte.
 *
 * Bug v5.7.3: ancestors were rendered as `/views/{id}` regardless of
 * type. The backend's /api/diagrams/{id}/ancestors returns objects with
 * `type: "package"` (see backend/app/diagrams/service.py:680), so the
 * link must route to `/packages/{id}`. A future-proofing branch for
 * `type === "diagram"` is also tested.
 */
import { describe, it, expect } from 'vitest';
import { viewBreadcrumbHref } from '$lib/utils/viewBreadcrumb';

describe('viewBreadcrumbHref', () => {
	it('routes package ancestors to /packages/{id}', () => {
		expect(
			viewBreadcrumbHref({ id: 'pkg-1', name: 'Part A', type: 'package' })
		).toBe('/packages/pkg-1');
	});

	it('routes diagram ancestors to /views/{id}', () => {
		expect(
			viewBreadcrumbHref({ id: 'dia-1', name: 'Some diagram', type: 'diagram' })
		).toBe('/views/dia-1');
	});

	it('falls back to /views/{id} for unknown types (defensive)', () => {
		expect(
			viewBreadcrumbHref({ id: 'x-1', name: '?', type: 'something-new' })
		).toBe('/views/x-1');
	});
});
