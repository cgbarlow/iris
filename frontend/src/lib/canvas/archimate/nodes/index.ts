/** ArchiMate node type registry — all 11 types use the same component, differentiated by data. */

import ArchimateNode from './ArchimateNode.svelte';

export const archimateNodeTypes = {
	business_actor: ArchimateNode,
	business_role: ArchimateNode,
	business_process: ArchimateNode,
	business_service: ArchimateNode,
	business_object: ArchimateNode,
	application_component: ArchimateNode,
	application_service: ArchimateNode,
	application_interface: ArchimateNode,
	technology_node: ArchimateNode,
	technology_service: ArchimateNode,
	technology_interface: ArchimateNode,
} as const;
