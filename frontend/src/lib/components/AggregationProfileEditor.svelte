<script lang="ts">
	/**
	 * SPEC-212-d: aggregation-profile editor (v6.25.0).
	 *
	 * Reusable component for creating, editing, and deleting
	 * aggregation profiles (ADR-212). Used in two parents:
	 *   - /admin/aggregation-profiles for global profiles.
	 *   - /sets/{id} for set-scoped profiles.
	 *
	 * v1 surface: list + create + delete + edit (JSON textarea with
	 * parse-validate on save). Form-based tabs editor with autocomplete
	 * is a future follow-up — the seeded profiles are good clone
	 * templates.
	 */

	import { apiFetch, ApiError } from '$lib/utils/api';

	interface Props {
		/** When set, only this set's profiles + globals are shown.
		 * Create / edit produces set-scoped profiles. */
		setId?: string | null;
		/** When true, the editor manages globals only — Create produces
		 * is_global=true profiles. */
		globalsMode?: boolean;
	}

	interface AggregationProfile {
		id: string;
		name: string;
		description: string | null;
		set_id: string | null;
		set_name: string | null;
		is_global: boolean;
		is_default_for_set: boolean;
		profile_data: Record<string, unknown>;
		created_by: string | null;
		created_by_username: string;
		created_at: string;
		updated_at: string;
	}

	interface ListResponse {
		items: AggregationProfile[];
		total: number;
		page: number;
		page_size: number;
	}

	let { setId = null, globalsMode = false }: Props = $props();

	let profiles = $state<AggregationProfile[]>([]);
	let loading = $state(true);
	let listError = $state<string | null>(null);

	// Editor state — when editingId is non-null we're editing a row;
	// when creating is true we're creating a new one (blank or cloned).
	let editingId = $state<string | null>(null);
	let creating = $state(false);
	let draftName = $state('');
	let draftDescription = $state('');
	let draftJson = $state('');
	let draftIsDefault = $state(false);
	let draftError = $state<string | null>(null);
	let saving = $state(false);

	// SPEC-212-e (v6.29.0): Clone-from-existing picker state.
	let cloning = $state(false);
	let cloneCandidates = $state<AggregationProfile[]>([]);

	const DEFAULT_PROFILE_JSON = JSON.stringify({
		traversal: {
			inner: {
				collect_token_type: 'element',
				value_attribute_path: 'attributes/Quantity/type',
				bucket_attribute_path: null,
				skip_blank_values: true,
			},
		},
		output: {
			group_by: 'element.package_name',
			sort_groups: 'alpha',
			sort_items_within_group: 'alpha',
			aggregation_fn: 'sum',
			line_format: '- {element.name}: {sum_value}{bucket_spaced}',
			show_per_source_breakdown: false,
			breakdown_format: ' ({sources_joined})',
		},
	}, null, 2);

	$effect(() => {
		// Re-fetch when scope changes.
		void load();
	});

	async function load() {
		loading = true;
		listError = null;
		try {
			const params = new URLSearchParams();
			if (setId) {
				params.set('set_id', setId);
				params.set('include_global', String(globalsMode));
			} else {
				params.set('include_global', 'true');
			}
			const data = await apiFetch<ListResponse>(
				`/api/aggregation/profiles?${params}`,
			);
			profiles = (data.items ?? []).filter((p) => {
				// In set mode, exclude globals; in globals mode, exclude set-scoped.
				if (globalsMode) return p.is_global;
				if (setId) return !p.is_global && p.set_id === setId;
				return true;
			});
		} catch (e) {
			listError = e instanceof ApiError ? e.message : 'Failed to load profiles';
		}
		loading = false;
	}

	function startCreate() {
		creating = true;
		editingId = null;
		cloning = false;
		draftName = '';
		draftDescription = '';
		draftJson = DEFAULT_PROFILE_JSON;
		draftIsDefault = false;
		draftError = null;
	}

	// SPEC-212-e: open the clone-source picker. Candidates are the
	// in-scope profiles already loaded in `profiles`, plus globals when
	// we're in set-mode (so the user can clone from a seeded global
	// into a set-scoped copy).
	async function startClone() {
		cloning = true;
		creating = false;
		editingId = null;
		// In set mode, also fetch globals so the user can clone from
		// a seeded global into a new set-scoped profile.
		if (setId) {
			try {
				const params = new URLSearchParams();
				params.set('set_id', setId);
				params.set('include_global', 'true');
				const data = await apiFetch<ListResponse>(
					`/api/aggregation/profiles?${params}`,
				);
				cloneCandidates = data.items ?? [];
			} catch {
				cloneCandidates = profiles;
			}
		} else {
			cloneCandidates = profiles;
		}
	}

	function cancelClone() {
		cloning = false;
		cloneCandidates = [];
	}

	function commitClone(source: AggregationProfile) {
		creating = true;
		editingId = null;
		cloning = false;
		cloneCandidates = [];
		draftName = `${source.name} (copy)`;
		draftDescription = source.description ?? '';
		draftJson = JSON.stringify(source.profile_data, null, 2);
		draftIsDefault = false;  // copies don't inherit default-for-set
		draftError = null;
	}

	function startEdit(p: AggregationProfile) {
		editingId = p.id;
		creating = false;
		draftName = p.name;
		draftDescription = p.description ?? '';
		draftJson = JSON.stringify(p.profile_data, null, 2);
		draftIsDefault = p.is_default_for_set;
		draftError = null;
	}

	function cancelEdit() {
		creating = false;
		editingId = null;
		draftError = null;
	}

	async function save() {
		if (saving) return;
		draftError = null;
		let parsed: Record<string, unknown>;
		try {
			parsed = JSON.parse(draftJson);
		} catch (e) {
			draftError = `Invalid JSON: ${(e as Error).message}`;
			return;
		}
		if (!draftName.trim()) {
			draftError = 'Name is required';
			return;
		}
		saving = true;
		try {
			if (creating) {
				const body: Record<string, unknown> = {
					name: draftName.trim(),
					description: draftDescription.trim() || null,
					profile_data: parsed,
					is_default_for_set: draftIsDefault,
				};
				if (globalsMode) {
					body.is_global = true;
				} else if (setId) {
					body.set_id = setId;
				}
				await apiFetch('/api/aggregation/profiles', {
					method: 'POST',
					body: JSON.stringify(body),
				});
			} else if (editingId) {
				const body: Record<string, unknown> = {
					name: draftName.trim(),
					description: draftDescription.trim() || null,
					profile_data: parsed,
					is_default_for_set: draftIsDefault,
				};
				await apiFetch(`/api/aggregation/profiles/${editingId}`, {
					method: 'PUT',
					body: JSON.stringify(body),
				});
			}
			cancelEdit();
			await load();
		} catch (e) {
			draftError = e instanceof ApiError ? e.message : 'Failed to save profile';
		}
		saving = false;
	}

	async function remove(p: AggregationProfile) {
		if (!confirm(`Delete profile '${p.name}'? This is reversible (soft delete).`)) {
			return;
		}
		try {
			await apiFetch(`/api/aggregation/profiles/${p.id}`, {
				method: 'DELETE',
			});
			await load();
		} catch (e) {
			listError = e instanceof ApiError ? e.message : 'Failed to delete profile';
		}
	}
