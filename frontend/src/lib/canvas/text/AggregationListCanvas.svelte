<script lang="ts">
	/**
	 * AggregationListCanvas (SPEC-213-b, v6.26.0).
	 *
	 * Edit / view canvas for the `aggregation_list` diagram type
	 * (ADR-213). Storage is minimal config (`data.source_diagram_id`
	 * + `data.profile_id`); the backend engine fills `data.content`
	 * at GET time.
	 *
	 * View mode: renders `content` via MarkdownView (same as
	 * smart_markdown / dynamic_list).
	 * Edit mode: shows pickers for source-diagram and profile.
	 */
	import { onMount } from 'svelte';
	import MarkdownView from '$lib/components/MarkdownView.svelte';
	import { apiFetch } from '$lib/utils/api';
	import type { TocHeading } from '$lib/components/markdownHelpers';

	interface DiagramRow {
		id: string;
		name: string;
		diagram_type: string;
	}
	interface ProfileRow {
		id: string;
		name: string;
		is_global: boolean;
		set_id: string | null;
	}

	interface AggregationListSource {
		source_diagram_id?: string | null;
		profile_id?: string | null;
	}

	interface Props {
		content: string;
		editing?: boolean;
		setId?: string | null;
		source?: AggregationListSource;
		onsourcechange?: (next: AggregationListSource) => void;
		onheadings?: (h: TocHeading[]) => void;
	}

	let {
		content,
		editing = false,
		setId = null,
		source = $bindable({}),
		onsourcechange,
		onheadings,
	}: Props = $props();

	let diagrams = $state<DiagramRow[]>([]);
	let profiles = $state<ProfileRow[]>([]);
	let loadingDiagrams = $state(false);
	let loadingProfiles = $state(false);
	let loadError = $state<string | null>(null);
	// One-shot guards: without these, a failed loadDiagrams/loadProfiles
	// would re-fire the $effect (diagrams.length stays 0) and spam the
	// API. The picker should attempt once per editing-toggle.
	let triedDiagrams = $state(false);
	let triedProfiles = $state(false);

	onMount(() => {
		if (editing) {
			void loadOptions();
		}
	});

	$effect(() => {
		if (editing && !triedDiagrams && !loadingDiagrams) {
			void loadOptions();
		}
	});

	async function loadOptions() {
		await Promise.all([loadDiagrams(), loadProfiles()]);
	}

	async function loadDiagrams() {
		loadingDiagrams = true;
		loadError = null;
		try {
			// Restrict to smart_markdown diagrams in the same set (the
			// engine's typical input). v1: same-set only; v1.1 could
			// expand to global picks.
			const params = new URLSearchParams();
			if (setId) params.set('set_id', setId);
			// Backend caps page_size at 100. Anything larger 422s and,
			// combined with the editing-effect, used to spam the API.
			params.set('page_size', '100');
			const data = await apiFetch<{ items: DiagramRow[] }>(
				`/api/diagrams?${params.toString()}`,
			);
			diagrams = (data.items ?? []).filter(
				(d) => d.diagram_type === 'smart_markdown',
			);
		} catch (e) {
			loadError = `Failed to load source diagrams: ${(e as Error).message}`;
		}
		triedDiagrams = true;
		loadingDiagrams = false;
	}

	async function loadProfiles() {
		loadingProfiles = true;
		try {
			const params = new URLSearchParams();
			if (setId) {
				params.set('set_id', setId);
				params.set('include_global', 'true');
			} else {
				params.set('include_global', 'true');
			}
			const data = await apiFetch<{ items: ProfileRow[] }>(
				`/api/aggregation/profiles?${params.toString()}`,
			);
			profiles = data.items ?? [];
		} catch (e) {
			loadError = `${loadError ?? ''}\nFailed to load profiles: ${(e as Error).message}`.trim();
		}
		triedProfiles = true;
		loadingProfiles = false;
	}

	function emit(next: AggregationListSource) {
		source = next;
		onsourcechange?.(next);
	}

	function onSourceDiagramChange(e: Event) {
		const value = (e.target as HTMLSelectElement).value || null;
		emit({ ...source, source_diagram_id: value });
	}

	function onProfileChange(e: Event) {
		const value = (e.target as HTMLSelectElement).value || null;
		emit({ ...source, profile_id: value });
	}
</script>

<div class="agg-list-canvas" data-mode={editing ? 'edit' : 'view'}>
	{#if editing}
		<div class="config-pane">
			<h3 class="text-base font-semibold" style="color: var(--color-fg)">Aggregation list configuration</h3>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				The engine walks the source diagram against the selected profile
				and renders aggregated markdown. Source and profile are required.
			</p>
			{#if loadError}
				<p class="mt-2 text-sm" style="color: var(--color-danger)">{loadError}</p>
			{/if}
			<label class="mt-3 block text-sm" style="color: var(--color-fg)">
				Source diagram (smart_markdown)
				<select
					value={source?.source_diagram_id ?? ''}
					onchange={onSourceDiagramChange}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					<option value="">— pick a source —</option>
					{#each diagrams as d (d.id)}
						<option value={d.id}>{d.name}</option>
					{/each}
				</select>
			</label>
			{#if loadingDiagrams}
				<p class="mt-1 text-xs" style="color: var(--color-muted)">Loading…</p>
			{/if}
			<label class="mt-3 block text-sm" style="color: var(--color-fg)">
				Aggregation profile
				<select
					value={source?.profile_id ?? ''}
					onchange={onProfileChange}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					<option value="">— pick a profile —</option>
					{#each profiles as p (p.id)}
						<option value={p.id}>
							{p.name}{p.is_global ? ' (global)' : ''}
						</option>
					{/each}
				</select>
			</label>
			{#if loadingProfiles}
				<p class="mt-1 text-xs" style="color: var(--color-muted)">Loading…</p>
			{/if}
			<details class="mt-4">
				<summary class="cursor-pointer text-sm" style="color: var(--color-muted)">Preview (current rendered output)</summary>
				<div class="mt-2 rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
					<MarkdownView source={content ?? ''} {onheadings} />
				</div>
			</details>
		</div>
	{:else}
		<div class="view-pane">
			<MarkdownView source={content ?? ''} {onheadings} />
		</div>
	{/if}
</div>

<style>
	.agg-list-canvas {
		width: 100%;
		height: 100%;
	}
	.config-pane {
		padding: 24px 32px;
		max-width: 700px;
	}
	.view-pane {
		padding: 24px 32px;
		max-width: 920px;
		margin: 0 auto;
	}
</style>
