<script lang="ts">
	/** ARIA live region for screen reader announcements. */
	let message = $state('');

	export function announce(text: string) {
		message = '';
		// Small delay ensures screen readers detect the change
		setTimeout(() => {
			message = text;
		}, 50);
	}
</script>

<div aria-live="polite" aria-atomic="true" class="sr-only">
	{message}
</div>
