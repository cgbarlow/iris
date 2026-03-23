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

<div class="rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
	<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Linked Diagram</h4>

	{#if loading}
		<p class="text-xs" style="color: var(--color-muted)">Loading...</p>
	{:else if linkedModelId && (linkedName || notFound)}
		<div class="flex items-center gap-1.5">
			<span class="flex-1 truncate text-xs" style="color: var(--color-fg)" title={linkedName ?? linkedModelId}>
				{linkedName ?? 'Diagram not found'}
			</span>
			<button
				onclick={() => (showPicker = true)}
				class="shrink-0 rounded border px-2 py-0.5 text-xs"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>Change</button>
			<button
				onclick={handleClear}
				title="Remove link"
				class="shrink-0 px-1 text-sm leading-none"
				style="color: var(--color-muted); background: none; border: none; cursor: pointer"
			>&times;</button>
		</div>
	{:else}
		<button
			onclick={() => (showPicker = true)}
			class="w-full rounded border py-1 text-xs"
			style="border-color: var(--color-border); border-style: dashed; background: none; color: var(--color-primary); cursor: pointer"
		>Link Diagram</button>
	{/if}
</div>

<DiagramPicker
	open={showPicker}
	onselect={handleSelect}
	oncancel={() => (showPicker = false)}
	excludeDiagramId={excludeDiagramId}
	title="Link to Diagram"
/>
