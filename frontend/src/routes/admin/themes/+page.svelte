<script lang="ts">
	/**
	 * Admin Themes page — CRUD for visual themes.
	 * Themes control element/edge colours per notation.
	 */
	import { apiFetch } from '$lib/utils/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

	interface ThemeConfig {
		element_defaults: Record<string, Record<string, unknown>>;
		stereotype_overrides: Record<string, Record<string, unknown>>;
		edge_defaults: Record<string, Record<string, unknown>>;
		global: Record<string, unknown>;
	}

	interface Theme {
		id: string;
		name: string;
		description: string | null;
		notation: string;
		config: ThemeConfig;
		is_default: boolean;
		created_at: string;
		updated_at: string;
	}

	let themes = $state<Theme[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Edit/create state
	let editing = $state<Theme | null>(null);
	let creating = $state(false);
	let editName = $state('');
	let editDescription = $state('');
	let editNotation = $state('uml');
	let editConfigJson = $state('');
	let saving = $state(false);

	// Delete state
	let deleteTarget = $state<Theme | null>(null);

	$effect(() => { loadThemes(); });

	async function loadThemes() {
		loading = true;
		error = null;
		try {
			themes = await apiFetch<Theme[]>('/api/themes');
		} catch {
			error = 'Failed to load themes';
		}
		loading = false;
	}

	const notations = ['simple', 'uml', 'archimate', 'c4'];

	const groupedThemes = $derived(
		notations.map((n) => ({
			notation: n,
			themes: themes.filter((t) => t.notation === n),
		})).filter((g) => g.themes.length > 0)
	);

	function startCreate() {
		creating = true;
		editing = null;
		editName = '';
		editDescription = '';
		editNotation = 'uml';
		editConfigJson = JSON.stringify({
			element_defaults: {},
			stereotype_overrides: {},
			edge_defaults: {},
			global: { defaultBgColor: '#ffffff', defaultBorderColor: '#333333', defaultFontColor: '#000000' },
		}, null, 2);
	}

	function startEdit(theme: Theme) {
		creating = false;
		editing = theme;
		editName = theme.name;
		editDescription = theme.description ?? '';
		editNotation = theme.notation;
		editConfigJson = JSON.stringify(theme.config, null, 2);
	}

	function cancelEdit() {
		editing = null;
		creating = false;
	}

	async function save() {
		saving = true;
		error = null;
		try {
			const config = JSON.parse(editConfigJson);
			if (creating) {
				await apiFetch('/api/themes', {
					method: 'POST',
					body: JSON.stringify({ name: editName, description: editDescription || null, notation: editNotation, config }),
				});
			} else if (editing) {
				await apiFetch(`/api/themes/${editing.id}`, {
					method: 'PUT',
					body: JSON.stringify({ name: editName, description: editDescription || null, notation: editNotation, config }),
				});
			}
			await loadThemes();
			cancelEdit();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save';
		}
		saving = false;
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		try {
			await apiFetch(`/api/themes/${deleteTarget.id}`, { method: 'DELETE' });
			await loadThemes();
		} catch {
			error = 'Cannot delete default themes';
		}
		deleteTarget = null;
	}
</script>

<svelte:head>
	<title>Admin — Themes — Iris</title>
</svelte:head>

<div class="mx-auto max-w-4xl p-6">
	<div class="mb-6 flex items-center justify-between">
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Themes</h1>
		<button
			class="rounded px-3 py-1.5 text-sm text-white"
			style="background-color: var(--color-primary)"
			onclick={startCreate}
		>
			New Theme
		</button>
	</div>

	{#if error}
		<div class="mb-4 rounded border p-3" role="alert" style="border-color: var(--color-danger); color: var(--color-danger)">
			{error}
		</div>
	{/if}

	{#if creating || editing}
		<div class="mb-6 rounded border p-4" style="border-color: var(--color-border); background: var(--color-surface)">
			<h2 class="mb-3 text-lg font-semibold" style="color: var(--color-fg)">
				{creating ? 'New Theme' : `Edit: ${editing?.name}`}
			</h2>
			<div class="space-y-3">
				<div>
					<label class="mb-1 block text-sm font-medium" style="color: var(--color-muted)">Name</label>
					<input
						type="text"
						bind:value={editName}
						class="w-full rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					/>
				</div>
				<div>
					<label class="mb-1 block text-sm font-medium" style="color: var(--color-muted)">Description</label>
					<input
						type="text"
						bind:value={editDescription}
						class="w-full rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					/>
				</div>
				<div>
					<label class="mb-1 block text-sm font-medium" style="color: var(--color-muted)">Notation</label>
					<select
						bind:value={editNotation}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						{#each notations as n}
							<option value={n}>{n.toUpperCase()}</option>
						{/each}
					</select>
				</div>
				<div>
					<label class="mb-1 block text-sm font-medium" style="color: var(--color-muted)">Config (JSON)</label>
					<textarea
						bind:value={editConfigJson}
						rows="16"
						class="w-full rounded border px-2 py-1 font-mono text-xs"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					></textarea>
				</div>
				<div class="flex gap-2">
					<button
						class="rounded px-3 py-1.5 text-sm"
						style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)"
						onclick={cancelEdit}
					>
						Cancel
					</button>
					<button
						class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
						style="background-color: var(--color-primary)"
						disabled={!editName || saving}
						onclick={save}
					>
						{saving ? 'Saving...' : 'Save'}
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if loading}
		<p style="color: var(--color-muted)">Loading themes...</p>
	{:else}
		{#each groupedThemes as group}
			<h2 class="mb-2 mt-4 text-lg font-semibold" style="color: var(--color-fg)">{group.notation.toUpperCase()}</h2>
			<div class="space-y-3">
				{#each group.themes as theme}
					<div class="flex items-center justify-between rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
						<div>
							<span class="font-medium" style="color: var(--color-fg)">{theme.name}</span>
							{#if theme.is_default}
								<span class="ml-2 rounded-full px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">Default</span>
							{/if}
							{#if theme.description}
								<p class="mt-1 text-sm" style="color: var(--color-muted)">{theme.description}</p>
							{/if}
						</div>
						<div class="flex gap-2">
							<button
								class="rounded px-2 py-1 text-xs"
								style="background: var(--color-bg); color: var(--color-fg); border: 1px solid var(--color-border)"
								onclick={() => startEdit(theme)}
							>
								Edit
							</button>
							{#if !theme.is_default}
								<button
									class="rounded px-2 py-1 text-xs"
									style="background: var(--color-bg); color: var(--color-danger); border: 1px solid var(--color-border)"
									onclick={() => { deleteTarget = theme; }}
								>
									Delete
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/each}
	{/if}
</div>

<ConfirmDialog
	open={!!deleteTarget}
	title="Delete Theme"
	message="Are you sure you want to delete this theme? This action cannot be undone."
	confirmLabel="Delete"
	onconfirm={confirmDelete}
	oncancel={() => { deleteTarget = null; }}
/>
