/** ArchiMate edge type registry — all types use the same component, differentiated by data. */

import ArchimateEdge from './ArchimateEdge.svelte';

export const archimateEdgeTypes = {
	serving: ArchimateEdge,
	flow: ArchimateEdge,
	triggering: ArchimateEdge,
	access: ArchimateEdge,
	influence: ArchimateEdge,
	archimate_realization: ArchimateEdge,
	archimate_composition: ArchimateEdge,
	archimate_aggregation: ArchimateEdge,
} as const;
