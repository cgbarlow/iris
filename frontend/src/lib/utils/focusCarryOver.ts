/**
 * Full screen (focus mode) carry-over for /views/[id] (ADR-258).
 *
 * When the user is in full screen and follows a link or linked-diagram node
 * to another view, the next view should open in full screen too. Returns the
 * URL to navigate to instead (with `?focus=1` added), or null to let the
 * navigation proceed unchanged.
 */
const VIEW_PATH = /^\/views\/[^/]+$/;

export function focusCarryOverTarget(
	focusMode: boolean,
	from: URL,
	to: URL | null,
	type: string,
): string | null {
	if (!focusMode || !to) return null;
	if (type !== 'link' && type !== 'goto') return null;
	if (to.origin !== from.origin) return null;
	if (!VIEW_PATH.test(to.pathname) || to.pathname === from.pathname) return null;
	if (to.searchParams.get('focus') === '1') return null;
	const next = new URL(to);
	next.searchParams.set('focus', '1');
	return next.pathname + next.search + next.hash;
}
