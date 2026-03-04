<script lang="ts">
	/** SparxEA import page — upload .qea files to import diagrams, elements, and relationships. */
	import { goto } from '$app/navigation';
	import { getAccessToken } from '$lib/stores/auth.svelte.js';
	import { setActiveSet } from '$lib/stores/activeSet.svelte.js';
	import { apiFetch } from '$lib/utils/api';
	import type { IrisSet } from '$lib/types/api';
	import SetSelector from '$lib/components/SetSelector.svelte';
	import SetDialog from '$lib/components/SetDialog.svelte';

	interface ImportWarning {
		category: string;
		message: string;
	}

	interface ImportSummary {
		packages_created: number;
		packages_skipped: number;
		elements_created: number;
		relationships_created: number;
		diagrams_created: number;
		diagrams_skipped: number;
		elements_skipped: number;
		connectors_skipped: number;
		warnings: ImportWarning[];
	}

	let dragOver = $state(false);
	let uploading = $state(false);
	let progress = $state(0);
	let error = $state<string | null>(null);
	let summary = $state<ImportSummary | null>(null);
	let selectedFile = $state<File | null>(null);
	let fileInputEl: HTMLInputElement | undefined = $state();
	let importSetId = $state('');
	let importSetName = $state('');
	let showCreateSetDialog = $state(false);
	let selectorRef: { reload: () => Promise<void> } | undefined = $state();

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		dragOver = true;
	}

	function handleDragLeave() {
		dragOver = false;
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragOver = false;
		const files = event.dataTransfer?.files;
		if (files && files.length > 0) {
			selectFile(files[0]);
		}
	}

	function handleFileInput(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			selectFile(input.files[0]);
		}
	}

	function selectFile(file: File) {
		if (!file.name.endsWith('.qea')) {
			error = 'Only .qea files (SparxEA) are supported.';
			return;
		}
		error = null;
		summary = null;
		selectedFile = file;
	}

	async function uploadFile() {
		if (!selectedFile) return;
		uploading = true;
		progress = 0;
		error = null;
		summary = null;

		try {
			const formData = new FormData();
			formData.append('file', selectedFile);
			if (importSetId) formData.append('set_id', importSetId);

			progress = 20;

			const token = getAccessToken();
			const response = await fetch('/api/import/sparx', {
				method: 'POST',
				headers: token ? { Authorization: `Bearer ${token}` } : {},
				body: formData,
			});

			progress = 80;

			if (!response.ok) {
				const detail = await response.json().catch(() => null);
				throw new Error(detail?.detail || `Import failed (${response.status})`);
			}

			summary = await response.json();
			progress = 100;
			selectedFile = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Import failed';
		}

		uploading = false;
	}

	function resetForm() {
		selectedFile = null;
		summary = null;
		error = null;
		progress = 0;
		if (fileInputEl) fileInputEl.value = '';
	}

	async function handleCreateSet(name: string, description: string | null) {
		try {
			const created = await apiFetch<IrisSet>('/api/sets', {
				method: 'POST',
				body: JSON.stringify({ name, description }),
			});
			showCreateSetDialog = false;
			importSetId = created.id;
			importSetName = created.name;
			await selectorRef?.reload();
		} catch {
			error = 'Failed to create set';
		}
	}

	function handleSetChange(id: string, name?: string) {
		importSetId = id;
		importSetName = name ?? '';
	}
</script>

<svelte:head>
	<title>Import — Iris</title>
</svelte:head>

<div>
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Import</h1>
	<p class="mt-2" style="color: var(--color-muted)">
		Import diagrams from SparxEA (.qea) files.
	</p>
</div>

