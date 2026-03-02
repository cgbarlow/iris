<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiFetch } from '$lib/utils/api';
	import { getAccessToken } from '$lib/stores/auth.svelte.js';
	import type { IrisSet, Model, PaginatedResponse } from '$lib/types/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import DOMPurify from 'dompurify';

	let set = $state<IrisSet | null>(null);
	let models = $state<Model[]>([]);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let successMsg = $state<string | null>(null);

	let name = $state('');
	let description = $state('');
	let thumbnailSource = $state<'model' | 'image' | null>(null);
	let thumbnailModelId = $state<string | null>(null);
	let thumbnailFile = $state<File | null>(null);

	let showDeleteDialog = $state(false);
	let deleting = $state(false);

	let setId = $derived(page.params.id);

	$effect(() => {
		loadSet();
	});

	async function loadSet() {
		loading = true;
		error = null;
		try {
			const [setData, modelsData] = await Promise.all([
				apiFetch<IrisSet>(`/api/sets/${setId}`),
				apiFetch<PaginatedResponse<Model>>(`/api/models?set_id=${setId}&page_size=100`),
			]);
			set = setData;
			models = modelsData.items;

			// Initialize form state
			name = setData.name;
			description = setData.description ?? '';
			thumbnailSource = setData.thumbnail_source;
			thumbnailModelId = setData.thumbnail_model_id;
		} catch {
			error = 'Failed to load set';
		}
		loading = false;
	}

	async function handleSave() {
		saving = true;
		error = null;
		successMsg = null;
		try {
			const sanitizedName = DOMPurify.sanitize(name.trim());
			const sanitizedDesc = description.trim()
				? DOMPurify.sanitize(description.trim())
				: null;

			await apiFetch<IrisSet>(`/api/sets/${setId}`, {
				method: 'PUT',
				body: JSON.stringify({
					name: sanitizedName,
					description: sanitizedDesc,
					thumbnail_source: thumbnailSource,
					thumbnail_model_id: thumbnailSource === 'model' ? thumbnailModelId : null,
				}),
			});

			// Upload image if user selected one and source is 'image'
			if (thumbnailSource === 'image' && thumbnailFile) {
				const formData = new FormData();
				formData.append('file', thumbnailFile);

				const token = getAccessToken();
				const resp = await fetch(`/api/sets/${setId}/thumbnail`, {
					method: 'POST',
					headers: token ? { Authorization: `Bearer ${token}` } : {},
					body: formData,
				});
				if (!resp.ok) {
					const detail = await resp.json().catch(() => ({ detail: 'Upload failed' }));
					throw new Error(detail.detail || 'Upload failed');
				}
			}

			successMsg = 'Set saved successfully';
			await loadSet();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save set';
		}
		saving = false;
	}

	async function handleForceDelete() {
		deleting = true;
		error = null;
		try {
			await apiFetch<{ models_deleted: number; entities_deleted: number }>(
				`/api/sets/${setId}?force=true`,
				{ method: 'DELETE' }
			);
			await goto('/sets');
		} catch {
			error = 'Failed to delete set';
		}
		deleting = false;
		showDeleteDialog = false;
	}

	function handleFileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0] ?? null;
		if (file) {
			if (file.size > 2 * 1024 * 1024) {
				error = 'Image must be under 2 MB';
				return;
			}
			if (!['image/png', 'image/jpeg'].includes(file.type)) {
				error = 'Only PNG and JPEG images are accepted';
				return;
			}
			thumbnailFile = file;
			error = null;
		}
	}
</script>

<svelte:head>
	<title>{set?.name ?? 'Set'} — Iris</title>
</svelte:head>

