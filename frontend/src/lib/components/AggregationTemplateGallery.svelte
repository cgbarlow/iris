<script lang="ts">
	/**
	 * SPEC-212-f: card-grid template gallery (Option E).
	 *
	 * Shown when the user clicks "New profile". Surfaces seeded global
	 * profiles (Shopping list, Sprint points, Time tracker, Expense
	 * report, Reading log per m077) as cards plus a "Blank" card.
	 * Selecting a card hands the chosen profile (or null for blank)
	 * back to the parent for form pre-population.
	 *
	 * Grid CSS mirrors EntityImagesEditor's pattern (DRY §13) — same
	 * `auto-fill` / `minmax` shape, just tuned for card width.
	 */

	interface SeededProfile {
		id: string;
		name: string;
		description: string | null;
		profile_data: Record<string, unknown>;
	}

	interface Props {
		seededProfiles: SeededProfile[];
		onpick: (profile: SeededProfile | null) => void;
		oncancel: () => void;
	}

	let { seededProfiles, onpick, oncancel }: Props = $props();

	function previewLineFormat(p: SeededProfile): string {
		const output = p.profile_data?.output as Record<string, unknown> | undefined;
		const fmt = output?.line_format;
		return typeof fmt === 'string' ? fmt : '';
	}
</script>

<div class="agg-gallery rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
	<div class="flex items-center justify-between">
		<p class="text-sm font-medium" style="color: var(--color-fg)">
			Pick a template to start from
		</p>
		<button
			onclick={oncancel}
			class="text-xs"
			style="color: var(--color-muted)"
		>
			Cancel
		</button>
	</div>
	<p class="mt-1 text-xs" style="color: var(--color-muted)">
		These ship with Iris — each one is a complete, working profile you
		can edit. Pick the closest match and tweak; pick Blank to build
		from scratch.
	</p>

	<div class="agg-gallery__grid mt-3">
		<button
			onclick={() => onpick(null)}
			class="agg-gallery__card text-left"
			style="border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<p class="font-medium">Blank</p>
			<p class="mt-1 text-xs" style="color: var(--color-muted)">
				Start with sensible defaults — element-collecting, sum-by-package.
			</p>
		</button>

		{#each seededProfiles as p (p.id)}
			<button
				onclick={() => onpick(p)}
				class="agg-gallery__card text-left"
				style="border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>
				<p class="font-medium">{p.name}</p>
				{#if p.description}
					<p class="mt-1 text-xs" style="color: var(--color-muted)">{p.description}</p>
				{/if}
				{#if previewLineFormat(p)}
					<p class="mt-2 truncate font-mono text-xs" style="color: var(--color-muted)" title={previewLineFormat(p)}>
						{previewLineFormat(p)}
					</p>
				{/if}
			</button>
		{/each}
	</div>
</div>

<style>
	.agg-gallery__grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 0.75rem;
	}
	.agg-gallery__card {
		border-radius: 0.375rem;
		padding: 0.75rem;
		cursor: pointer;
		transition: transform 0.05s;
	}
	.agg-gallery__card:hover {
		transform: translateY(-1px);
	}
</style>
