<script lang="ts">
	/**
	 * SPEC-212-f: line_format chip composer with live preview (Option B).
	 *
	 * Click a chip → that placeholder is inserted at the input's cursor.
	 * When `sourceDiagramId` is set, debounce-call POST /api/aggregation/run
	 * with the inline profile draft to show 3-5 rendered preview lines.
	 */

	import { apiFetch, ApiError } from '$lib/utils/api';
	import { LINE_FORMAT_PLACEHOLDERS } from './aggregationProfileHelpers';
	import { insertAtCursor } from './aggregationProfileHelpers';

	interface Props {
		value: string;
		profileData: Record<string, unknown>;
		sourceDiagramId: string | null;
	}

	let { value = $bindable(''), profileData, sourceDiagramId }: Props = $props();

	let inputEl: HTMLInputElement | null = $state(null);
	let preview = $state<string | null>(null);
	let previewError = $state<string | null>(null);
	let previewLoading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	function insertChip(placeholder: string) {
		const el = inputEl;
		if (!el) {
			value = value + placeholder;
			return;
		}
		const cursor = el.selectionStart ?? value.length;
		const { text, cursor: newCursor } = insertAtCursor(value, cursor, placeholder);
		value = text;
		// Restore focus + cursor after Svelte re-renders.
		queueMicrotask(() => {
			el.focus();
			el.setSelectionRange(newCursor, newCursor);
		});
	}

	async function runPreview() {
		if (!sourceDiagramId) {
			preview = null;
			previewError = null;
			return;
		}
		previewLoading = true;
		previewError = null;
		try {
			const result = await apiFetch<{ markdown: string; row_count: number }>(
				'/api/aggregation/run',
				{
					method: 'POST',
					body: JSON.stringify({
						profile_data: profileData,
						source_diagram_id: sourceDiagramId,
					}),
				},
			);
			// Show first 5 non-empty lines as a preview.
			const lines = (result.markdown ?? '').split('\n').filter((l) => l.trim() !== '');
			preview = lines.slice(0, 5).join('\n');
			if (lines.length === 0) {
				preview = '(no rows matched the current profile)';
			}
		} catch (e) {
			preview = null;
			previewError = e instanceof ApiError ? e.message : 'Preview failed';
		}
		previewLoading = false;
	}

	$effect(() => {
		// Watch profileData + sourceDiagramId; debounce 400ms.
		// Touch the inputs Svelte should track:
		void value;
		void profileData;
		void sourceDiagramId;
		if (debounceTimer) clearTimeout(debounceTimer);
		if (!sourceDiagramId) {
			preview = null;
			previewError = null;
			return;
		}
		debounceTimer = setTimeout(() => {
			void runPreview();
		}, 400);
	});
</script>

<div class="line-format-composer">
	<label class="block text-sm font-medium" style="color: var(--color-fg)">
		Line format
		<input
			type="text"
			bind:value
			bind:this={inputEl}
			class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</label>
	<div class="mt-2 flex flex-wrap gap-1">
		{#each LINE_FORMAT_PLACEHOLDERS as p (p.key)}
			<button
				type="button"
				onclick={() => insertChip(p.label)}
				title={p.hint}
				class="rounded px-2 py-1 text-xs"
				style="border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-fg); font-family: monospace"
			>
				{p.label}
			</button>
		{/each}
	</div>
	<p class="mt-1 text-xs" style="color: var(--color-muted)">
		Click a placeholder to insert it at the cursor.
	</p>

	{#if sourceDiagramId}
		<div class="mt-3 rounded border p-2" style="border-color: var(--color-border); background: var(--color-bg)">
			<p class="text-xs font-medium" style="color: var(--color-muted)">Live preview</p>
			{#if previewLoading}
				<p class="mt-1 text-xs" style="color: var(--color-muted)">Rendering…</p>
			{:else if previewError}
				<p class="mt-1 text-xs" style="color: var(--color-danger)">{previewError}</p>
			{:else if preview}
				<pre class="mt-1 whitespace-pre-wrap text-xs" style="color: var(--color-fg); font-family: monospace">{preview}</pre>
			{:else}
				<p class="mt-1 text-xs" style="color: var(--color-muted)">(no preview yet)</p>
			{/if}
		</div>
	{:else}
		<p class="mt-2 text-xs" style="color: var(--color-muted)">
			Live preview requires a source diagram. Open the editor from a set page that has a smart-markdown diagram, or set the preview source after creating the profile.
		</p>
	{/if}
</div>
