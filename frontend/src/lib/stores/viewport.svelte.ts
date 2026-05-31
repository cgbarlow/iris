// Reactive viewport breakpoint store (ADR-229 / SPEC-229-A).
//
// Generalises the one-off `matchMedia('(min-width: 1024px)')` pattern that
// previously lived inline in routes/+page.svelte's dashboard. A single set of
// listeners is shared across every consumer via module-level $state, so reading
// `viewport.isMobile` in any component is reactive without that component
// owning its own listener.
//
// Mechanism guidance (SPEC-229-A): prefer Tailwind responsive classes
// (`md:`, `lg:`) for pure CSS layout. Reach for this store only when a
// component *prop or behaviour* must change reactively — e.g. passing
// `nodesDraggable` into SvelteFlow, choosing drawer-vs-inline nav, or toggling
// body scroll-lock.

// Breakpoints align with Tailwind v4 defaults: md = 768px, lg = 1024px.
const MOBILE_MAX = 767; // < 768px  → mobile
const DESKTOP_MIN = 1024; // ≥ 1024px → desktop; the 768–1023px band is tablet.

// SSR / prerender default: adapter-static prerenders without a window, so we
// render the desktop tree (the historical default) and reconcile on mount.
let isMobileState = $state(false);
let isDesktopState = $state(true);

/**
 * Wire up the matchMedia listeners. Call once from the root layout's $effect
 * (which only runs in the browser) and return value is the cleanup function.
 * No-ops and returns undefined when there is no usable `window.matchMedia`
 * (SSR/prerender, or a test environment that hasn't stubbed it).
 */
export function initViewport(): (() => void) | undefined {
	if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
		return undefined;
	}

	const mqMobile = window.matchMedia(`(max-width: ${MOBILE_MAX}px)`);
	const mqDesktop = window.matchMedia(`(min-width: ${DESKTOP_MIN}px)`);

	const sync = () => {
		isMobileState = mqMobile.matches;
		isDesktopState = mqDesktop.matches;
	};
	sync();

	mqMobile.addEventListener('change', sync);
	mqDesktop.addEventListener('change', sync);

	return () => {
		mqMobile.removeEventListener('change', sync);
		mqDesktop.removeEventListener('change', sync);
	};
}

/**
 * Reactive viewport flags. Exactly one of isMobile / isTablet / isDesktop is
 * true at any time. Consume via the getters so reads track the underlying
 * $state (e.g. `{#if viewport.isMobile}`).
 */
export const viewport = {
	get isMobile() {
		return isMobileState;
	},
	get isTablet() {
		return !isMobileState && !isDesktopState;
	},
	get isDesktop() {
		return isDesktopState;
	}
};
