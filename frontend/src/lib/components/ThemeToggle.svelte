<script lang="ts">
	import { toggleMode, mode, setMode } from 'mode-watcher';

	let highContrast = $state(false);

	function cycleTheme() {
		if (highContrast) {
			highContrast = false;
			document.documentElement.classList.remove('high-contrast');
			setMode('light');
		} else if (mode.current === 'light') {
			toggleMode();
		} else if (mode.current === 'dark') {
			highContrast = true;
			document.documentElement.classList.add('high-contrast');
		} else {
			toggleMode();
		}
	}

	const label = $derived(
		highContrast ? 'High contrast' : mode.current === 'dark' ? 'Dark' : 'Light',
	);
</script>

<button
	onclick={cycleTheme}
	class="rounded px-2 py-1 text-sm"
	style="color: var(--color-muted)"
	aria-label="Toggle theme: currently {label}"
	title="Theme: {label}"
>
	{highContrast ? 'HC' : mode.current === 'dark' ? 'Dark' : 'Light'}
</button>
