<script lang="ts">
	/**
	 * NodeStylePanel: Per-element visual override editor.
	 * Shows when a node is selected in edit mode. Allows colour/size overrides.
	 * Emits a 'nodestylechange' CustomEvent with the updated visual overrides.
	 */
	import type { NodeVisualOverrides } from '$lib/types/canvas';

	interface Props {
		nodeId: string;
		visual: NodeVisualOverrides;
	}

	let { nodeId, visual }: Props = $props();

	let bgColor = $state(visual.bgColor ?? '');
	let borderColor = $state(visual.borderColor ?? '');
	let fontColor = $state(visual.fontColor ?? '');
	let borderWidth = $state(visual.borderWidth ?? 2);
	let fontSize = $state(visual.fontSize ?? 0);
	let bold = $state(visual.bold ?? false);
	let italic = $state(visual.italic ?? false);

	function emit() {
		const updated: NodeVisualOverrides = {};
		if (bgColor) updated.bgColor = bgColor;
		if (borderColor) updated.borderColor = borderColor;
		if (fontColor) updated.fontColor = fontColor;
		if (borderWidth && borderWidth !== 2) updated.borderWidth = borderWidth;
		if (fontSize && fontSize > 0) updated.fontSize = fontSize;
		if (bold) updated.bold = true;
		if (italic) updated.italic = true;
		// Preserve width/height from existing visual
		if (visual.width) updated.width = visual.width;
		if (visual.height) updated.height = visual.height;
		document.dispatchEvent(
			new CustomEvent('nodestylechange', { detail: { nodeId, visual: updated } }),
		);
	}

	function resetToDefaults() {
		bgColor = '';
		borderColor = '';
		fontColor = '';
		borderWidth = 2;
		fontSize = 0;
		bold = false;
		italic = false;
		// Keep dimensions but reset colours
		const reset: NodeVisualOverrides = {};
		if (visual.width) reset.width = visual.width;
		if (visual.height) reset.height = visual.height;
		document.dispatchEvent(
			new CustomEvent('nodestylechange', { detail: { nodeId, visual: Object.keys(reset).length > 0 ? reset : undefined } }),
		);
	}
</script>

<div class="rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
	<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Node Style</h4>
	<div class="grid grid-cols-2 gap-2">
		<label class="text-xs" style="color: var(--color-fg)">
			Background
			<input type="color" bind:value={bgColor} onchange={emit} class="mt-1 block h-6 w-full cursor-pointer" />
		</label>
		<label class="text-xs" style="color: var(--color-fg)">
			Border
			<input type="color" bind:value={borderColor} onchange={emit} class="mt-1 block h-6 w-full cursor-pointer" />
		</label>
		<label class="text-xs" style="color: var(--color-fg)">
			Font
			<input type="color" bind:value={fontColor} onchange={emit} class="mt-1 block h-6 w-full cursor-pointer" />
		</label>
		<label class="text-xs" style="color: var(--color-fg)">
			Border Width
			<input type="number" bind:value={borderWidth} onchange={emit} min="0" max="10" class="mt-1 block w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
		</label>
		<label class="text-xs" style="color: var(--color-fg)">
			Font Size
			<input type="number" bind:value={fontSize} onchange={emit} min="0" max="32" placeholder="auto" class="mt-1 block w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
		</label>
		<div class="flex items-end gap-3">
			<label class="flex items-center gap-1 text-xs" style="color: var(--color-fg)">
				<input type="checkbox" bind:checked={bold} onchange={emit} /> Bold
			</label>
			<label class="flex items-center gap-1 text-xs" style="color: var(--color-fg)">
				<input type="checkbox" bind:checked={italic} onchange={emit} /> Italic
			</label>
		</div>
	</div>
	<button
		onclick={resetToDefaults}
		class="mt-2 rounded px-2 py-1 text-xs"
		style="border: 1px solid var(--color-border); color: var(--color-muted)"
	>
		Reset to theme defaults
	</button>
</div>
