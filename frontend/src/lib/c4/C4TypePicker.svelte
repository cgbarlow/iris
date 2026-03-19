<script lang="ts">
	import { C4_TYPE_GLYPHS } from './c4TypeVisuals';
	import C4TypeGlyph from './C4TypeGlyph.svelte';
	import { C4_ENTITY_TYPES } from '$lib/types/canvas';

	interface Props {
		value: string;
		onchange: (type: string) => void;
		compact?: boolean;
	}

	let { value, onchange, compact = false }: Props = $props();

	/** Canonical C4 colours per type — matches c4-default theme seed. */
	const C4_TYPE_COLOURS: Record<string, { border: string; bg: string; font: string; dashed?: boolean }> = {
		person:                   { border: '#2d8a4e', bg: '#f0fdf4', font: '#166534' },
		software_system:          { border: '#1168bd', bg: '#eff6ff', font: '#1e40af' },
		software_system_external: { border: '#c0392b', bg: '#fef2f2', font: '#991b1b' },
		container:                { border: '#438dd5', bg: '#f0f7ff', font: '#1e40af' },
		c4_component:             { border: '#85bbf0', bg: '#f8fbff', font: '#1e40af' },
		code_element:             { border: '#93c5fd', bg: '#fafcff', font: '#1e40af' },
		deployment_node:          { border: '#438dd5', bg: '#ffffff', font: '#1e40af', dashed: true },
		infrastructure_node:      { border: '#6b7280', bg: '#ffffff', font: '#555555', dashed: true },
		container_instance:       { border: '#438dd5', bg: '#f0f7ff', font: '#1e40af', dashed: true },
	};

	const types = $derived(
		C4_ENTITY_TYPES.filter((t) => t.key in C4_TYPE_GLYPHS)
	);
</script>

<div class="c4-type-picker" class:compact>
	{#each types as entityType (entityType.key)}
		{@const selected = value === entityType.key}
		{@const colours = C4_TYPE_COLOURS[entityType.key]}
		<button
			type="button"
			class="type-card"
			class:selected
			onclick={() => onchange(entityType.key)}
			aria-pressed={selected}
			title={entityType.description}
			style="border-color: {colours?.border ?? 'var(--color-border)'}; background: {selected ? (colours?.bg ?? 'var(--color-bg)') : 'var(--color-surface)'}; {colours?.dashed ? 'border-style: dashed;' : ''}"
		>
			<C4TypeGlyph
				type={entityType.key}
				size={compact ? 20 : 28}
				color={colours?.border ?? 'var(--color-muted)'}
			/>
			<span class="type-label" style="color: {selected ? (colours?.font ?? 'var(--color-fg)') : 'var(--color-fg)'}">{entityType.label}</span>
		</button>
	{/each}
</div>

<style>
	.c4-type-picker {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.5rem;
	}

	.type-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.375rem;
		padding: 0.75rem 0.5rem;
		border: 2px solid var(--color-border);
		border-radius: 0.5rem;
		background: var(--color-surface);
		cursor: pointer;
		transition:
			border-color 0.15s,
			background-color 0.15s;
	}

	.type-card:hover {
		opacity: 0.85;
	}

	.type-card.selected {
		box-shadow: 0 0 0 1px currentColor;
	}

	.type-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: var(--color-fg);
		text-align: center;
		line-height: 1.2;
	}

	/* Compact variant */
	.compact {
		gap: 0.375rem;
	}

	.compact .type-card {
		padding: 0.5rem 0.375rem;
		gap: 0.25rem;
	}

	.compact .type-label {
		font-size: 0.625rem;
	}
</style>