</script>

<section class="agg-profile-editor">
	<div class="flex items-center justify-between">
		<h2 class="text-base font-semibold" style="color: var(--color-fg)">
			{globalsMode ? 'Global aggregation profiles' : 'Aggregation profiles for this set'}
		</h2>
		{#if !creating && !editingId && !cloning}
			<div class="flex gap-2">
				<button onclick={startClone} class="rounded px-3 py-1 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
					+ Clone from existing
				</button>
				<button onclick={startCreate} class="rounded px-3 py-1 text-sm text-white" style="background: var(--color-primary)">
					+ New profile
				</button>
			</div>
		{/if}
	</div>
	<p class="mt-1 text-xs" style="color: var(--color-muted)">
		Aggregation profiles describe how to roll up data across a group
		of documents — deduplicated lists with summed quantities, points
		totals, time-tracking rollups, and so on. Pick a seeded profile
		as a starting point with <strong>Clone from existing</strong> and
		duplicate-and-edit it for your use case, or start blank with
		<strong>New profile</strong>.
	</p>

	{#if cloning}
		<div class="mt-3 rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
			<p class="text-sm" style="color: var(--color-fg)">Clone from which profile?</p>
			<div class="mt-2 flex flex-col gap-1">
				{#each cloneCandidates as p (p.id)}
					<button
						onclick={() => commitClone(p)}
						class="rounded px-3 py-2 text-left text-sm"
						style="border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						<span style="color: var(--color-fg)">{p.name}</span>
						{#if p.is_global}
							<span class="ml-2 rounded px-1 text-xs" style="background: var(--color-surface); color: var(--color-muted)">global</span>
						{/if}
						{#if p.description}
							<div class="mt-0.5 text-xs" style="color: var(--color-muted)">{p.description}</div>
						{/if}
					</button>
				{/each}
				{#if cloneCandidates.length === 0}
					<p class="text-xs" style="color: var(--color-muted)">No profiles available to clone.</p>
				{/if}
			</div>
			<div class="mt-3 flex justify-end">
				<button onclick={cancelClone} class="rounded px-3 py-1 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
					Cancel
				</button>
			</div>
		</div>
	{/if}

	{#if listError}
		<p class="mt-3 text-sm" style="color: var(--color-danger)">{listError}</p>
	{/if}

	{#if creating || editingId}
		<div class="mt-4 rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
			<label class="block text-sm font-medium" style="color: var(--color-fg)">
				Name
				<input
					type="text"
					bind:value={draftName}
					required
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</label>
			<label class="mt-3 block text-sm font-medium" style="color: var(--color-fg)">
				Description
				<input
					type="text"
					bind:value={draftDescription}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</label>
			<label class="mt-3 block text-sm font-medium" style="color: var(--color-fg)">
				profile_data (JSON)
				<textarea
					bind:value={draftJson}
					rows="18"
					class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				></textarea>
			</label>
			{#if !globalsMode && setId}
				<label class="mt-3 flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input type="checkbox" bind:checked={draftIsDefault} />
					Default profile for this set
				</label>
			{/if}
			{#if draftError}
				<p class="mt-2 text-sm" style="color: var(--color-danger)">{draftError}</p>
			{/if}
			<div class="mt-3 flex justify-end gap-2">
				<button onclick={cancelEdit} disabled={saving} class="rounded px-4 py-2 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
					Cancel
				</button>
				<button onclick={save} disabled={saving} class="rounded px-4 py-2 text-sm text-white disabled:opacity-50" style="background: var(--color-primary)">
					{saving ? 'Saving…' : (creating ? 'Create profile' : 'Save profile')}
				</button>
			</div>
		</div>
	{/if}

	<div class="mt-4">
		{#if loading}
			<p class="text-sm" style="color: var(--color-muted)">Loading…</p>
		{:else if profiles.length === 0}
			<p class="text-sm" style="color: var(--color-muted)">No profiles yet.</p>
		{:else}
			<table class="w-full text-sm" style="color: var(--color-fg)">
				<thead>
					<tr style="border-bottom: 1px solid var(--color-border)">
						<th class="py-2 pr-4 text-left font-medium" style="color: var(--color-muted)">Name</th>
						<th class="py-2 pr-4 text-left font-medium" style="color: var(--color-muted)">Scope</th>
						<th class="py-2 pr-4 text-left font-medium" style="color: var(--color-muted)">Description</th>
						<th class="py-2 text-right font-medium" style="color: var(--color-muted)"></th>
					</tr>
				</thead>
				<tbody>
					{#each profiles as p (p.id)}
						<tr style="border-bottom: 1px solid var(--color-border)">
							<td class="py-2 pr-4">{p.name}</td>
							<td class="py-2 pr-4">
								{#if p.is_global}
									<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-bg); color: var(--color-fg); border: 1px solid var(--color-border)">Global</span>
								{:else}
									<span class="text-xs" style="color: var(--color-muted)">{p.set_name ?? 'set-scoped'}</span>
								{/if}
							</td>
							<td class="py-2 pr-4 text-xs" style="color: var(--color-muted)">{p.description ?? '—'}</td>
							<td class="py-2 text-right">
								<button onclick={() => startEdit(p)} class="rounded px-2 py-1 text-xs" style="border: 1px solid var(--color-border); color: var(--color-fg)">Edit</button>
								<button onclick={() => remove(p)} class="ml-2 rounded px-2 py-1 text-xs text-white" style="background: var(--color-danger)">Delete</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</section>
