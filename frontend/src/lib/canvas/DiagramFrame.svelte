<script lang="ts">
	/**
	 * DiagramFrame: Renders a border rectangle + title tab for imported EA diagrams.
	 * Shows "[type] [name]" in a tab at the top-left corner.
	 */
	interface Props {
		type: string;
		name: string;
		width: number;
		height: number;
	}

	let { type, name, width, height }: Props = $props();
</script>

<svg
	class="diagram-frame"
	style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: -1;"
	width={width + 20}
	height={height + 40}
	viewBox="-10 -30 {width + 20} {height + 40}"
>
	<!-- Title tab -->
	<rect x="0" y="-24" width={Math.max((type.length + name.length + 2) * 7, 120)} height="24" fill="#fff" stroke="#333" stroke-width="1" />
	<text x="6" y="-8" font-size="11" fill="#333" font-family="sans-serif">{type} {name}</text>
	<!-- Frame border -->
	<rect x="0" y="0" {width} {height} fill="none" stroke="#333" stroke-width="1" />
</svg>
