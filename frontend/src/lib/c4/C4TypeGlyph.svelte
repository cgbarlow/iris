<script lang="ts">
	import { C4_TYPE_GLYPHS } from './c4TypeVisuals';

	interface Props {
		type: string;
		size?: number;
		color?: string;
	}

	let { type, size = 16, color = 'currentColor' }: Props = $props();
	const glyph = $derived(C4_TYPE_GLYPHS[type]);
</script>

{#if glyph}
	<svg
		width={size}
		height={size}
		viewBox={glyph.viewBox}
		fill="none"
		stroke={color}
		stroke-width="2"
		stroke-linecap="round"
		stroke-linejoin="round"
		role="img"
		aria-label={glyph.label}
	>
		{@html glyph.path}
	</svg>
{/if}
