<script lang="ts">
	/** ARIA live region for canvas operation announcements to screen readers. */
	let message = $state('');

	export function announce(text: string) {
		message = '';
		setTimeout(() => {
			message = text;
		}, 50);
	}
</script>

<div aria-live="polite" aria-atomic="true" class="sr-only" id="canvas-announcer">
	{message}
</div>
