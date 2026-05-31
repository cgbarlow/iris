<script lang="ts">
	/**
	 * SPEC-212-f: drill-down picker for attribute paths (Option C).
	 *
	 * Reuses the existing /api/elements/{id}/data-tree endpoint (the same
	 * one SmartMarkdownSlashPicker uses) — the data-tree shape is the
	 * single source of truth (DRY §13). Emits a path-string like
	 * `attributes/Quantity/type`. The user picks an example element from
	 * the seeded set; the path generalises to any element matching the
	 * same template.
	 *
	 * Falls back to a plain text input when no example element is
	 * available (e.g. globals-mode authoring).
	 */

	import { apiFetch, ApiError } from '$lib/utils/api';

	type TreeKind = 'dict' | 'list_of_named' | 'list' | 'primitive' | 'empty';
	interface TreeDescriptor {
		kind: TreeKind;
		keys?: string[];
		names?: string[];
		length?: number;
		value?: string;
	}

	interface Props {
		value: string;
		exampleElementId: string | null;
		label?: string;
		placeholder?: string;
	}

	let {
		value = $bindable(''),
		exampleElementId,
		label = 'Attribute path',
		placeholder = 'e.g. attributes/Quantity/type',
	}: Props = $props();

	let drillOpen = $state(false);
	let drillPath = $state<string[]>([]);
	let drillNode = $state<TreeDescriptor | null>(null);
	let drillError = $state<string | null>(null);
	let drillLoading = $state(false);

	async function openDrill() {
		if (!exampleElementId) return;
		drillOpen = true;
		drillPath = [];
		drillError = null;
		await loadNode();
	}

	function cancelDrill() {
		drillOpen = false;
		drillError = null;
	}

	async function loadNode() {
		if (!exampleElementId) return;
		drillLoading = true;
		drillError = null;
		try {
			const pathParam = drillPath.join('/');
			const url = pathParam
				? `/api/elements/${exampleElementId}/data-tree?path=${encodeURIComponent(pathParam)}`
				: `/api/elements/${exampleElementId}/data-tree`;
			drillNode = await apiFetch<TreeDescriptor>(url);
		} catch (e) {
			drillNode = null;
			drillError = e instanceof ApiError ? e.message : 'Failed to load data tree';
		}
		drillLoading = false;
	}

	async function drillInto(segment: string) {
		drillPath = [...drillPath, segment];
		await loadNode();
	}

	async function drillUp() {
		drillPath = drillPath.slice(0, -1);
		await loadNode();
	}

	function selectCurrent() {
		value = drillPath.join('/');
		drillOpen = false;
	}

	function items(): string[] {
		if (!drillNode) return [];
		if (drillNode.kind === 'dict') return drillNode.keys ?? [];
		if (drillNode.kind === 'list_of_named') return drillNode.names ?? [];
		if (drillNode.kind === 'list') return Array.from({ length: drillNode.length ?? 0 }, (_, i) => String(i));
		return [];
	}
</script>

<div class="attr-path-picker">
	<label class="block text-sm font-medium" style="color: var(--color-fg)">
		{label}
		<div class="mt-1 flex gap-2">
			<input
				type="text"
				bind:value
				{placeholder}
				class="flex-1 rounded border px-3 py-2 font-mono text-xs"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
			{#if exampleElementId}
				<button
					type="button"
					onclick={openDrill}
					class="rounded px-3 py-1 text-xs"
					style="border: 1px solid var(--color-border); color: var(--color-fg); background: var(--color-bg)"
				>
					Pick…
				</button>
			{/if}
		</div>
	</label>

	{#if !exampleElementId}
		<p class="mt-1 text-xs" style="color: var(--color-muted)">
			Type the path manually, e.g. <code>attributes/Quantity/type</code>.
		</p>
	{/if}

	{#if drillOpen}
		<div class="mt-2 rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
			<div class="flex items-center justify-between">
				<p class="text-xs font-medium" style="color: var(--color-fg)">
					{drillPath.length === 0 ? 'Pick a field' : drillPath.join(' / ')}
				</p>
				<button
					type="button"
					onclick={cancelDrill}
					class="text-xs"
					style="color: var(--color-muted)"
				>
					Close
				</button>
			</div>
			{#if drillError}
				<p class="mt-2 text-xs" style="color: var(--color-danger)">{drillError}</p>
			{/if}
			{#if drillLoading}
				<p class="mt-2 text-xs" style="color: var(--color-muted)">Loading…</p>
			{:else if drillNode}
				{#if drillNode.kind === 'primitive'}
					<p class="mt-2 text-xs" style="color: var(--color-muted)">
						Value: <code>{drillNode.value}</code>
					</p>
					<button
						type="button"
						onclick={selectCurrent}
						class="mt-2 rounded px-2 py-1 text-xs text-white"
						style="background: var(--color-primary)"
					>
						Use this path
					</button>
				{:else if drillNode.kind === 'empty'}
					<p class="mt-2 text-xs" style="color: var(--color-muted)">No data here.</p>
				{:else}
					<div class="mt-2 flex flex-wrap gap-1">
						{#if drillPath.length > 0}
							<button
								type="button"
								onclick={drillUp}
								class="rounded px-2 py-1 text-xs"
								style="border: 1px solid var(--color-border); color: var(--color-fg); background: var(--color-bg)"
							>
								↑ up
							</button>
						{/if}
						{#each items() as item (item)}
							<button
								type="button"
								onclick={() => drillInto(item)}
								class="rounded px-2 py-1 text-xs"
								style="border: 1px solid var(--color-border); color: var(--color-fg); background: var(--color-bg)"
							>
								{item}
							</button>
						{/each}
					</div>
					{#if drillPath.length > 0}
						<button
							type="button"
							onclick={selectCurrent}
							class="mt-2 rounded px-2 py-1 text-xs text-white"
							style="background: var(--color-primary)"
						>
							Use {drillPath.join('/')}
						</button>
					{/if}
				{/if}
			{/if}
		</div>
	{/if}
</div>
