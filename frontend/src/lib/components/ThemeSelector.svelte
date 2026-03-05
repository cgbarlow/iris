<script lang="ts">
	/**
	 * ThemeSelector: Dropdown for switching the active theme for a given notation.
	 * Placed in diagram toolbar — shows themes available for the current notation.
	 */
	import {
		getThemesForNotation,
		getActiveThemeId,
		setActiveTheme,
		loadThemes,
		getThemes,
	} from '$lib/stores/themeStore.svelte';

	interface Props {
		notation: string;
	}

	let { notation }: Props = $props();

	let loaded = $state(false);

	$effect(() => {
		if (!loaded && getThemes().length === 0) {
			loadThemes().then(() => { loaded = true; });
		} else {
			loaded = true;
		}
	});

	const themes = $derived(getThemesForNotation(notation));
	const activeId = $derived(getActiveThemeId(notation));

	function handleChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		setActiveTheme(notation, target.value);
	}
</script>

{#if themes.length > 0}
	<select
		aria-label="Active theme"
		class="rounded border px-2 py-1 text-xs"
		style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
		value={activeId}
		onchange={handleChange}
	>
		{#each themes as theme}
			<option value={theme.id}>{theme.name}</option>
		{/each}
	</select>
{/if}
