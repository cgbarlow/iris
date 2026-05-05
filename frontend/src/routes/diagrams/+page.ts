import { redirect } from '@sveltejs/kit';

/** Issue #27: the diagrams browser was renamed to "Views" so Text views
 *  and Diagrams sit on the same page. Old `/diagrams?...` deep links keep
 *  working via this redirect. */
export const load = ({ url }) => {
	const target = `/views${url.search}${url.hash}`;
	redirect(308, target);
};
