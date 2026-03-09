<script lang="ts">
	/**
	 * IconDisplay: Renders an IconRef to an SVG icon at any size (ADR-091-B).
	 * Uses the icon registry to resolve the reference to a Svelte component.
	 */
	import type { IconRef } from '$lib/types/canvas';
	import { resolveIcon } from './iconRegistry';

	interface Props {
		icon: IconRef;
		size?: number;
		color?: string;
		cssClass?: string;
	}

	let { icon, size = 24, color = 'currentColor', cssClass = '' }: Props = $props();

	const IconComponent = $derived(resolveIcon(icon));
</script>

{#if IconComponent}
	<IconComponent {size} {color} class={cssClass} />
{:else}
	<!-- Fallback: show icon name as text -->
	<span class="icon-display-fallback {cssClass}" style="font-size: {size * 0.5}px; color: {color}">
		{icon.name}
	</span>
{/if}

<style>
	.icon-display-fallback {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		opacity: 0.5;
	}
</style>
