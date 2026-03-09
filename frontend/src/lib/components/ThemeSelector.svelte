<script lang="ts">
	/**
	 * ThemeSelector: Dropdown for switching the active theme.
	 * Shows all available themes grouped by notation, with the current
	 * notation's themes listed first. Always visible in diagram toolbar.
	 */
	import {
		getThemes,
		getActiveThemeId,
		getActiveTheme,
		setActiveTheme,
	} from '$lib/stores/themeStore.svelte';

	interface Props {
		notation: string;
	}

	let { notation }: Props = $props();

	/** All themes, with current notation first, then others grouped by notation. */
	const sortedThemes = $derived.by(() => {
		const all = getThemes();
		const forNotation = all.filter((t) => t.notation === notation);
		const others = all.filter((t) => t.notation !== notation);
		return { forNotation, others };
	});

	/** Active theme ID — explicit selection or fallback default. */
	const activeId = $derived(getActiveThemeId(notation) ?? getActiveTheme(notation)?.id ?? '');
	const hasThemes = $derived(sortedThemes.forNotation.length > 0 || sortedThemes.others.length > 0);

	function handleChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		setActiveTheme(notation, target.value);
	}
</script>

{#if hasThemes}
	<select
		aria-label="Active theme"
		class="rounded border px-2 py-1 text-xs"
		style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
		value={activeId}
		onchange={handleChange}
	>
		{#if sortedThemes.forNotation.length > 0}
			<optgroup label="{notation.toUpperCase()} themes">
				{#each sortedThemes.forNotation as theme}
					<option value={theme.id}>{theme.name}</option>
				{/each}
			</optgroup>
		{/if}
		{#if sortedThemes.others.length > 0}
			<optgroup label="Other themes">
				{#each sortedThemes.others as theme}
					<option value={theme.id}>{theme.name} ({theme.notation})</option>
				{/each}
			</optgroup>
		{/if}
	</select>
{/if}
