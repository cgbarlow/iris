<script lang="ts">
	/**
	 * EdgeStylePanel: Per-edge metadata editor (ADR-086).
	 * Shows when an edge is selected in edit mode. Allows editing routing,
	 * cardinality, roles, and stereotype.
	 * Emits 'edgestylechange' CustomEvent with updated edge data.
	 */
	import type { EdgeRoutingType } from '$lib/types/canvas';

	interface EdgeData {
		label?: string;
		routingType?: EdgeRoutingType;
		sourceCardinality?: string;
		targetCardinality?: string;
		sourceRole?: string;
		targetRole?: string;
		stereotype?: string;
	}

	interface Props {
		edgeId: string;
		data: EdgeData;
	}

	let { edgeId, data }: Props = $props();

	let routingType = $state<EdgeRoutingType>(data.routingType ?? 'default');
	let sourceCardinality = $state(data.sourceCardinality ?? '');
	let targetCardinality = $state(data.targetCardinality ?? '');
	let sourceRole = $state(data.sourceRole ?? '');
	let targetRole = $state(data.targetRole ?? '');
	let stereotype = $state(data.stereotype ?? '');

	function emit() {
		const updated: EdgeData = {};
		if (routingType !== 'default') updated.routingType = routingType;
		if (sourceCardinality.trim()) updated.sourceCardinality = sourceCardinality.trim();
		if (targetCardinality.trim()) updated.targetCardinality = targetCardinality.trim();
		if (sourceRole.trim()) updated.sourceRole = sourceRole.trim();
		if (targetRole.trim()) updated.targetRole = targetRole.trim();
		if (stereotype.trim()) updated.stereotype = stereotype.trim();
		document.dispatchEvent(
			new CustomEvent('edgestylechange', { detail: { edgeId, data: updated } }),
		);
	}
</script>

<div class="rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
	<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Edge Properties</h4>
	<div class="flex flex-col gap-2">
		<label class="text-xs" style="color: var(--color-fg)">
			Routing
			<select bind:value={routingType} onchange={emit} class="mt-1 block w-full rounded border px-2 py-1 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
				<option value="default">Default</option>
				<option value="straight">Straight</option>
				<option value="step">Step</option>
				<option value="smoothstep">Smooth Step</option>
				<option value="bezier">Bezier</option>
			</select>
		</label>
		<div class="grid grid-cols-2 gap-2">
			<label class="text-xs" style="color: var(--color-fg)">
				Source Cardinality
				<input type="text" bind:value={sourceCardinality} onchange={emit} placeholder="e.g. 0..*" class="mt-1 block w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
			</label>
			<label class="text-xs" style="color: var(--color-fg)">
				Target Cardinality
				<input type="text" bind:value={targetCardinality} onchange={emit} placeholder="e.g. 1" class="mt-1 block w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
			</label>
			<label class="text-xs" style="color: var(--color-fg)">
				Source Role
				<input type="text" bind:value={sourceRole} onchange={emit} placeholder="e.g. +owner" class="mt-1 block w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
			</label>
			<label class="text-xs" style="color: var(--color-fg)">
				Target Role
				<input type="text" bind:value={targetRole} onchange={emit} placeholder="e.g. +items" class="mt-1 block w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
			</label>
		</div>
		<label class="text-xs" style="color: var(--color-fg)">
			Stereotype
			<input type="text" bind:value={stereotype} onchange={emit} placeholder="e.g. create" class="mt-1 block w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
		</label>
	</div>
</div>
