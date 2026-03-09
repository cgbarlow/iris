<script lang="ts">
	/**
	 * NodeStylePanel: Per-element visual override editor.
	 * Shows when a node is selected in edit mode. Allows colour/size overrides,
	 * icon selection via IconPicker (ADR-091-C), and C4 element type selection.
	 * Emits a 'nodestylechange' CustomEvent with the updated visual overrides.
	 * Emits a 'nodedatachange' CustomEvent for non-visual data fields (e.g. entityType).
	 */
	import type { NodeVisualOverrides, IconRef, NotationType, SimpleEntityType } from '$lib/types/canvas';
	import IconPicker from '$lib/icons/IconPicker.svelte';
	import IconDisplay from '$lib/icons/IconDisplay.svelte';

	interface Props {
		nodeId: string;
		visual: NodeVisualOverrides;
		notation?: NotationType;
		entityType?: SimpleEntityType;
	}

	let { nodeId, visual, notation, entityType = 'component' }: Props = $props();

	let bgColor = $state('');
	let borderColor = $state('');
	let fontColor = $state('');
	let borderWidth = $state(2);
	let fontSize = $state(0);
	let bold = $state(false);
	let italic = $state(false);
	let showIconPicker = $state(false);

	// Sync local state when the selected node changes
	$effect(() => {
		// Reading nodeId and visual triggers re-run when either changes
		void nodeId;
		bgColor = visual.bgColor ?? '';
		borderColor = visual.borderColor ?? '';
		fontColor = visual.fontColor ?? '';
		borderWidth = visual.borderWidth ?? 2;
		fontSize = visual.fontSize ?? 0;
		bold = visual.bold ?? false;
		italic = visual.italic ?? false;
	});

	function buildVisual(): NodeVisualOverrides {
		const updated: NodeVisualOverrides = {};
		if (bgColor) updated.bgColor = bgColor;
		if (borderColor) updated.borderColor = borderColor;
		if (fontColor) updated.fontColor = fontColor;
		if (borderWidth && borderWidth !== 2) updated.borderWidth = borderWidth;
		if (fontSize && fontSize > 0) updated.fontSize = fontSize;
		if (bold) updated.bold = true;
		if (italic) updated.italic = true;
		// Preserve width/height and icon from existing visual
		if (visual.width) updated.width = visual.width;
		if (visual.height) updated.height = visual.height;
		if (visual.icon) updated.icon = visual.icon;
		return updated;
	}

	function emit() {
		document.dispatchEvent(
			new CustomEvent('nodestylechange', { detail: { nodeId, visual: buildVisual() } }),
		);
	}

	function handleIconSelect(icon: IconRef) {
		showIconPicker = false;
		const updated = buildVisual();
		updated.icon = icon;
		document.dispatchEvent(
			new CustomEvent('nodestylechange', { detail: { nodeId, visual: updated } }),
		);
	}

	function clearIcon() {
		const updated = buildVisual();
		delete updated.icon;
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

	<!-- Icon section (ADR-091-C) -->
	<div class="mt-3 flex items-center gap-2">
		<span class="text-xs font-medium" style="color: var(--color-fg)">Icon</span>
		{#if visual.icon}
			<IconDisplay icon={visual.icon} size={16} />
			<span class="text-xs" style="color: var(--color-muted)">{visual.icon.name}</span>
			<button
				onclick={clearIcon}
				class="text-xs"
				style="color: var(--color-danger, #ef4444)"
				aria-label="Remove icon"
			>
				✕
			</button>
		{/if}
		<button
			onclick={() => (showIconPicker = true)}
			class="rounded px-2 py-0.5 text-xs"
			style="border: 1px solid var(--color-border); color: var(--color-fg)"
		>
			{visual.icon ? 'Change' : 'Add icon'}
		</button>
	</div>

	<button
		onclick={resetToDefaults}
		class="mt-2 rounded px-2 py-1 text-xs"
		style="border: 1px solid var(--color-border); color: var(--color-muted)"
	>
		Reset to theme defaults
	</button>
</div>

<IconPicker
	open={showIconPicker}
	onselect={handleIconSelect}
	onclose={() => (showIconPicker = false)}
/>
