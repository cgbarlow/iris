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
		themeVisual?: NodeVisualOverrides;
		notation?: NotationType;
		entityType?: SimpleEntityType;
	}

	let { nodeId, visual, themeVisual, notation, entityType = 'component' }: Props = $props();

	// --- Node-level state ---
	let bgColor = $state('');
	let borderColor = $state('');
	let borderWidth = $state(2);
	let showIconPicker = $state(false);
	let iconColor = $state('');

	// --- Title font state ---
	let titleColor = $state('');
	let titleSize = $state(14);
	let titleBold = $state(false);
	let titleItalic = $state(false);

	// --- Description font state ---
	let descColor = $state('');
	let descSize = $state(12);
	let descBold = $state(false);
	let descItalic = $state(false);

	/** CSS fallback defaults when neither per-element nor theme values exist. */
	const FALLBACK_BG = '#f8fafc';
	const FALLBACK_BORDER = '#6b7280';
	const FALLBACK_FONT = '#1a1a2e';
	const FALLBACK_ICON_COLOR = '#5b9bd5';
	const DEFAULT_TITLE_SIZE = 14;
	const DEFAULT_DESC_SIZE = 12;

	/** Whether UML notation (no description section). */
	const isUml = $derived(notation === 'uml');

	// Sync local state when the selected node changes.
	// Show effective value: per-element override > theme default > CSS fallback.
	$effect(() => {
		void nodeId;
		// Node-level
		bgColor = visual.bgColor ?? themeVisual?.bgColor ?? FALLBACK_BG;
		borderColor = visual.borderColor ?? themeVisual?.borderColor ?? FALLBACK_BORDER;
		borderWidth = visual.borderWidth ?? themeVisual?.borderWidth ?? 2;
		iconColor = visual.iconColor ?? themeVisual?.iconColor ?? FALLBACK_ICON_COLOR;
		// Title font
		titleColor = visual.fontColor ?? themeVisual?.fontColor ?? FALLBACK_FONT;
		titleSize = visual.fontSize ?? themeVisual?.fontSize ?? DEFAULT_TITLE_SIZE;
		titleBold = visual.bold ?? themeVisual?.bold ?? false;
		titleItalic = visual.italic ?? themeVisual?.italic ?? false;
		// Description font
		descColor = visual.descFontColor ?? themeVisual?.descFontColor ?? FALLBACK_FONT;
		descSize = visual.descFontSize ?? themeVisual?.descFontSize ?? DEFAULT_DESC_SIZE;
		descBold = visual.descBold ?? themeVisual?.descBold ?? false;
		descItalic = visual.descItalic ?? themeVisual?.descItalic ?? false;
	});

	/** Detect whether any overrides differ from theme defaults. */
	const hasChanges = $derived.by(() => {
		const tb = themeVisual ?? {};
		if (bgColor !== (tb.bgColor ?? FALLBACK_BG)) return true;
		if (borderColor !== (tb.borderColor ?? FALLBACK_BORDER)) return true;
		if (borderWidth !== (tb.borderWidth ?? 2)) return true;
		if (titleColor !== (tb.fontColor ?? FALLBACK_FONT)) return true;
		if (titleSize !== (tb.fontSize ?? DEFAULT_TITLE_SIZE)) return true;
		if (titleBold !== (tb.bold ?? false)) return true;
		if (titleItalic !== (tb.italic ?? false)) return true;
		if (!isUml) {
			if (descColor !== (tb.descFontColor ?? FALLBACK_FONT)) return true;
			if (descSize !== (tb.descFontSize ?? DEFAULT_DESC_SIZE)) return true;
			if (descBold !== (tb.descBold ?? false)) return true;
			if (descItalic !== (tb.descItalic ?? false)) return true;
		}
		if (visual.icon) return true;
		if (iconColor !== (tb.iconColor ?? FALLBACK_ICON_COLOR)) return true;
		return false;
	});

	function buildVisual(): NodeVisualOverrides {
		const updated: NodeVisualOverrides = {};
		const tb = themeVisual ?? {};
		// Node-level
		if (bgColor && bgColor !== (tb.bgColor ?? FALLBACK_BG)) updated.bgColor = bgColor;
		if (borderColor && borderColor !== (tb.borderColor ?? FALLBACK_BORDER)) updated.borderColor = borderColor;
		if (borderWidth != null && borderWidth !== (tb.borderWidth ?? 2)) updated.borderWidth = borderWidth;
		// Title font
		if (titleColor && titleColor !== (tb.fontColor ?? FALLBACK_FONT)) updated.fontColor = titleColor;
		if (titleSize > 0 && titleSize !== (tb.fontSize ?? DEFAULT_TITLE_SIZE)) updated.fontSize = titleSize;
		if (titleBold !== (tb.bold ?? false)) updated.bold = titleBold;
		if (titleItalic !== (tb.italic ?? false)) updated.italic = titleItalic;
		// Description font
		if (!isUml) {
			if (descColor && descColor !== (tb.descFontColor ?? FALLBACK_FONT)) updated.descFontColor = descColor;
			if (descSize > 0 && descSize !== (tb.descFontSize ?? DEFAULT_DESC_SIZE)) updated.descFontSize = descSize;
			if (descBold !== (tb.descBold ?? false)) updated.descBold = descBold;
			if (descItalic !== (tb.descItalic ?? false)) updated.descItalic = descItalic;
		}
		// Icon colour
		if (iconColor && iconColor !== (tb.iconColor ?? FALLBACK_ICON_COLOR)) updated.iconColor = iconColor;
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
		const tb = themeVisual ?? {};
		bgColor = tb.bgColor ?? FALLBACK_BG;
		borderColor = tb.borderColor ?? FALLBACK_BORDER;
		borderWidth = tb.borderWidth ?? 2;
		titleColor = tb.fontColor ?? FALLBACK_FONT;
		titleSize = tb.fontSize ?? DEFAULT_TITLE_SIZE;
		titleBold = tb.bold ?? false;
		titleItalic = tb.italic ?? false;
		descColor = tb.descFontColor ?? FALLBACK_FONT;
		descSize = tb.descFontSize ?? DEFAULT_DESC_SIZE;
		descBold = tb.descBold ?? false;
		descItalic = tb.descItalic ?? false;
		iconColor = tb.iconColor ?? FALLBACK_ICON_COLOR;
		const reset: NodeVisualOverrides = {};
		if (visual.width) reset.width = visual.width;
		if (visual.height) reset.height = visual.height;
		if (visual.icon) reset.icon = visual.icon;
		document.dispatchEvent(
			new CustomEvent('nodestylechange', { detail: { nodeId, visual: Object.keys(reset).length > 0 ? reset : undefined } }),
		);
	}