{#if loading}
	<p style="color: var(--color-muted)">Loading set...</p>
{:else if error && !set}
	<div role="alert" style="color: var(--color-danger)">{error}</div>
{:else if set}
	<div class="flex items-center gap-3">
		<a href="/sets" class="text-sm" style="color: var(--color-primary)">Sets</a>
		<span style="color: var(--color-muted)">/</span>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{set.name}</h1>
	</div>

	{#if error}
		<div role="alert" class="mt-3" style="color: var(--color-danger)">{error}</div>
	{/if}
	{#if successMsg}
		<div class="mt-3" style="color: var(--color-primary)" role="status">{successMsg}</div>
	{/if}

	<form
		onsubmit={(e) => { e.preventDefault(); handleSave(); }}
		class="mt-6"
		style="max-width: 600px"
	>
		<!-- Name -->
		<div>
			<label for="set-edit-name" class="text-sm font-medium" style="color: var(--color-fg)">
				Name <span style="color: var(--color-danger)">*</span>
			</label>
			<input
				id="set-edit-name"
				bind:value={name}
				type="text"
				required
				maxlength="255"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<!-- Description -->
		<div class="mt-4">
			<label for="set-edit-description" class="text-sm font-medium" style="color: var(--color-fg)">
				Description
			</label>
			<textarea
				id="set-edit-description"
				bind:value={description}
				rows="3"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			></textarea>
		</div>

		<!-- Thumbnail -->
		<fieldset class="mt-6">
			<legend class="text-sm font-medium" style="color: var(--color-fg)">Thumbnail</legend>
			<div class="mt-2 flex flex-col gap-2">
				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input
						type="radio"
						name="thumbnail-source"
						value=""
						checked={thumbnailSource === null}
						onchange={() => { thumbnailSource = null; }}
					/>
					No thumbnail
				</label>
				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input
						type="radio"
						name="thumbnail-source"
						value="model"
						checked={thumbnailSource === 'model'}
						onchange={() => { thumbnailSource = 'model'; }}
					/>
					Use model thumbnail
				</label>
				{#if thumbnailSource === 'model'}
					<div class="ml-6">
						<select
							bind:value={thumbnailModelId}
							class="rounded border px-3 py-1.5 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						>
							<option value={null}>Select a model...</option>
							{#each models as model}
								<option value={model.id}>{model.name}</option>
							{/each}
						</select>
					</div>
				{/if}
				<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
					<input
						type="radio"
						name="thumbnail-source"
						value="image"
						checked={thumbnailSource === 'image'}
						onchange={() => { thumbnailSource = 'image'; }}
					/>
					Upload image
				</label>
				{#if thumbnailSource === 'image'}
					<div class="ml-6">
						<input
							type="file"
							accept="image/png,image/jpeg"
							onchange={handleFileInput}
							class="text-sm"
							style="color: var(--color-fg)"
						/>
						<p class="mt-1 text-xs" style="color: var(--color-muted)">PNG or JPEG, max 2 MB</p>
					</div>
				{/if}
			</div>
		</fieldset>

		<!-- Save button -->
		<div class="mt-6">
			<button
				type="submit"
				disabled={saving || !name.trim()}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-primary)"
			>
				{saving ? 'Saving...' : 'Save Changes'}
			</button>
		</div>
	</form>

	<!-- Info -->
	<div class="mt-6 text-sm" style="color: var(--color-muted); max-width: 600px">
		<p>{set.model_count} model{set.model_count !== 1 ? 's' : ''}, {set.entity_count} entit{set.entity_count !== 1 ? 'ies' : 'y'} in this set</p>
	</div>

	<!-- Danger zone -->
	<div
		class="mt-8 rounded border p-4"
		style="border-color: var(--color-danger); max-width: 600px"
	>
		<h2 class="text-sm font-bold" style="color: var(--color-danger)">Danger Zone</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			This will permanently delete this set and all {set.model_count} model{set.model_count !== 1 ? 's' : ''} and {set.entity_count} entit{set.entity_count !== 1 ? 'ies' : 'y'} within it.
		</p>
		<button
			onclick={() => (showDeleteDialog = true)}
			class="mt-3 rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-danger)"
		>
			Delete Set and All Contents
		</button>
	</div>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Set"
		message="Are you sure you want to delete &quot;{set.name}&quot; and all its contents? This will delete {set.model_count} model{set.model_count !== 1 ? 's' : ''} and {set.entity_count} entit{set.entity_count !== 1 ? 'ies' : 'y'}. This action cannot be undone."
		confirmLabel={deleting ? 'Deleting...' : 'Delete Everything'}
		onconfirm={handleForceDelete}
		oncancel={() => (showDeleteDialog = false)}
	/>
{/if}
