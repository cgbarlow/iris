/** Full View UML node type registry for Svelte Flow. */

import ClassNode from './ClassNode.svelte';
import ObjectNode from './ObjectNode.svelte';
import UseCaseNode from './UseCaseNode.svelte';
import StateNode from './StateNode.svelte';
import ActivityNode from './ActivityNode.svelte';
import DeploymentNode from './DeploymentNode.svelte';

export const umlNodeTypes = {
	class: ClassNode,
	object: ObjectNode,
	use_case: UseCaseNode,
	state: StateNode,
	activity: ActivityNode,
	node: DeploymentNode,
} as const;
