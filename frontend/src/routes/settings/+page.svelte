<script lang="ts">
	import { mode, setMode } from 'mode-watcher';
	import { onMount } from 'svelte';

	let highContrast = $state(false);

	onMount(() => {
		highContrast = localStorage.getItem('iris-high-contrast') === 'true';
		if (highContrast) {
			document.documentElement.classList.add('high-contrast');
		}
	});

	const currentTheme = $derived(
		highContrast ? 'high-contrast' : (mode.current ?? 'light'),
	);

	function selectTheme(theme: string) {
		if (theme === 'high-contrast') {
			highContrast = true;
			document.documentElement.classList.add('high-contrast');
			localStorage.setItem('iris-high-contrast', 'true');
			setMode('dark');
		} else {
			highContrast = false;
			document.documentElement.classList.remove('high-contrast');
			localStorage.setItem('iris-high-contrast', 'false');
			setMode(theme as 'light' | 'dark');
		}
	}
</script>

<svelte:head>
	<title>Settings — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Settings</h1>
<p class="mt-2" style="color: var(--color-muted)">Configure your preferences.</p>

<section class="mt-6">
	<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Theme</h2>
	<p class="mt-1 text-sm" style="color: var(--color-muted)">Choose your preferred colour scheme.</p>

	<fieldset class="mt-4 flex flex-col gap-3" role="radiogroup" aria-label="Theme selection">
		<label
			class="flex items-center gap-3 rounded border px-4 py-3 cursor-pointer"
			style="border-color: {currentTheme === 'light' ? 'var(--color-primary)' : 'var(--color-border)'}; background-color: {currentTheme === 'light' ? 'var(--color-bg)' : 'transparent'}"
		>
			<input
				type="radio"
				name="theme"
				value="light"
				checked={currentTheme === 'light'}
				onchange={() => selectTheme('light')}
				class="accent-[var(--color-primary)]"
			/>
			<span style="color: var(--color-fg)">Light</span>
		</label>

		<label
			class="flex items-center gap-3 rounded border px-4 py-3 cursor-pointer"
			style="border-color: {currentTheme === 'dark' ? 'var(--color-primary)' : 'var(--color-border)'}; background-color: {currentTheme === 'dark' ? 'var(--color-bg)' : 'transparent'}"
		>
			<input
				type="radio"
				name="theme"
				value="dark"
				checked={currentTheme === 'dark'}
				onchange={() => selectTheme('dark')}
				class="accent-[var(--color-primary)]"
			/>
			<span style="color: var(--color-fg)">Dark</span>
		</label>

		<label
			class="flex items-center gap-3 rounded border px-4 py-3 cursor-pointer"
			style="border-color: {currentTheme === 'high-contrast' ? 'var(--color-primary)' : 'var(--color-border)'}; background-color: {currentTheme === 'high-contrast' ? 'var(--color-bg)' : 'transparent'}"
		>
			<input
				type="radio"
				name="theme"
				value="high-contrast"
				checked={currentTheme === 'high-contrast'}
				onchange={() => selectTheme('high-contrast')}
				class="accent-[var(--color-primary)]"
			/>
			<span style="color: var(--color-fg)">High Contrast</span>
		</label>
	</fieldset>
</section>
