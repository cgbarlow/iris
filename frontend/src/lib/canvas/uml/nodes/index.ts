/** Full View UML node type registry for Svelte Flow. */

import ClassNode from './ClassNode.svelte';
import ObjectNode from './ObjectNode.svelte';
import UseCaseNode from './UseCaseNode.svelte';
import StateNode from './StateNode.svelte';
import ActivityNode from './ActivityNode.svelte';
import DeploymentNode from './DeploymentNode.svelte';
import InterfaceNode from './InterfaceNode.svelte';
import EnumNode from './EnumNode.svelte';
import AbstractClassNode from './AbstractClassNode.svelte';
import UmlComponentNode from './UmlComponentNode.svelte';
import UmlPackageNode from './UmlPackageNode.svelte';

export const umlNodeTypes = {
	class: ClassNode,
	object: ObjectNode,
	use_case: UseCaseNode,
	state: StateNode,
	activity: ActivityNode,
	node: DeploymentNode,
	interface_uml: InterfaceNode,
	enumeration: EnumNode,
	abstract_class: AbstractClassNode,
	component_uml: UmlComponentNode,
	package_uml: UmlPackageNode,
} as const;
