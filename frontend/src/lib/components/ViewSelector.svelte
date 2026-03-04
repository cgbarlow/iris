<script lang="ts">
	/**
	 * ViewSelector: Dropdown in top nav for switching the active View.
	 * Views are admin-configurable profiles that control UI feature visibility.
	 */
	import { getViews, getActiveViewId, setActiveView, loadViews } from '$lib/stores/viewStore.svelte';

	let loaded = $state(false);

	$effect(() => {
		if (!loaded) {
			loadViews().then(() => { loaded = true; });
		}
	});

	const views = $derived(getViews());
	const activeId = $derived(getActiveViewId());

	function handleChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		setActiveView(target.value);
	}
</script>

{#if views.length > 0}
	<select
		aria-label="Active view"
		class="rounded border px-2 py-1 text-xs"
		style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
		value={activeId}
		onchange={handleChange}
	>
		{#each views as view}
			<option value={view.id}>{view.name}</option>
		{/each}
	</select>
{/if}