{#if summary}
	<!-- Import Results -->
	<div class="mt-6 rounded border p-6" style="border-color: var(--color-border); background: var(--color-surface)">
		<h2 class="text-lg font-bold" style="color: var(--color-fg)">Import Complete</h2>
		<div class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-primary)">{summary.diagrams_created}</p>
				<p class="text-sm" style="color: var(--color-muted)">Diagrams</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-primary)">{summary.elements_created}</p>
				<p class="text-sm" style="color: var(--color-muted)">Elements</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-primary)">{summary.relationships_created}</p>
				<p class="text-sm" style="color: var(--color-muted)">Relationships</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-primary)">{summary.packages_created}</p>
				<p class="text-sm" style="color: var(--color-muted)">Packages</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-muted)">{summary.packages_skipped}</p>
				<p class="text-sm" style="color: var(--color-muted)">Packages Skipped</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-muted)">{summary.diagrams_skipped}</p>
				<p class="text-sm" style="color: var(--color-muted)">Diagrams Skipped</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-muted)">{summary.elements_skipped}</p>
				<p class="text-sm" style="color: var(--color-muted)">Elements Skipped</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-muted)">{summary.connectors_skipped}</p>
				<p class="text-sm" style="color: var(--color-muted)">Connectors Skipped</p>
			</div>
		</div>

		{#if summary.warnings.length > 0}
			<div class="mt-4">
				<h3 class="text-sm font-semibold" style="color: var(--color-fg)">Warnings ({summary.warnings.length})</h3>
				<ul class="mt-2 max-h-40 overflow-y-auto text-sm" style="color: var(--color-muted)">
					{#each summary.warnings as warning}
						<li class="py-1">[{warning.category}] {warning.message}</li>
					{/each}
				</ul>
			</div>
		{/if}

		<div class="mt-4 flex gap-3">
			<a
				href={importSetId ? `/diagrams?set_id=${importSetId}` : '/diagrams'}
				onclick={() => { if (importSetId && importSetName) setActiveSet(importSetId, importSetName); }}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-primary)"
			>
				View Diagrams
			</a>
			<button
				onclick={resetForm}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Import Another
			</button>
		</div>
	</div>
{:else}
	<!-- Upload Form -->
	<div
		class="mt-6 flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors"
		class:drag-over={dragOver}
		style="border-color: {dragOver ? 'var(--color-primary)' : 'var(--color-border)'}; background: {dragOver ? 'var(--color-surface)' : 'transparent'}"
		role="button"
		tabindex="0"
		aria-label="Drop .qea file here or click to browse"
		ondragover={handleDragOver}
		ondragleave={handleDragLeave}
		ondrop={handleDrop}
		onclick={() => fileInputEl?.click()}
		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputEl?.click(); } }}
	>
		<input
			bind:this={fileInputEl}
			type="file"
			class="hidden"
			onchange={handleFileInput}
			aria-hidden="true"
		/>
		<span class="text-4xl" aria-hidden="true">&#128193;</span>
		<p class="mt-3 text-sm font-medium" style="color: var(--color-fg)">
			{#if selectedFile}
				Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
			{:else}
				Drop a .qea file here or click to browse
			{/if}
		</p>
		<p class="mt-1 text-xs" style="color: var(--color-muted)">
			SparxEA files (.qea) — SQLite format, EA 16+
		</p>
	</div>

	{#if selectedFile}
		<div class="mt-4">
			<SetSelector
				bind:this={selectorRef}
				value={importSetId}
				onchange={handleSetChange}
				showAll={false}
				label="Import into set"
				showNewSet={true}
				onNewSet={() => (showCreateSetDialog = true)}
			/>
		</div>
		<div class="mt-4 flex items-center gap-4">
			<button
				onclick={uploadFile}
				disabled={uploading}
				class="rounded px-6 py-2 text-sm text-white"
				style="background-color: var(--color-primary); opacity: {uploading ? 0.6 : 1}"
			>
				{uploading ? 'Importing...' : 'Import'}
			</button>
			<button
				onclick={resetForm}
				disabled={uploading}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Cancel
			</button>
		</div>
	{/if}

	{#if uploading}
		<div class="mt-4">
			<div class="h-2 w-full rounded-full" style="background: var(--color-border)">
				<div
					class="h-2 rounded-full transition-all"
					style="width: {progress}%; background: var(--color-primary)"
					role="progressbar"
					aria-valuenow={progress}
					aria-valuemin={0}
					aria-valuemax={100}
				></div>
			</div>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">
				{#if progress < 20}
					Preparing upload...
				{:else if progress < 80}
					Reading .qea file and importing data...
				{:else if progress < 100}
					Finalizing import...
				{:else}
					Complete!
				{/if}
			</p>
		</div>
	{/if}

	{#if error}
		<div role="alert" class="mt-4 rounded border p-3" style="border-color: var(--color-danger); color: var(--color-danger)">
			{error}
		</div>
	{/if}
{/if}

<SetDialog
	open={showCreateSetDialog}
	oncreate={handleCreateSet}
	oncancel={() => (showCreateSetDialog = false)}
/>
