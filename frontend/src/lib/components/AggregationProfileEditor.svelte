<script lang="ts">
	/**
	 * SPEC-212-d: aggregation-profile editor (v6.25.0).
	 * SPEC-212-e (v6.29.0): clone-from-existing picker.
	 * SPEC-212-f: form-based authoring — output fields lifted out of
	 *   JSON (Option A), `line_format` chip composer with live preview
	 *   (Option B), traversal wizard with attribute-path picker
	 *   (Option C), and a template gallery on "New profile" (Option E).
	 *   The JSON textarea is retained as an "Advanced (JSON)" escape
	 *   hatch — round-tripping through JSON.parse / JSON.stringify so
	 *   power users keep their direct path.
	 *
	 * Used in two parents:
	 *   - /admin/aggregation-profiles for global profiles.
	 *   - /sets/{id} for set-scoped profiles.
	 */

	import { apiFetch, ApiError } from '$lib/utils/api';
	import {
		readOutputFields, patchOutputFields,
		readTraversalFields, patchTraversalFields,
		assembleProfileData,
		buildDraftFromTemplate, buildBlankDraft,
		AGGREGATION_FNS, SORT_MODES,
		type OutputFields, type TraversalFields,
	} from './aggregationProfileHelpers';
	import AggregationTemplateGallery from './AggregationTemplateGallery.svelte';
	import LineFormatComposer from './LineFormatComposer.svelte';
	import TraversalBuilder from './TraversalBuilder.svelte';

	interface Props {
		/** When set, only this set's profiles + globals are shown.
		 * Create / edit produces set-scoped profiles. */
		setId?: string | null;
		/** When true, the editor manages globals only — Create produces
		 * is_global=true profiles. */
		globalsMode?: boolean;
		/** Source smart-markdown diagram id used by the live-preview pane
		 *  in the LineFormatComposer. Caller typically passes the page's
		 *  primary aggregation source; leave null to hide preview. */
		previewSourceDiagramId?: string | null;
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

	let {
		setId = null,
		globalsMode = false,
		previewSourceDiagramId = null,
	}: Props = $props();

	let profiles = $state<AggregationProfile[]>([]);
	let loading = $state(true);
	let listError = $state<string | null>(null);

	// Editor state — when editingId is non-null we're editing a row;
	// when creating is true we're creating a new one (blank or template).
	let editingId = $state<string | null>(null);
	let creating = $state(false);
	let gallery = $state(false);
	let draftName = $state('');
	let draftDescription = $state('');
	let draftJson = $state('');
	let draftIsDefault = $state(false);
	let draftOutput = $state<OutputFields>(readOutputFields(null));
	let draftTraversal = $state<TraversalFields>(readTraversalFields(null));
	let showAdvanced = $state(false);
	let draftError = $state<string | null>(null);
	let saving = $state(false);

	// SPEC-212-e (v6.29.0): clone-from-existing picker (kept as a
	// secondary action alongside the gallery so set-scoped users can
	// still clone an in-scope custom profile).
	let cloning = $state(false);
	let cloneCandidates = $state<AggregationProfile[]>([]);

	// Seeded global profiles for the Option E gallery. Loaded once when
	// the gallery opens — the set is small (5 today) so a single fetch
	// is fine.
	let seededGlobals = $state<AggregationProfile[]>([]);

	$effect(() => {
		void setId;
		void globalsMode;
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
				if (globalsMode) return p.is_global;
				if (setId) return !p.is_global && p.set_id === setId;
				return true;
			});
		} catch (e) {
			listError = e instanceof ApiError ? e.message : 'Failed to load profiles';
		}
		loading = false;
	}

	// Form ↔ JSON sync: when form fields change (the default path), the
	// JSON textarea is regenerated. When the user opens Advanced and
	// edits JSON directly, we parse it on save and let JSON win.
	function syncJsonFromForm() {
		const pd = assembleProfileData(draftOutput, draftTraversal);
		draftJson = JSON.stringify(pd, null, 2);
	}

	async function startGallery() {
		gallery = true;
		creating = false;
		editingId = null;
		cloning = false;
		// Fetch globals to populate the gallery if we haven't already.
		if (seededGlobals.length === 0) {
			try {
				const params = new URLSearchParams();
				params.set('include_global', 'true');
				const data = await apiFetch<ListResponse>(
					`/api/aggregation/profiles?${params}`,
				);
				seededGlobals = (data.items ?? []).filter((p) => p.is_global);
			} catch {
				seededGlobals = [];
			}
		}
	}

	function pickFromGallery(template: { id: string; name: string; description: string | null; profile_data: Record<string, unknown> } | null) {
		gallery = false;
		creating = true;
		editingId = null;
		const draft = template ? buildDraftFromTemplate(template) : buildBlankDraft();
		// For a template clone we want a fresh name (the helper suffixes
		// " (copy)"); for blank we leave it empty so the field highlights.
		draftName = template ? draft.name : '';
		draftDescription = draft.description;
		draftJson = draft.json;
		draftIsDefault = draft.isDefault;
		draftOutput = draft.output;
		draftTraversal = draft.traversal;
		showAdvanced = false;
		draftError = null;
	}

	function cancelGallery() {
		gallery = false;
	}

	// SPEC-212-e: open the clone-source picker. Candidates are in-scope
	// profiles plus globals when we're in set-mode (so a user can clone
	// from a seeded global into a set-scoped copy).
	async function startClone() {
		cloning = true;
		creating = false;
		editingId = null;
		gallery = false;
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
		const draft = buildDraftFromTemplate({
			id: source.id, name: source.name,
			description: source.description,
			profile_data: source.profile_data,
		});
		creating = true;
		editingId = null;
		cloning = false;
		cloneCandidates = [];
		draftName = draft.name;
		draftDescription = draft.description;
		draftJson = draft.json;
		draftIsDefault = draft.isDefault;
		draftOutput = draft.output;
		draftTraversal = draft.traversal;
		showAdvanced = false;
		draftError = null;
	}

	function startEdit(p: AggregationProfile) {
		editingId = p.id;
		creating = false;
		gallery = false;
		cloning = false;
		draftName = p.name;
		draftDescription = p.description ?? '';
		draftJson = JSON.stringify(p.profile_data, null, 2);
		draftIsDefault = p.is_default_for_set;
		draftOutput = readOutputFields(p.profile_data);
		draftTraversal = readTraversalFields(p.profile_data);
		showAdvanced = false;
		draftError = null;
	}

	function cancelEdit() {
		creating = false;
		editingId = null;
		gallery = false;
		cloning = false;
		draftError = null;
	}

	async function save() {
		if (saving) return;
		draftError = null;
		if (!draftName.trim()) {
			draftError = 'Name is required';
			return;
		}
		// Two sources of truth for profile_data:
		//   - Form fields (default) — assemble from draftOutput + draftTraversal.
		//   - Advanced JSON — user may have edited the textarea directly.
		// When Advanced is open we trust the JSON (the user opted in);
		// otherwise we trust the form. JSON-syntax errors keep the
		// editor open with an inline error.
		let parsed: Record<string, unknown>;
		if (showAdvanced) {
			try {
				parsed = JSON.parse(draftJson);
			} catch (e) {
				draftError = `Invalid JSON: ${(e as Error).message}`;
				return;
			}
		} else {
			parsed = assembleProfileData(draftOutput, draftTraversal);
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

	function toggleAdvanced() {
		// Entering advanced mode → serialise current form state into JSON
		// so the textarea matches what would be saved.
		if (!showAdvanced) {
			syncJsonFromForm();
		}
		showAdvanced = !showAdvanced;
	}

	// Live profile_data for the LineFormatComposer preview pane.
	const livePreviewProfile = $derived(
		assembleProfileData(draftOutput, draftTraversal),
	);
</script>

<section class="agg-profile-editor">
	<div class="flex items-center justify-between">
		<h2 class="text-base font-semibold" style="color: var(--color-fg)">
			{globalsMode ? 'Global aggregation profiles' : 'Aggregation profiles for this set'}
		</h2>
		{#if !creating && !editingId && !cloning && !gallery}
			<div class="flex gap-2">
				<button onclick={startClone} class="rounded px-3 py-1 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
					+ Clone from existing
				</button>
				<button onclick={startGallery} class="rounded px-3 py-1 text-sm text-white" style="background: var(--color-primary)">
					+ New profile
				</button>
			</div>
		{/if}
	</div>
	<p class="mt-1 text-xs" style="color: var(--color-muted)">
		Aggregation profiles describe how to roll up data across a group
		of documents — deduplicated lists with summed quantities, points
		totals, time-tracking rollups, and so on. Start with
		<strong>New profile</strong> to pick a template, or
		<strong>Clone from existing</strong> to duplicate one you've already
		customised.
	</p>

	{#if gallery}
		<div class="mt-3">
			<AggregationTemplateGallery
				seededProfiles={seededGlobals}
				onpick={pickFromGallery}
				oncancel={cancelGallery}
			/>
		</div>
	{/if}

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

			<!-- Option A: lifted output fields -->
			<h3 class="mt-4 text-sm font-semibold" style="color: var(--color-fg)">Output</h3>
			<div class="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
				<label class="block text-sm font-medium" style="color: var(--color-fg)">
					Aggregation
					<select
						bind:value={draftOutput.aggregation_fn}
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						{#each AGGREGATION_FNS as fn (fn)}
							<option value={fn}>{fn}</option>
						{/each}
					</select>
				</label>
				<label class="block text-sm font-medium" style="color: var(--color-fg)">
					Group by
					<input
						type="text"
						bind:value={draftOutput.group_by}
						placeholder="element.package_name"
						class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					/>
					<span class="mt-1 block text-xs" style="color: var(--color-muted)">
						<code>element.name</code>, <code>element.package_name</code>, <code>element.attributes.&lt;Name&gt;/type</code>, or leave blank for ungrouped.
					</span>
				</label>
				<label class="block text-sm font-medium" style="color: var(--color-fg)">
					Sort groups
					<select
						bind:value={draftOutput.sort_groups}
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						{#each SORT_MODES as m (m)}
							<option value={m}>{m}</option>
						{/each}
					</select>
				</label>
				<label class="block text-sm font-medium" style="color: var(--color-fg)">
					Sort items within group
					<select
						bind:value={draftOutput.sort_items_within_group}
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						{#each SORT_MODES as m (m)}
							<option value={m}>{m}</option>
						{/each}
					</select>
				</label>
			</div>

			<!-- Option B: line_format chip composer + preview -->
			<div class="mt-3">
				<LineFormatComposer
					bind:value={draftOutput.line_format}
					profileData={livePreviewProfile}
					sourceDiagramId={previewSourceDiagramId}
				/>
			</div>

			<label class="mt-3 flex items-start gap-2 text-sm" style="color: var(--color-fg)">
				<input type="checkbox" bind:checked={draftOutput.show_per_source_breakdown} class="mt-1" />
				<span>
					<span class="font-medium">Show per-source breakdown</span>
					<span class="block text-xs" style="color: var(--color-muted)">
						Append a parenthetical showing how each contributing source
						added up.
					</span>
				</span>
			</label>
			{#if draftOutput.show_per_source_breakdown}
				<label class="mt-2 block text-sm font-medium" style="color: var(--color-fg)">
					Breakdown format
					<input
						type="text"
						bind:value={draftOutput.breakdown_format}
						placeholder={' ({sources_joined})'}
						class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					/>
				</label>
			{/if}
			<label class="mt-3 flex items-start gap-2 text-sm" style="color: var(--color-fg)">
				<input type="checkbox" bind:checked={draftOutput.include_provenance} class="mt-1" />
				<span>
					<span class="font-medium">Include provenance comments</span>
					<span class="block text-xs" style="color: var(--color-muted)">
						When on, each aggregated line is rendered with a trailing HTML
						comment carrying the source element id, e.g. <code>&lt;!-- iris:element=… --&gt;</code>.
						Required by downstream orchestrators that need to map output
						lines back to elements (ADR-217).
					</span>
				</span>
			</label>

			<!-- Option C: traversal wizard -->
			<h3 class="mt-4 text-sm font-semibold" style="color: var(--color-fg)">Traversal</h3>
			<div class="mt-2">
				<TraversalBuilder bind:fields={draftTraversal} />
			</div>

			<!-- Advanced (JSON) escape hatch -->
			<details class="mt-4 rounded border p-2" style="border-color: var(--color-border); background: var(--color-bg)">
				<summary
					class="cursor-pointer text-sm font-medium"
					style="color: var(--color-fg)"
					onclick={toggleAdvanced}
				>
					Advanced (JSON)
				</summary>
				<label class="mt-2 block text-sm font-medium" style="color: var(--color-fg)">
					profile_data (JSON)
					<textarea
						bind:value={draftJson}
						rows="14"
						class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					></textarea>
					<span class="mt-1 block text-xs" style="color: var(--color-muted)">
						When this section is open, the JSON is authoritative on save —
						the form fields above are ignored. Use this for fields the
						form doesn't surface yet.
					</span>
				</label>
			</details>

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
