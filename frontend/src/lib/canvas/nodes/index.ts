/** Simple View node type registry for Svelte Flow. */

import ComponentNode from './ComponentNode.svelte';
import ServiceNode from './ServiceNode.svelte';
import InterfaceNode from './InterfaceNode.svelte';
import PackageNode from './PackageNode.svelte';
import ActorNode from './ActorNode.svelte';
import DatabaseNode from './DatabaseNode.svelte';
import QueueNode from './QueueNode.svelte';
import ModelRefNode from './ModelRefNode.svelte';

export const simpleViewNodeTypes = {
	component: ComponentNode,
	service: ServiceNode,
	interface: InterfaceNode,
	package: PackageNode,
	actor: ActorNode,
	database: DatabaseNode,
	queue: QueueNode,
	modelref: ModelRefNode,
} as const;
