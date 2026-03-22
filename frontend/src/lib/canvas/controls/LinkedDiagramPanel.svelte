<script lang="ts">
	/**
	 * LinkedDiagramPanel: Set, change, or clear the linked diagram for a canvas node.
	 * Appears in the edit sidebar alongside ElementEditPanel and NodeStylePanel.
	 * Dispatches 'nodedatachange' CustomEvent to update node.data.linkedModelId.
	 */
	import { apiFetch } from '$lib/utils/api';
	import DiagramPicker from '$lib/components/DiagramPicker.svelte';
	import type { Diagram } from '$lib/types/api';

	interface Props {
		nodeId: string;
		linkedModelId?: string | null;
		excludeDiagramId?: string;
	}

	let { nodeId, linkedModelId, excludeDiagramId }: Props = $props();

	let showPicker = $state(false);
	let linkedName = $state<string | null>(null);
	let loading = $state(false);
	let notFound = $state(false);

	$effect(() => {
		if (linkedModelId) {
			loading = true;
			notFound = false;
			apiFetch<Diagram>(`/api/diagrams/${linkedModelId}`)
				.then((d) => {
					linkedName = d.name;
					loading = false;
				})
				.catch(() => {
					linkedName = null;
					notFound = true;
					loading = false;
				});
		} else {
			linkedName = null;
			notFound = false;
		}
	});

	function handleSelect(diagram: Diagram) {
		showPicker = false;
		document.dispatchEvent(
			new CustomEvent('nodedatachange', {
				detail: { nodeId, field: 'linkedModelId', value: diagram.id },
			})
		);
	}

	function handleClear() {
		document.dispatchEvent(
			new CustomEvent('nodedatachange', {
				detail: { nodeId, field: 'linkedModelId', value: undefined },
			})
		);
	}
</script>

<div class="linked-diagram-panel">
	<h4 class="panel-heading">Linked Diagram</h4>

	{#if loading}
		<p class="panel-text muted">Loading...</p>
	{:else if linkedModelId && (linkedName || notFound)}
		<div class="linked-row">
			<span class="linked-name" title={linkedName ?? linkedModelId}>
				{linkedName ?? 'Diagram not found'}
			</span>
			<button class="btn-sm" onclick={() => (showPicker = true)}>Change</button>
			<button class="btn-clear" onclick={handleClear} title="Remove link">&times;</button>
		</div>
	{:else}
		<button class="btn-link" onclick={() => (showPicker = true)}>Link Diagram</button>
	{/if}
</div>

<DiagramPicker
	open={showPicker}
	onselect={handleSelect}
	oncancel={() => (showPicker = false)}
	excludeDiagramId={excludeDiagramId}
	title="Link to Diagram"
/>

<style>
	.linked-diagram-panel {
		padding: 12px;
		border-top: 1px solid var(--color-border);
	}
	.panel-heading {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-muted);
		margin: 0 0 8px 0;
	}
	.panel-text.muted {
		font-size: 0.8rem;
		color: var(--color-muted);
		margin: 0;
	}
	.linked-row {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.linked-name {
		flex: 1;
		font-size: 0.8rem;
		color: var(--color-fg);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.btn-sm {
		padding: 2px 8px;
		font-size: 0.7rem;
		border: 1px solid var(--color-border);
		border-radius: 4px;
		background: var(--color-surface);
		color: var(--color-fg);
		cursor: pointer;
		flex-shrink: 0;
	}
	.btn-sm:hover {
		background: var(--color-bg);
	}
	.btn-clear {
		padding: 2px 6px;
		font-size: 0.9rem;
		line-height: 1;
		border: none;
		background: none;
		color: var(--color-muted);
		cursor: pointer;
		flex-shrink: 0;
	}
	.btn-clear:hover {
		color: var(--color-danger, #dc2626);
	}
	.btn-link {
		padding: 4px 12px;
		font-size: 0.8rem;
		border: 1px dashed var(--color-border);
		border-radius: 4px;
		background: none;
		color: var(--color-primary);
		cursor: pointer;
		width: 100%;
	}
	.btn-link:hover {
		background: var(--color-surface);
	}
</style>
