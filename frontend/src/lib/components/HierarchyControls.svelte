<script lang="ts">
	/**
	 * Issue #27: Hierarchy panel controls — two dropdowns standardised
	 * across the Dashboard and Views page so the toolbar reads the same
	 * everywhere.
	 *
	 *  - "+ New"  → create View | create Package
	 *  - "Show"   → toggle Diagrams / Text visibility (Packages always shown)
	 *
	 * Issue #30: dropdowns anchor `left-0` so the menu extends rightwards
	 * from the button. `right-0` clipped under the AppShell on the
	 * Dashboard hierarchy panel because that panel sits flush-left and
	 * a leftward menu had nowhere to go.
	 */
	interface Props {
		showDiagrams: boolean;
		showText: boolean;
		onShowDiagrams: (v: boolean) => void;
		onShowText: (v: boolean) => void;
		oncreateview: () => void;
		oncreatepackage: () => void;
	}

	let {
		showDiagrams,
		showText,
		onShowDiagrams,
		onShowText,
		oncreateview,
		oncreatepackage,
	}: Props = $props();

	let newOpen = $state(false);
	let showOpen = $state(false);

	function closeAll() {
		newOpen = false;
		showOpen = false;
	}
</script>

<div class="flex items-center gap-2">
	<div class="relative">
		<button
			type="button"
			onclick={() => { newOpen = !newOpen; showOpen = false; }}
			class="rounded px-3 py-1.5 text-sm text-white"
			style="background-color: var(--color-primary)"
			aria-haspopup="menu"
			aria-expanded={newOpen}
		>
			+ New ▾
		</button>
		{#if newOpen}
			<div
				role="menu"
				class="absolute left-0 z-50 mt-1 min-w-[160px] rounded border py-1 shadow-lg"
				style="background-color: var(--color-bg, #fff); border-color: var(--color-border)"
			>
				<button
					role="menuitem"
					onclick={() => { oncreateview(); closeAll(); }}
					class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80"
					style="color: var(--color-fg)"
				>
					View
				</button>
				<button
					role="menuitem"
					onclick={() => { oncreatepackage(); closeAll(); }}
					class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80"
					style="color: var(--color-fg)"
				>
					Package
				</button>
			</div>
		{/if}
	</div>

	<div class="relative">
		<button
			type="button"
			onclick={() => { showOpen = !showOpen; newOpen = false; }}
			class="rounded border px-3 py-1.5 text-sm"
			style="border-color: var(--color-border); color: var(--color-fg)"
			aria-haspopup="menu"
			aria-expanded={showOpen}
		>
			Show ▾
		</button>
		{#if showOpen}
			<div
				role="menu"
				class="absolute left-0 z-50 mt-1 min-w-[180px] rounded border py-1 shadow-lg"
				style="background-color: var(--color-bg, #fff); border-color: var(--color-border)"
			>
				<label
					class="flex cursor-pointer items-center gap-2 px-4 py-1.5 text-sm hover:opacity-80"
					style="color: var(--color-fg)"
				>
					<input
						type="checkbox"
						checked={showDiagrams}
						onchange={(e) => onShowDiagrams((e.target as HTMLInputElement).checked)}
					/>
					Diagrams
				</label>
				<label
					class="flex cursor-pointer items-center gap-2 px-4 py-1.5 text-sm hover:opacity-80"
					style="color: var(--color-fg)"
				>
					<input
						type="checkbox"
						checked={showText}
						onchange={(e) => onShowText((e.target as HTMLInputElement).checked)}
					/>
					Text
				</label>
				<p class="mt-1 px-4 py-1 text-xs" style="color: var(--color-muted)">
					Packages are always shown.
				</p>
			</div>
		{/if}
	</div>
</div>

{#if newOpen || showOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-40"
		onclick={closeAll}
		onkeydown={(e) => { if (e.key === 'Escape') closeAll(); }}
	></div>
{/if}
