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

function canMatch(): boolean {
	return typeof window !== 'undefined' && typeof window.matchMedia === 'function';
}

// Read the current breakpoint straight from matchMedia. Used both for the
// eager initial value (below) and on every change event.
function readMobile(): boolean {
	return canMatch() ? window.matchMedia(`(max-width: ${MOBILE_MAX}px)`).matches : false;
}
function readDesktop(): boolean {
	// SSR / prerender (no window): default to desktop — adapter-static
	// prerenders the desktop tree, then the browser reconciles eagerly below.
	return canMatch() ? window.matchMedia(`(min-width: ${DESKTOP_MIN}px)`).matches : true;
}

// Eager initial values: in the browser the module loads during hydration when
// `window` is available, so consumers (and toggle handlers that branch on
// `isDesktop`) see the correct breakpoint on the very first render — no flash,
// no race. Falls back to the desktop default during SSR.
let isMobileState = $state(readMobile());
let isDesktopState = $state(readDesktop());

/**
 * Wire up the matchMedia listeners. Call once from the root layout's $effect
 * (which only runs in the browser) and return value is the cleanup function.
 * No-ops and returns undefined when there is no usable `window.matchMedia`
 * (SSR/prerender, or a test environment that hasn't stubbed it).
 */
export function initViewport(): (() => void) | undefined {
	if (!canMatch()) {
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
