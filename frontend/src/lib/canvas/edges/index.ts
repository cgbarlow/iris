/** Simple View edge type registry for Svelte Flow. */

import UsesEdge from './UsesEdge.svelte';
import DependsOnEdge from './DependsOnEdge.svelte';
import ComposesEdge from './ComposesEdge.svelte';
import ImplementsEdge from './ImplementsEdge.svelte';
import ContainsEdge from './ContainsEdge.svelte';

export const simpleViewEdgeTypes = {
	uses: UsesEdge,
	depends_on: DependsOnEdge,
	composes: ComposesEdge,
	implements: ImplementsEdge,
	contains: ContainsEdge,
} as const;
