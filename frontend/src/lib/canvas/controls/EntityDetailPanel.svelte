<script lang="ts">
	/** Side panel showing entity details when selected in browse mode. */
	import type { CanvasNodeData } from '$lib/types/canvas';
	import { apiFetch } from '$lib/utils/api';
	import type { EntityModelRef } from '$lib/types/api';

	interface Props {
		entity: CanvasNodeData | null;
		onclose: () => void;
		currentModelId?: string;
	}

	let { entity, onclose, currentModelId }: Props = $props();

	let usedInModels = $state<EntityModelRef[]>([]);
	let modelsLoading = $state(false);

	$effect(() => {
		if (entity?.entityId) {
			loadModels(entity.entityId);
		} else {
			usedInModels = [];
		}
	});

	async function loadModels(entityId: string) {
		modelsLoading = true;
		try {
			usedInModels = await apiFetch<EntityModelRef[]>(`/api/entities/${entityId}/models`);
		} catch {
			usedInModels = [];
		}
		modelsLoading = false;
	}
</script>

{#if entity}
	<aside class="entity-detail-panel" aria-label="Entity details">
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

		{#if entity.entityId}
			<div class="mt-3 flex flex-col gap-2">
				<a
					href="/entities/{entity.entityId}"
					class="block rounded px-3 py-2 text-center text-sm"
					style="border: 1px solid var(--color-primary); color: var(--color-primary)"
				>
					View Entity
				</a>

				{#if entity.linkedModelId}
					<a
						href="/models/{entity.linkedModelId}"
						class="block rounded px-3 py-2 text-center text-sm text-white"
						style="background-color: var(--color-primary)"
					>
						Open Linked Model
					</a>
				{/if}
			</div>

			<div class="mt-4">
				<h4 class="text-sm font-medium" style="color: var(--color-muted)">Used In Models</h4>
				{#if modelsLoading}
					<p class="mt-1 text-xs" style="color: var(--color-muted)">Loading...</p>
				{:else if usedInModels.length === 0}
					<p class="mt-1 text-xs" style="color: var(--color-muted)">Not used in any models.</p>
				{:else}
					<ul class="mt-1 flex flex-col gap-1">
						{#each usedInModels as model}
							<li>
								<a
									href="/models/{model.model_id}"
									class="block rounded px-2 py-1 text-sm"
									style="color: var(--color-primary)"
								>
									{model.name}
									{#if model.model_id === currentModelId}
										<span class="text-xs" style="color: var(--color-muted)">(current)</span>
									{/if}
									<span class="text-xs" style="color: var(--color-muted)">({model.model_type})</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/if}
	</aside>
{/if}
