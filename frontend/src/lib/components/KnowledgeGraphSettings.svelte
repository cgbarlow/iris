<script lang="ts">
	import type { GraphSettings } from '$lib/types/api';
	import { NODE_TYPE_LABELS, getNodeTypeColor } from '$lib/utils/graphColors';

	interface Props {
		settings: GraphSettings;
		onchange: (settings: GraphSettings) => void;
	}

	let { settings, onchange }: Props = $props();

	const EDGE_GROUPS: { label: string; items: { key: string; label: string }[] }[] = [
		{
			label: 'Containment',
			items: [
				{ key: 'collection_membership', label: 'Collection \u2192 Sets' },
				{ key: 'set_membership', label: 'Set \u2192 Contents' },
			],
		},
		{
			label: 'Package',
			items: [
				{ key: 'hierarchy', label: 'Nesting' },
				{ key: 'package_relationship', label: 'Relationships' },
			],
		},
		{
			label: 'Diagram',
			items: [
				{ key: 'diagram_element', label: 'Elements' },
				{ key: 'diagram_package', label: 'References' },
				{ key: 'diagram_link', label: 'Navigation' },
			],
		},
		{
			label: 'Element',
			items: [
				{ key: 'element_relationship', label: 'Relationships' },
			],
		},
	];

	function toggleNode(key: string) {
		const updated = { ...settings, nodes: { ...settings.nodes, [key]: !settings.nodes[key] } };
		onchange(updated);
	}

	function toggleEdge(key: string) {
		const updated = { ...settings, edges: { ...settings.edges, [key]: !settings.edges[key] } };
		onchange(updated);
	}

	function toggleGroup(group: { items: { key: string }[] }) {
		const allOn = group.items.every((i) => settings.edges[i.key] !== false);
		const newEdges = { ...settings.edges };
		for (const item of group.items) {
			newEdges[item.key] = !allOn;
		}
		onchange({ ...settings, edges: newEdges });
	}
</script>

<div
	style="position: absolute; top: 100%; right: 0; z-index: 20; margin-top: 4px; min-width: 220px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-surface); box-shadow: 0 4px 16px rgba(0,0,0,0.18); padding: 12px"
>
	<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Node Types</h4>
	{#each Object.entries(NODE_TYPE_LABELS) as [key, label]}
		<label class="mb-1 flex cursor-pointer items-center gap-2 text-sm" style="color: var(--color-fg)">
			<input type="checkbox" checked={settings.nodes[key]} onchange={() => toggleNode(key)} />
			<span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {getNodeTypeColor(key)}"></span>
			{label}
		</label>
	{/each}

	<hr class="my-2" style="border-color: var(--color-border)" />

	<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Relationship Types</h4>
	{#each EDGE_GROUPS as group}
		{@const allOn = group.items.every((i) => settings.edges[i.key] !== false)}
		{@const someOn = group.items.some((i) => settings.edges[i.key] !== false)}
		<label class="mb-0.5 flex cursor-pointer items-center gap-2 text-sm font-medium" style="color: var(--color-fg)">
			<input
				type="checkbox"
				checked={allOn}
				indeterminate={!allOn && someOn}
				onchange={() => toggleGroup(group)}
			/>
			{group.label}
		</label>
		{#each group.items as item}
			<label class="mb-0.5 flex cursor-pointer items-center gap-2 text-sm" style="color: var(--color-fg); padding-left: 20px">
				<input type="checkbox" checked={settings.edges[item.key] !== false} onchange={() => toggleEdge(item.key)} />
				{item.label}
			</label>
		{/each}
	{/each}
</div>
