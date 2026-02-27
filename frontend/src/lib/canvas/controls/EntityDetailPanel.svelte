<script lang="ts">
	/** Side panel showing entity details when selected in browse mode. */
	import type { CanvasNodeData } from '$lib/types/canvas';

	interface Props {
		entity: CanvasNodeData | null;
		onclose: () => void;
	}

	let { entity, onclose }: Props = $props();
</script>

{#if entity}
	<aside
		class="entity-detail-panel"
		aria-label="Entity details"
	>
		<div class="entity-detail-panel__header">
			<h3 class="text-lg font-bold" style="color: var(--color-fg)">{entity.label}</h3>
			<button
				onclick={onclose}
				aria-label="Close entity details"
				class="rounded px-2 py-1 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Close
			</button>
		</div>

		<dl class="entity-detail-panel__body">
			<dt class="text-sm font-medium" style="color: var(--color-muted)">Type</dt>
			<dd class="mb-3" style="color: var(--color-fg)">{entity.entityType}</dd>

			{#if entity.description}
				<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
				<dd class="mb-3" style="color: var(--color-fg)">{entity.description}</dd>
			{/if}

			{#if entity.entityId}
				<dt class="text-sm font-medium" style="color: var(--color-muted)">Entity ID</dt>
				<dd class="mb-3 text-xs font-mono" style="color: var(--color-muted)">{entity.entityId}</dd>
			{/if}
		</dl>
	</aside>
{/if}
