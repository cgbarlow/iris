<script lang="ts">
	/** Side panel showing element details when selected in browse mode. */
	import type { CanvasNodeData } from '$lib/types/canvas';
	import { apiFetch } from '$lib/utils/api';
	import type { ElementDiagramRef } from '$lib/types/api';

	interface Props {
		entity: CanvasNodeData | null;
		onclose: () => void;
		currentDiagramId?: string;
	}

	let { entity, onclose, currentDiagramId }: Props = $props();

	let usedInDiagrams = $state<ElementDiagramRef[]>([]);
	let diagramsLoading = $state(false);

	$effect(() => {
		if (entity?.entityId) {
			loadDiagrams(entity.entityId);
		} else {
			usedInDiagrams = [];
		}
	});

	async function loadDiagrams(entityId: string) {
		diagramsLoading = true;
		try {
			usedInDiagrams = await apiFetch<ElementDiagramRef[]>(`/api/elements/${entityId}/diagrams`);
		} catch {
			usedInDiagrams = [];
		}
		diagramsLoading = false;
	}
</script>

{#if entity}
	<aside class="entity-detail-panel" aria-label="Element details">
		<div class="entity-detail-panel__header">
			<h3 class="text-lg font-bold" style="color: var(--color-fg)">{entity.label}</h3>
			<button
				onclick={onclose}
				aria-label="Close element details"
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
				<dt class="text-sm font-medium" style="color: var(--color-muted)">Element ID</dt>
				<dd class="mb-3 text-xs font-mono" style="color: var(--color-muted)">{entity.entityId}</dd>
			{/if}
		</dl>

		{#if entity.entityId}
			<div class="mt-3 flex flex-col gap-2">
				<a
					href="/elements/{entity.entityId}"
					class="block rounded px-3 py-2 text-center text-sm"
					style="border: 1px solid var(--color-primary); color: var(--color-primary)"
				>
					View Element
				</a>

				{#if entity.linkedModelId}
					<a
						href="/diagrams/{entity.linkedModelId}"
						class="block rounded px-3 py-2 text-center text-sm text-white"
						style="background-color: var(--color-primary)"
					>
						Open Linked Diagram
					</a>
				{/if}
			</div>

			<div class="mt-4">
				<h4 class="text-sm font-medium" style="color: var(--color-muted)">Used In Diagrams</h4>
				{#if diagramsLoading}
					<p class="mt-1 text-xs" style="color: var(--color-muted)">Loading...</p>
				{:else if usedInDiagrams.length === 0}
					<p class="mt-1 text-xs" style="color: var(--color-muted)">Not used in any diagrams.</p>
				{:else}
					<ul class="mt-1 flex flex-col gap-1">
						{#each usedInDiagrams as ref}
							<li>
								<a
									href="/diagrams/{ref.diagram_id}"
									class="block rounded px-2 py-1 text-sm"
									style="color: var(--color-primary)"
								>
									{ref.name}
									{#if ref.diagram_id === currentDiagramId}
										<span class="text-xs" style="color: var(--color-muted)">(current)</span>
									{/if}
									<span class="text-xs" style="color: var(--color-muted)">({ref.diagram_type})</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/if}
	</aside>
{/if}
