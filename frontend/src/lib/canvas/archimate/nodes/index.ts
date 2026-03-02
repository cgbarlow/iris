/** ArchiMate node type registry — all types use the same component, differentiated by data. */

import ArchimateNode from './ArchimateNode.svelte';

export const archimateNodeTypes = {
	/* ── Business Layer ── */
	business_actor: ArchimateNode,
	business_role: ArchimateNode,
	business_process: ArchimateNode,
	business_service: ArchimateNode,
	business_object: ArchimateNode,
	business_function: ArchimateNode,
	business_interaction: ArchimateNode,
	business_event: ArchimateNode,
	business_collaboration: ArchimateNode,
	business_interface: ArchimateNode,
	/* ── Application Layer ── */
	application_component: ArchimateNode,
	application_service: ArchimateNode,
	application_interface: ArchimateNode,
	application_function: ArchimateNode,
	application_interaction: ArchimateNode,
	application_event: ArchimateNode,
	application_collaboration: ArchimateNode,
	application_process: ArchimateNode,
	/* ── Technology Layer ── */
	technology_node: ArchimateNode,
	technology_service: ArchimateNode,
	technology_interface: ArchimateNode,
	technology_function: ArchimateNode,
	technology_interaction: ArchimateNode,
	technology_event: ArchimateNode,
	technology_collaboration: ArchimateNode,
	technology_process: ArchimateNode,
	technology_artifact: ArchimateNode,
	technology_device: ArchimateNode,
	/* ── Motivation Layer ── */
	stakeholder: ArchimateNode,
	driver: ArchimateNode,
	assessment: ArchimateNode,
	goal: ArchimateNode,
	outcome: ArchimateNode,
	principle: ArchimateNode,
	requirement_archimate: ArchimateNode,
	constraint_archimate: ArchimateNode,
	/* ── Strategy Layer ── */
	resource: ArchimateNode,
	capability: ArchimateNode,
	course_of_action: ArchimateNode,
	value_stream: ArchimateNode,
	/* ── Implementation & Migration Layer ── */
	work_package: ArchimateNode,
	deliverable: ArchimateNode,
	implementation_event: ArchimateNode,
	plateau: ArchimateNode,
	gap: ArchimateNode,
} as const;
