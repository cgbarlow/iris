/**
 * Helpers for the breadcrumb on /views/[id].
 *
 * v5.7.3: the /api/diagrams/{id}/ancestors endpoint returns objects
 * shaped as { id, name, type, parent_package_id? }. The breadcrumb
 * previously hard-coded /views/{id} for every ancestor, which broke
 * navigation because ancestors are packages (a diagram's parent chain
 * walks the packages table — see backend/app/diagrams/service.py:680).
 */

export interface BreadcrumbAncestor {
	id: string;
	name: string;
	type: string;
	parent_package_id?: string | null;
}

export function viewBreadcrumbHref(ancestor: BreadcrumbAncestor): string {
	if (ancestor.type === 'package') return `/packages/${ancestor.id}`;
	return `/views/${ancestor.id}`;
}
