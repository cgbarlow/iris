<script lang="ts">
	/**
	 * SPEC-212-f: form-based traversal builder (Option C).
	 *
	 * Two-step wizard for the `traversal` half of a profile:
	 *   Step 1 — optional outer source (with optional multiplier).
	 *   Step 2 — inner items (value path + bucket path + skip-blank).
	 *
	 * Replaces the JSON-only authoring path for traversal. The
	 * attribute-path inputs autocomplete via AttributePathPicker when an
	 * example element is available; otherwise they fall back to a plain
	 * text field (e.g. globals-mode authoring).
	 */

	import AttributePathPicker from './AttributePathPicker.svelte';
	import { TOKEN_TYPES, type TraversalFields } from './aggregationProfileHelpers';

	interface Props {
		fields: TraversalFields;
		/** Pre-selected example element id used to seed AttributePathPicker
		 *  drill-mode. Null in globals authoring → text-only input. */
		exampleElementId?: string | null;
	}

	let { fields = $bindable(), exampleElementId = null }: Props = $props();
</script>

<div class="traversal-builder">
	<details open class="rounded border p-3" style="border-color: var(--color-border); background: var(--color-bg)">
		<summary class="cursor-pointer text-sm font-medium" style="color: var(--color-fg)">
			Source container (optional)
		</summary>
		<label class="mt-3 flex items-start gap-2 text-sm" style="color: var(--color-fg)">
			<input type="checkbox" bind:checked={fields.has_outer} class="mt-1" />
			<span>
				<span class="font-medium">These items live inside a parent container</span>
				<span class="block text-xs" style="color: var(--color-muted)">
					Turn this on when the source diagram references other
					diagrams whose contents should be summed together. Leave
					off for a one-level walk.
				</span>
			</span>
		</label>
		{#if fields.has_outer}
			<label class="mt-3 block text-sm font-medium" style="color: var(--color-fg)">
				Container token type
				<select
					bind:value={fields.outer_token_type}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					{#each TOKEN_TYPES as t (t)}
						<option value={t}>{t}</option>
					{/each}
				</select>
			</label>
			<label class="mt-3 flex items-start gap-2 text-sm" style="color: var(--color-fg)">
				<input type="checkbox" bind:checked={fields.has_multiplier} class="mt-1" />
				<span>
					<span class="font-medium">Scale items by a per-container multiplier</span>
					<span class="block text-xs" style="color: var(--color-muted)">
						Numerator is a per-use override on the container; divisor
						is read from the container's diagram data.
					</span>
				</span>
			</label>
			{#if fields.has_multiplier}
				<div class="mt-2 rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
					<label class="block text-sm font-medium" style="color: var(--color-fg)">
						Numerator attribute (override on the container token)
						<input
							type="text"
							bind:value={fields.multiplier.from_attribute_override}
							placeholder="attributes/<Name>/type"
							class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
					</label>
					<label class="mt-3 block text-sm font-medium" style="color: var(--color-fg)">
						Divisor (path on the container's diagram data)
						<input
							type="text"
							bind:value={fields.multiplier.divisor_from_diagram_data}
							placeholder="data.<field>"
							class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
					</label>
					<label class="mt-3 block text-sm font-medium" style="color: var(--color-fg)">
						Default multiplier (when no override is set)
						<input
							type="number"
							step="0.01"
							bind:value={fields.multiplier.default_multiplier}
							class="mt-1 w-full rounded border px-3 py-2 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
					</label>
				</div>
			{/if}
		{/if}
	</details>

	<details open class="mt-3 rounded border p-3" style="border-color: var(--color-border); background: var(--color-bg)">
		<summary class="cursor-pointer text-sm font-medium" style="color: var(--color-fg)">
			Inner items
		</summary>
		<label class="mt-3 block text-sm font-medium" style="color: var(--color-fg)">
			Inner token type
			<select
				bind:value={fields.inner_token_type}
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>
				{#each TOKEN_TYPES as t (t)}
					<option value={t}>{t}</option>
				{/each}
			</select>
		</label>
		<div class="mt-3">
			<AttributePathPicker
				bind:value={fields.inner_value_path}
				{exampleElementId}
				label="Value attribute path"
				placeholder="e.g. attributes/Quantity/type"
			/>
		</div>
		<div class="mt-3">
			<AttributePathPicker
				bind:value={fields.inner_bucket_path}
				{exampleElementId}
				label="Bucket attribute path (optional)"
				placeholder="e.g. attributes/Unit/type"
			/>
		</div>
		<label class="mt-3 flex items-start gap-2 text-sm" style="color: var(--color-fg)">
			<input type="checkbox" bind:checked={fields.skip_blank_values} class="mt-1" />
			<span>
				<span class="font-medium">Skip blank values</span>
				<span class="block text-xs" style="color: var(--color-muted)">
					When on, tokens without a value contribute nothing to the
					total. When off, blanks count as zero.
				</span>
			</span>
		</label>
	</details>
</div>
