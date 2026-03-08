<script lang="ts">
	/**
	 * DiagramFrameNode: Renders a diagram border + title tab as a non-interactive
	 * SvelteFlow node so it zooms/pans with the canvas (ADR-088).
	 */
	import type { CanvasNodeData } from '$lib/types/canvas';

	interface Props {
		data: CanvasNodeData;
	}

	let { data }: Props = $props();

	/** UML frame type abbreviations (standard EA notation). */
	const FRAME_ABBREV: Record<string, string> = {
		class: 'cd',
		use_case: 'uc',
		component: 'cmp',
		deployment: 'dep',
		sequence: 'sd',
		pkg: 'pkg',
		process: 'act',
		state_machine: 'stm',
	};

	const rawType = $derived((data as Record<string, unknown>).frameType as string ?? '');
	const framePrefix = $derived(rawType ? (FRAME_ABBREV[rawType] ?? rawType) : '');
	const frameName = $derived(data.label ?? '');
	const frameWidth = $derived((data as Record<string, unknown>).frameWidth as number ?? 800);
	const frameHeight = $derived((data as Record<string, unknown>).frameHeight as number ?? 600);
	const displayText = $derived(framePrefix ? `${framePrefix} ${frameName}` : frameName);
	const tabWidth = $derived(Math.max(displayText.length * 7, 120));
</script>

<div class="diagram-frame-node" style="width: {frameWidth}px; height: {frameHeight}px; pointer-events: none;">
	<svg
		width={frameWidth}
		height={frameHeight}
		viewBox="0 0 {frameWidth} {frameHeight}"
		style="pointer-events: none"
	>
		<!-- Title tab (border-less, text only) -->
		<text x="6" y="16" font-size="11" fill="#333" font-family="sans-serif">{displayText}</text>
	</svg>
</div>

<style>
	.diagram-frame-node {
		pointer-events: none;
	}
</style>
