<script lang="ts">
	/**
	 * Admin Views page — CRUD for admin-configurable views.
	 * Views control which UI features are visible across the application.
	 */
	import { apiFetch } from '$lib/utils/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

	interface ViewConfig {
		toolbar: Record<string, unknown>;
		metadata: Record<string, unknown>;
		canvas: Record<string, unknown>;
	}

	interface View {
		id: string;
		name: string;
		description: string | null;
		config: ViewConfig;
		is_default: boolean;
		created_at: string;
		updated_at: string;
	}

	let views = $state<View[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Edit/create state
	let editing = $state<View | null>(null);
	let creating = $state(false);
	let editName = $state('');
	let editDescription = $state('');
	let editConfigJson = $state('');
	let saving = $state(false);

	// Delete state
	let deleteTarget = $state<View | null>(null);

	$effect(() => { loadViews(); });

	async function loadViews() {
		loading = true;
		error = null;
		try {
			views = await apiFetch<View[]>('/api/views');
		} catch {
			error = 'Failed to load views';
		}
		loading = false;
	}

	function startCreate() {
		creating = true;
		editing = null;
		editName = '';
		editDescription = '';
		editConfigJson = JSON.stringify({
			toolbar: { element_types: [], relationship_types: [], show_routing_type: true, show_edge_properties: true },
			metadata: { show_overview: true, show_details: true, show_extended: true },
			canvas: { show_cardinality: true, show_role_names: true, show_stereotypes: true, show_description_on_nodes: true },
		}, null, 2);
	}

	function startEdit(view: View) {
		creating = false;
		editing = view;
		editName = view.name;
		editDescription = view.description ?? '';
		editConfigJson = JSON.stringify(view.config, null, 2);
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
				await apiFetch('/api/views', {
					method: 'POST',
					body: JSON.stringify({ name: editName, description: editDescription || null, config }),
				});
			} else if (editing) {
				await apiFetch(`/api/views/${editing.id}`, {
					method: 'PUT',
					body: JSON.stringify({ name: editName, description: editDescription || null, config }),
				});
			}
			await loadViews();
			cancelEdit();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save';
		}
		saving = false;
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		try {
			await apiFetch(`/api/views/${deleteTarget.id}`, { method: 'DELETE' });
			await loadViews();
		} catch {
			error = 'Cannot delete default views';
		}
		deleteTarget = null;
	}
</script>

<svelte:head>
	<title>Admin — Views — Iris</title>
</svelte:head>

<div class="mx-auto max-w-4xl p-6">
	<div class="mb-6 flex items-center justify-between">
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Views</h1>
		<button
			class="rounded px-3 py-1.5 text-sm text-white"
			style="background-color: var(--color-primary)"
			onclick={startCreate}
		>
			New View
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
				{creating ? 'New View' : `Edit: ${editing?.name}`}
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
					<label class="mb-1 block text-sm font-medium" style="color: var(--color-muted)">Config (JSON)</label>
					<textarea
						bind:value={editConfigJson}
						rows="12"
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
		<p style="color: var(--color-muted)">Loading views...</p>
	{:else}
		<div class="space-y-3">
			{#each views as view}
				<div class="flex items-center justify-between rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
					<div>
						<span class="font-medium" style="color: var(--color-fg)">{view.name}</span>
						{#if view.is_default}
							<span class="ml-2 rounded-full px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">Default</span>
						{/if}
						{#if view.description}
							<p class="mt-1 text-sm" style="color: var(--color-muted)">{view.description}</p>
						{/if}
					</div>
					<div class="flex gap-2">
						<button
							class="rounded px-2 py-1 text-xs"
							style="background: var(--color-bg); color: var(--color-fg); border: 1px solid var(--color-border)"
							onclick={() => startEdit(view)}
						>
							Edit
						</button>
						{#if !view.is_default}
							<button
								class="rounded px-2 py-1 text-xs"
								style="background: var(--color-bg); color: var(--color-danger); border: 1px solid var(--color-border)"
								onclick={() => { deleteTarget = view; }}
							>
								Delete
							</button>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<ConfirmDialog
	open={!!deleteTarget}
	title="Delete View"
	message="Are you sure you want to delete this view? This action cannot be undone."
	confirmLabel="Delete"
	onconfirm={confirmDelete}
	oncancel={() => { deleteTarget = null; }}
/>