</script>

<div class="rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
	<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Node Style</h4>

	<!-- Node-level: background, border colour, border width -->
	<div class="grid grid-cols-3 gap-2">
		<label class="text-xs" style="color: var(--color-fg)">
			Background
			<input type="color" bind:value={bgColor} onchange={emit} class="mt-0.5 block h-6 w-full cursor-pointer" />
		</label>
		<label class="text-xs" style="color: var(--color-fg)">
			Border
			<input type="color" bind:value={borderColor} onchange={emit} class="mt-0.5 block h-6 w-full cursor-pointer" />
		</label>
		<label class="text-xs" style="color: var(--color-fg)">
			Width
			<input type="number" bind:value={borderWidth} onchange={emit} min="0" max="10" class="mt-0.5 block w-full rounded border px-2 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
		</label>
	</div>

	<!-- Title: colour, size, bold, italic -->
	<div class="mt-2 text-xs" style="color: var(--color-fg)">
		<span class="font-semibold" style="color: var(--color-muted)">Title</span>
		<div class="mt-0.5 flex items-center gap-2">
			<input type="color" bind:value={titleColor} onchange={emit} class="h-6 w-8 cursor-pointer" title="Title colour" />
			<input type="number" bind:value={titleSize} onchange={emit} min="8" max="48" class="w-14 rounded border px-2 py-0.5 text-xs" title="Size" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
			<label class="flex items-center gap-1 text-xs"><input type="checkbox" bind:checked={titleBold} onchange={emit} /> Bold</label>
			<label class="flex items-center gap-1 text-xs"><input type="checkbox" bind:checked={titleItalic} onchange={emit} /> Italic</label>
		</div>
	</div>

	<!-- Description: colour, size, bold, italic -->
	{#if !isUml}
		<div class="mt-2 text-xs" style="color: var(--color-fg)">
			<span class="font-semibold" style="color: var(--color-muted)">Description</span>
			<div class="mt-0.5 flex items-center gap-2">
				<input type="color" bind:value={descColor} onchange={emit} class="h-6 w-8 cursor-pointer" title="Description colour" />
				<input type="number" bind:value={descSize} onchange={emit} min="8" max="48" class="w-14 rounded border px-2 py-0.5 text-xs" title="Size" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
				<label class="flex items-center gap-1 text-xs"><input type="checkbox" bind:checked={descBold} onchange={emit} /> Bold</label>
				<label class="flex items-center gap-1 text-xs"><input type="checkbox" bind:checked={descItalic} onchange={emit} /> Italic</label>
			</div>
		</div>
	{/if}

	<!-- Icon + Icon Colour + Reset -->
	<div class="mt-2 flex items-center gap-2">
		<span class="text-xs" style="color: var(--color-fg)">Icon</span>
		{#if visual.icon}
			<IconDisplay icon={visual.icon} size={16} />
			<button onclick={clearIcon} class="text-xs" style="color: var(--color-danger, #ef4444)" aria-label="Remove icon">✕</button>
		{/if}
		<button
			onclick={() => (showIconPicker = true)}
			class="rounded px-2 py-0.5 text-xs"
			style="border: 1px solid var(--color-border); color: var(--color-fg)"
		>
			{visual.icon ? 'Change' : 'Add'}
		</button>
		<input type="color" bind:value={iconColor} onchange={emit} class="h-6 w-8 cursor-pointer" title="Icon colour" />
		<span style="flex:1"></span>
		<button
			onclick={resetToDefaults}
			class="rounded px-2 py-1 text-xs"
			style="border: 1px solid var(--color-border); color: {hasChanges ? 'var(--color-fg)' : 'var(--color-muted)'}"
		>
			Reset
		</button>
	</div>
</div>

<IconPicker
	open={showIconPicker}
	onselect={handleIconSelect}
	onclose={() => (showIconPicker = false)}
/>
