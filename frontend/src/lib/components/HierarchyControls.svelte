<script lang="ts">
	/**
	 * Issue #27: Hierarchy panel controls — two dropdowns standardised
	 * across the Dashboard and Views page so the toolbar reads the same
	 * everywhere.
	 *
	 *  - "+ New"  → create View | create Package
	 *  - "Show"   → toggle Diagrams / Text visibility (Packages always shown)
	 *
	 * Issue #169: the menus used `position: absolute` anchored `left-0`
	 * against a `<div class="relative">` parent. On the packages-detail
	 * sidebar (and other callers whose ancestor sets `overflow-y: auto`
	 * or `overflow: hidden`), the menu got clipped at the container's
	 * right edge. Switching to `position: fixed` with viewport-anchored
	 * coordinates from `getBoundingClientRect()` lets the menu escape
	 * any ancestor overflow.
	 *
	 * Fixed-position menus do not follow the page when it scrolls, so
	 * we close them on scroll — the user can re-open with one click.
	 */
	import { onMount } from 'svelte';

	interface Props {
		showDiagrams: boolean;
		showText: boolean;
		onShowDiagrams: (v: boolean) => void;
		onShowText: (v: boolean) => void;
		oncreateview?: () => void;
		oncreatepackage?: () => void;
		oncreateelement?: () => void;
	}

	let {
		showDiagrams,
		showText,
		onShowDiagrams,
		onShowText,
		oncreateview,
		oncreatepackage,
		oncreateelement,
	}: Props = $props();

	let newOpen = $state(false);
	let showOpen = $state(false);
	let newButtonEl = $state<HTMLButtonElement | undefined>(undefined);
	let showButtonEl = $state<HTMLButtonElement | undefined>(undefined);
	let newMenuPos = $state({ top: 0, left: 0 });
	let showMenuPos = $state({ top: 0, left: 0 });

	function positionFor(btn: HTMLButtonElement | undefined) {
		if (!btn) return { top: 0, left: 0 };
		const r = btn.getBoundingClientRect();
		return { top: r.bottom + 4, left: r.left };
	}

	function toggleNew() {
		if (!newOpen) newMenuPos = positionFor(newButtonEl);
		newOpen = !newOpen;
		showOpen = false;
	}

	function toggleShow() {
		if (!showOpen) showMenuPos = positionFor(showButtonEl);
		showOpen = !showOpen;
		newOpen = false;
	}

	function closeAll() {
		newOpen = false;
		showOpen = false;
	}

	onMount(() => {
		// Fixed-position menus stay glued to the viewport while the page
		// scrolls under them — close on any scroll to keep the menu
		// visually attached to its trigger.
		const handler = () => { if (newOpen || showOpen) closeAll(); };
		window.addEventListener('scroll', handler, true);
		return () => window.removeEventListener('scroll', handler, true);
	});
</script>

<div class="flex items-center gap-2">
	<div>
		<button
			bind:this={newButtonEl}
			type="button"
			onclick={toggleNew}
			class="whitespace-nowrap rounded border border-transparent px-2 py-1 text-xs text-white"
			style="background-color: var(--color-primary)"
			aria-haspopup="menu"
			aria-expanded={newOpen}
		>
			+ New ▾
		</button>
	</div>

	<div>
		<button
			bind:this={showButtonEl}
			type="button"
			onclick={toggleShow}
			class="whitespace-nowrap rounded border px-2 py-1 text-xs"
			style="border-color: var(--color-border); color: var(--color-fg)"
			aria-haspopup="menu"
			aria-expanded={showOpen}
		>
			Show ▾
		</button>
	</div>
</div>

{#if newOpen}
	<!-- v5.4.1 (#46 item #3): Package above View, with View indented to
	     visually convey the package → view containment relationship. -->
	<div
		role="menu"
		class="z-50 min-w-[160px] rounded border py-1 shadow-lg"
		style="position: fixed; top: {newMenuPos.top}px; left: {newMenuPos.left}px; background-color: var(--color-bg, #fff); border-color: var(--color-border)"
	>
		{#if oncreatepackage}
			<button
				role="menuitem"
				onclick={() => { oncreatepackage?.(); closeAll(); }}
				class="block w-full px-3 py-1 text-left text-xs hover:opacity-80"
				style="color: var(--color-fg)"
			>
				Package
			</button>
		{/if}
		{#if oncreateview}
			<button
				role="menuitem"
				onclick={() => { oncreateview?.(); closeAll(); }}
				class="block w-full px-3 py-1 text-left text-xs hover:opacity-80"
				style="color: var(--color-fg); padding-left: 2rem"
			>
				View
			</button>
		{/if}
		{#if oncreateelement}
			<!-- Issue #191: Element below View, indented to convey the
			     view → element containment hint (a view is composed
			     of elements). -->
			<button
				role="menuitem"
				onclick={() => { oncreateelement?.(); closeAll(); }}
				class="block w-full px-3 py-1 text-left text-xs hover:opacity-80"
				style="color: var(--color-fg); padding-left: 2rem"
			>
				Element
			</button>
		{/if}
	</div>
{/if}

{#if showOpen}
	<div
		role="menu"
		class="z-50 min-w-[180px] rounded border py-1 shadow-lg"
		style="position: fixed; top: {showMenuPos.top}px; left: {showMenuPos.left}px; background-color: var(--color-bg, #fff); border-color: var(--color-border)"
	>
		<!-- v5.4.1 (#46 item #2): "Views" section header above the
		     Diagrams checkbox. Greyed and non-interactive — informs the
		     user that "Diagrams" is a kind of View, since the data model
		     calls them diagrams but the UI calls them Views. -->
		<div
			class="px-4 pb-0.5 pt-1 text-xs uppercase tracking-wide"
			style="color: var(--color-muted); pointer-events: none"
		>
			Views
		</div>
		<label
			class="flex cursor-pointer items-center gap-2 px-3 py-1 text-xs hover:opacity-80"
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
			class="flex cursor-pointer items-center gap-2 px-3 py-1 text-xs hover:opacity-80"
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

{#if newOpen || showOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-40"
		onclick={closeAll}
		onkeydown={(e) => { if (e.key === 'Escape') closeAll(); }}
	></div>
{/if}
