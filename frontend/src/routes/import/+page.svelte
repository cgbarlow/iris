<script lang="ts">
	/** Import page — upload .qea/.eap (SparxEA) or .pptx (DoView) files. */
	import { goto } from '$app/navigation';
	import { getAccessToken } from '$lib/stores/auth.svelte.js';
	import { API_BASE_URL } from '$lib/config.js';
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
		packages_skipped?: number;
		elements_created: number;
		relationships_created: number;
		diagrams_created: number;
		diagrams_skipped?: number;
		elements_skipped?: number;
		connectors_skipped?: number;
		slides_skipped?: number;
		warnings: ImportWarning[];
	}

	interface BatchFileResult {
		filename: string;
		success: boolean;
		error: string | null;
		packages_created: number;
		elements_created: number;
		relationships_created: number;
		diagrams_created: number;
		slides_skipped: number;
		warnings: ImportWarning[];
	}

	interface BatchSummary {
		files_processed: number;
		files_succeeded: number;
		files_failed: number;
		total_packages: number;
		total_elements: number;
		total_relationships: number;
		total_diagrams: number;
		results: BatchFileResult[];
	}

	let dragOver = $state(false);
	let uploading = $state(false);
	let progress = $state(0);
	let error = $state<string | null>(null);
	let summary = $state<ImportSummary | null>(null);
	let batchSummary = $state<BatchSummary | null>(null);
	let selectedFiles = $state<File[]>([]);
	let fileInputEl: HTMLInputElement | undefined = $state();
	let importSetId = $state('');
	let importSetName = $state('');
	let showCreateSetDialog = $state(false);
	let selectorRef: { reload: () => Promise<void> } | undefined = $state();

	const isBatch = $derived(selectedFiles.length > 1 && selectedFiles.every((f) => f.name.endsWith('.pptx')));
	const isPptx = $derived(selectedFiles.length === 1 && (selectedFiles[0]?.name.endsWith('.pptx') ?? false));
	const hasResults = $derived(summary !== null || batchSummary !== null);

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
			selectFiles(Array.from(files));
		}
	}

	function handleFileInput(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			selectFiles(Array.from(input.files));
		}
	}

	function selectFiles(files: File[]) {
		const valid = files.filter(
			(f) => f.name.endsWith('.qea') || f.name.endsWith('.eap') || f.name.endsWith('.pptx'),
		);
		if (valid.length === 0) {
			error = 'Supported formats: .qea, .eap (SparxEA) or .pptx (DoView).';
			return;
		}
		// Multi-file only for .pptx
		if (valid.length > 1 && !valid.every((f) => f.name.endsWith('.pptx'))) {
			error = 'Batch import is only supported for .pptx (DoView) files.';
			return;
		}
		error = null;
		summary = null;
		batchSummary = null;
		selectedFiles = valid;
	}

	async function uploadFile() {
		if (selectedFiles.length === 0) return;
		if (importSetId && importSetName) {
			if (!confirm(`Are you sure you want to import to existing set "${importSetName}"?`)) return;
		}
		uploading = true;
		progress = 0;
		error = null;
		summary = null;
		batchSummary = null;

		try {
			const token = getAccessToken();
			const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

			if (isBatch) {
				// Batch PPTX import
				const formData = new FormData();
				for (const f of selectedFiles) {
					formData.append('files', f);
				}
				formData.append('set_id', importSetId);

				progress = 20;

				const response = await fetch(`${API_BASE_URL}/api/import/pptx/batch`, {
					method: 'POST',
					headers,
					body: formData,
				});

				progress = 80;

				if (!response.ok) {
					const detail = await response.json().catch(() => null);
					throw new Error(detail?.detail || `Import failed (${response.status})`);
				}

				batchSummary = await response.json();
				progress = 100;
			} else {
				// Single file import
				const file = selectedFiles[0];
				const formData = new FormData();
				formData.append('file', file);
				if (importSetId) formData.append('set_id', importSetId);

				progress = 20;

				const endpoint = isPptx ? '/api/import/pptx' : '/api/import/sparx';
				const response = await fetch(`${API_BASE_URL}${endpoint}`, {
					method: 'POST',
					headers,
					body: formData,
				});

				progress = 80;

				if (!response.ok) {
					const detail = await response.json().catch(() => null);
					throw new Error(detail?.detail || `Import failed (${response.status})`);
				}

				summary = await response.json();
				progress = 100;
			}

			selectedFiles = [];
		} catch (e) {
			error = e instanceof Error ? e.message : 'Import failed';
		}

		uploading = false;
	}

	function resetForm() {
		selectedFiles = [];
		summary = null;
		batchSummary = null;
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
	<p class="mt-1 text-sm" style="color: var(--color-muted)">
		Import diagrams from SparxEA (.qea, .eap) or DoView (.pptx) files. Select multiple .pptx files for batch import.
	</p>
</div>

{#if batchSummary}
	<!-- Batch Import Results -->
	<div class="mt-6 rounded border p-6" style="border-color: var(--color-border); background: var(--color-surface)">
		<h2 class="text-lg font-bold" style="color: var(--color-fg)">
			Batch Import Complete — {batchSummary.files_succeeded} of {batchSummary.files_processed} files
		</h2>
		<div class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-primary)">{batchSummary.total_diagrams}</p>
				<p class="text-sm" style="color: var(--color-muted)">Diagrams</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-primary)">{batchSummary.total_elements}</p>
				<p class="text-sm" style="color: var(--color-muted)">Elements</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-primary)">{batchSummary.total_relationships}</p>
				<p class="text-sm" style="color: var(--color-muted)">Relationships</p>
			</div>
			<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
				<p class="text-2xl font-bold" style="color: var(--color-primary)">{batchSummary.total_packages}</p>
				<p class="text-sm" style="color: var(--color-muted)">Packages</p>
			</div>
		</div>

		<!-- Per-file breakdown -->
		<div class="mt-4">
			<h3 class="text-sm font-semibold" style="color: var(--color-fg)">Files</h3>
			<ul class="mt-2 space-y-2">
				{#each batchSummary.results as result}
					<li
						class="rounded border p-3 text-sm"
						style="border-color: var(--color-border); color: var(--color-fg)"
					>
						<div class="flex items-center justify-between">
							<span class="font-medium">{result.filename}</span>
							{#if result.success}
								<span style="color: var(--color-success, #22c55e)">
									{result.diagrams_created} diagrams, {result.elements_created} elements
								</span>
							{:else}
								<span style="color: var(--color-danger)">{result.error}</span>
							{/if}
						</div>
						{#if result.warnings.length > 0}
							<ul class="mt-1 text-xs" style="color: var(--color-muted)">
								{#each result.warnings as w}
									<li>[{w.category}] {w.message}</li>
								{/each}
							</ul>
						{/if}
					</li>
				{/each}
			</ul>
		</div>

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
				Import More
			</button>
		</div>
	</div>
{:else if summary}
	<!-- Single Import Results -->
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
			{#if summary.slides_skipped != null}
				<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
					<p class="text-2xl font-bold" style="color: var(--color-muted)">{summary.slides_skipped}</p>
					<p class="text-sm" style="color: var(--color-muted)">Slides Skipped</p>
				</div>
			{/if}
			{#if summary.packages_skipped != null}
				<div class="rounded border p-3 text-center" style="border-color: var(--color-border)">
					<p class="text-2xl font-bold" style="color: var(--color-muted)">{summary.packages_skipped}</p>
					<p class="text-sm" style="color: var(--color-muted)">Packages Skipped</p>
				</div>
			{/if}
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
		aria-label="Drop files here or click to browse"
		ondragover={handleDragOver}
		ondragleave={handleDragLeave}
		ondrop={handleDrop}
		onclick={() => fileInputEl?.click()}
		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputEl?.click(); } }}
	>
		<input
			bind:this={fileInputEl}
			type="file"
			accept=".qea,.eap,.pptx"
			multiple
			class="hidden"
			onchange={handleFileInput}
			aria-hidden="true"
		/>
		<span class="text-4xl" aria-hidden="true">&#128193;</span>
		<p class="mt-3 text-sm font-medium" style="color: var(--color-fg)">
			{#if selectedFiles.length > 1}
				{selectedFiles.length} files selected
			{:else if selectedFiles.length === 1}
				Selected: {selectedFiles[0].name} ({(selectedFiles[0].size / 1024 / 1024).toFixed(1)} MB)
			{:else}
				Drop files here or click to browse
			{/if}
		</p>
		<p class="mt-1 text-xs" style="color: var(--color-muted)">
			SparxEA (.qea, .eap) or DoView (.pptx) — select multiple .pptx for batch import
		</p>
	</div>

	{#if selectedFiles.length > 1}
		<div class="mt-3 rounded border p-3" style="border-color: var(--color-border)">
			<h3 class="text-sm font-semibold" style="color: var(--color-fg)">Files ({selectedFiles.length})</h3>
			<ul class="mt-1 text-sm" style="color: var(--color-muted)">
				{#each selectedFiles as f}
					<li>{f.name} ({(f.size / 1024 / 1024).toFixed(1)} MB)</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if selectedFiles.length > 0}
		<div class="mt-4">
			<SetSelector
				bind:this={selectorRef}
				value={importSetId}
				onchange={handleSetChange}
				showAll={false}
				label={isBatch ? 'Import all into set (required)' : 'Import into set'}
				showNewSet={true}
				onNewSet={() => (showCreateSetDialog = true)}
			/>
		</div>
		{#if isBatch && !importSetId}
			<p class="mt-1 text-xs" style="color: var(--color-danger)">A set must be selected for batch import.</p>
		{/if}
		<div class="mt-4 flex items-center gap-4">
			<button
				onclick={uploadFile}
				disabled={uploading || (isBatch && !importSetId)}
				class="rounded px-6 py-2 text-sm text-white"
				style="background-color: var(--color-primary); opacity: {uploading || (isBatch && !importSetId) ? 0.6 : 1}"
			>
				{uploading ? 'Importing...' : isBatch ? `Import ${selectedFiles.length} Files` : 'Import'}
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
					{isBatch ? `Processing ${selectedFiles.length} files...` : 'Reading file and importing data...'}
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
