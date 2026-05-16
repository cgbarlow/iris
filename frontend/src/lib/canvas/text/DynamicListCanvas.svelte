<script lang="ts">
	/**
	 * DynamicListCanvas: read-only auto-generated markdown surface
	 * (ADR-186, issue #147).
	 *
	 * The diagram's `data.content` is synthesised on the backend
	 * (ADR-187); the user never edits the text directly. Edit mode
	 * exposes a Source panel with three controls (mode + package +
	 * show_description) that get persisted to `data.dynamic_source`
	 * on Save.
	 */
	import MarkdownView from '$lib/components/MarkdownView.svelte';
	import type { TocHeading } from '$lib/components/markdownHelpers';
	import { apiFetch } from '$lib/api';
	import { onMount } from 'svelte';

	interface PackageOption {
		id: string;
		name: string;
	}

	export interface DynamicSource {
		mode: 'diagram_relationships' | 'package_elements';
		package_id: string | null;
		show_description: boolean;
	}

	interface Props {
		/** Computed markdown — produced by the backend (`data.content`). */
		content: string;
		/** Edit-mode toggle owned by the parent /views page. */
		editing?: boolean;
		/** Set of diagram IDs for muted iris:// link styling. */
		textDiagramIds?: Set<string>;
		/** Called when the heading list updates — feeds the TOC drawer. */
		onheadings?: (headings: TocHeading[]) => void;
		/** Current source-of-truth config. */
		source: DynamicSource;
		/** Set the diagram belongs to — scopes the package picker. */
		setId: string | null;
		/** Fires whenever the user changes mode / package / show_description. */
		onsourcechange?: (next: DynamicSource) => void;
	}

	let {
		content,
		editing = false,
		textDiagramIds,
		onheadings,
		source = $bindable(),
		setId,
		onsourcechange,
	}: Props = $props();

	let packages = $state<PackageOption[]>([]);

	async function loadPackages() {
		if (!setId) {
			packages = [];
			return;
		}
		try {
			const resp = await apiFetch<{ items: PackageOption[] }>(
				`/api/packages?set_id=${encodeURIComponent(setId)}&page_size=100`,
			);
			packages = resp.items ?? [];
		} catch {
			packages = [];
		}
	}

	onMount(loadPackages);

	function setMode(mode: DynamicSource['mode']) {
		source = { ...source, mode };
		onsourcechange?.(source);
	}

	function setPackage(pkgId: string) {
		source = { ...source, package_id: pkgId || null };
		onsourcechange?.(source);
	}

	function setShowDescription(value: boolean) {
		source = { ...source, show_description: value };
		onsourcechange?.(source);
	}
</script>

<div class="dynamic-list-canvas" style="padding: 1rem">
	<MarkdownView
		markdown={content}
		{textDiagramIds}
		{onheadings}
	/>

	{#if editing}
		<details
			open
			class="mt-4 rounded border p-3"
			style="border-color: var(--color-border); background: var(--color-surface)"
		>
			<summary class="cursor-pointer text-sm font-semibold" style="color: var(--color-fg)">
				Source for this list
			</summary>
			<p class="mt-2 text-xs" style="color: var(--color-muted)">
				The bullet list above is auto-generated. Edit the source
				below — the canvas content itself is read-only.
			</p>

			<div class="mt-3 flex flex-col gap-3">
				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<span class="w-40">Mode</span>
					<select
						value={source.mode}
						onchange={(e) =>
							setMode((e.currentTarget as HTMLSelectElement).value as DynamicSource['mode'])}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						<option value="diagram_relationships">Default (diagram relationships)</option>
						<option value="package_elements">Package elements</option>
					</select>
				</label>

				{#if source.mode === 'package_elements'}
					<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
						<span class="w-40">Package</span>
						<select
							value={source.package_id ?? ''}
							onchange={(e) => setPackage((e.currentTarget as HTMLSelectElement).value)}
							class="rounded border px-2 py-1 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						>
							<option value="">(choose a package)</option>
							{#each packages as pkg}
								<option value={pkg.id}>{pkg.name}</option>
							{/each}
						</select>
					</label>
				{/if}

				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input
						type="checkbox"
						checked={source.show_description}
						onchange={(e) =>
							setShowDescription((e.currentTarget as HTMLInputElement).checked)}
					/>
					<span title="Append each element's Description in brackets after its name.">
						Show description
					</span>
				</label>
			</div>
		</details>
	{/if}
</div>
