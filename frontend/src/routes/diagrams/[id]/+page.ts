import { redirect } from '@sveltejs/kit';

/** Issue #27: redirect old `/diagrams/<id>` deep links to `/views/<id>`. */
export const load = ({ params, url }) => {
	const target = `/views/${params.id}${url.search}${url.hash}`;
	redirect(308, target);
};
