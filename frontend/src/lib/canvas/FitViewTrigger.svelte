<script lang="ts">
	/** Reactive viewport pan trigger — must be a child of SvelteFlow. */
	import { useSvelteFlow } from '@xyflow/svelte';

	interface Props {
		panX?: number;
	}

	let { panX = 0 }: Props = $props();
	const { getViewport, setViewport } = useSvelteFlow();
	let prevPanX = 0;

	$effect(() => {
		const delta = panX - prevPanX;
		if (delta !== 0) {
			prevPanX = panX;
			const vp = getViewport();
			setViewport({ x: vp.x + delta, y: vp.y, zoom: vp.zoom });
		}
	});
</script>
