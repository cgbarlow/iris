/** Simple View edge type registry for Svelte Flow. */

import UsesEdge from './UsesEdge.svelte';
import DependsOnEdge from './DependsOnEdge.svelte';
import ComposesEdge from './ComposesEdge.svelte';
import ImplementsEdge from './ImplementsEdge.svelte';
import ContainsEdge from './ContainsEdge.svelte';
import NoteLinkEdge from './NoteLinkEdge.svelte';
import SelfLoopEdge from './SelfLoopEdge.svelte';

export const simpleViewEdgeTypes = {
	uses: UsesEdge,
	depends_on: DependsOnEdge,
	composes: ComposesEdge,
	implements: ImplementsEdge,
	contains: ContainsEdge,
	note_link: NoteLinkEdge,
	self_loop: SelfLoopEdge,
} as const;
