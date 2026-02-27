/** Full View UML edge type registry for Svelte Flow. */

import AssociationEdge from './AssociationEdge.svelte';
import AggregationEdge from './AggregationEdge.svelte';
import CompositionEdge from './CompositionEdge.svelte';
import DependencyEdge from './DependencyEdge.svelte';
import RealizationEdge from './RealizationEdge.svelte';
import GeneralizationEdge from './GeneralizationEdge.svelte';

export const umlEdgeTypes = {
	association: AssociationEdge,
	aggregation: AggregationEdge,
	composition: CompositionEdge,
	dependency: DependencyEdge,
	realization: RealizationEdge,
	generalization: GeneralizationEdge,
} as const;
