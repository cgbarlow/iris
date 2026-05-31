import { describe, it, expect, afterEach, vi } from 'vitest';
import { initViewport, viewport } from '$lib/stores/viewport.svelte';

// Installs a fake window.matchMedia driven by a single controllable width.
// matches is computed live from the query so the same change handler covers
// both the (max-width: 767px) and (min-width: 1024px) queries the store opens.
function mockMatchMedia(initialWidth: number) {
	let width = initialWidth;
	// One registration per addEventListener call across every MediaQueryList —
	// real MQLs track listeners independently, so two queries = two listeners
	// even when the same callback is registered on both.
	const registrations: Array<() => void> = [];

	const matchesFor = (query: string) => {
		const min = query.match(/min-width:\s*(\d+)/);
		const max = query.match(/max-width:\s*(\d+)/);
		if (min) return width >= Number(min[1]);
		if (max) return width <= Number(max[1]);
		return false;
	};

	window.matchMedia = ((query: string) => ({
		media: query,
		get matches() {
			return matchesFor(query);
		},
		addEventListener: (_type: string, cb: () => void) => registrations.push(cb),
		removeEventListener: (_type: string, cb: () => void) => {
			const i = registrations.indexOf(cb);
			if (i !== -1) registrations.splice(i, 1);
		}
	})) as unknown as typeof window.matchMedia;

	return {
		resize(next: number) {
			width = next;
			[...registrations].forEach((cb) => cb());
		},
		listenerCount: () => registrations.length
	};
}

afterEach(() => {
	// @ts-expect-error — restore so a stray reference can't leak between tests
	delete window.matchMedia;
});

describe('viewport store', () => {
	it('reports mobile below 768px', () => {
		mockMatchMedia(360);
		const cleanup = initViewport();
		expect(viewport.isMobile).toBe(true);
		expect(viewport.isTablet).toBe(false);
		expect(viewport.isDesktop).toBe(false);
		cleanup?.();
	});

	it('treats the 768–1023px band as tablet', () => {
		const mm = mockMatchMedia(768);
		const cleanup = initViewport();
		expect(viewport.isTablet).toBe(true);
		expect(viewport.isMobile).toBe(false);
		expect(viewport.isDesktop).toBe(false);

		mm.resize(1023);
		expect(viewport.isTablet).toBe(true);
		cleanup?.();
	});

	it('reports desktop at 1024px and up', () => {
		mockMatchMedia(1440);
		const cleanup = initViewport();
		expect(viewport.isDesktop).toBe(true);
		expect(viewport.isMobile).toBe(false);
		expect(viewport.isTablet).toBe(false);
		cleanup?.();
	});

	it('honours the exact 767/768/1023/1024 boundaries', () => {
		const mm = mockMatchMedia(767);
		const cleanup = initViewport();
		expect(viewport.isMobile).toBe(true); // 767 → mobile

		mm.resize(768);
		expect(viewport.isTablet).toBe(true); // 768 → tablet

		mm.resize(1023);
		expect(viewport.isTablet).toBe(true); // 1023 → tablet

		mm.resize(1024);
		expect(viewport.isDesktop).toBe(true); // 1024 → desktop
		cleanup?.();
	});

	it('reacts to viewport changes after init', () => {
		const mm = mockMatchMedia(1440);
		const cleanup = initViewport();
		expect(viewport.isDesktop).toBe(true);

		mm.resize(360);
		expect(viewport.isMobile).toBe(true);
		expect(viewport.isDesktop).toBe(false);
		cleanup?.();
	});

	it('defaults to desktop and no-ops when matchMedia is unavailable (SSR)', async () => {
		// A pristine module instance — module-level $state from prior tests must
		// not leak in, since the point is the untouched SSR default.
		vi.resetModules();
		const fresh = await import('$lib/stores/viewport.svelte');
		// No mockMatchMedia installed → matchMedia is undefined this test.
		const cleanup = fresh.initViewport();
		expect(cleanup).toBeUndefined();
		expect(fresh.viewport.isDesktop).toBe(true);
		expect(fresh.viewport.isMobile).toBe(false);
		expect(fresh.viewport.isTablet).toBe(false);
	});

	it('cleanup removes both listeners', () => {
		const mm = mockMatchMedia(360);
		const cleanup = initViewport();
		expect(mm.listenerCount()).toBe(2);
		cleanup?.();
		expect(mm.listenerCount()).toBe(0);
	});
});
