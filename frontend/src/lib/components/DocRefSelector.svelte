<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';

	interface DocRefDocument {
		id: string;
		slug: string;
		title: string;
		latest_version: string;
		source_url: string;
		csv_url: string;
		chunk_count: number;
		status: string;
		error_message: string | null;
		imported_at: string | null;
		imported_by: string | null;
	}

	interface Props {
		selectedDocIds: string[];
		onchange: (ids: string[]) => void;
	}

	let { selectedDocIds, onchange }: Props = $props();

	let documents = $state<DocRefDocument[]>([]);
	let loading = $state(true);
	let importingIds = $state<Set<string>>(new Set());
	let open = $state(false);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let searchInput = $state<HTMLInputElement | null>(null);

	let selectedCount = $derived(selectedDocIds.length);

	let filteredDocuments = $derived(
		searchQuery
			? documents.filter((d) => d.title.toLowerCase().includes(searchQuery.toLowerCase()))
			: documents
	);

	let summaryText = $derived.by(() => {
		if (selectedCount === 0) return 'Select legislation...';
		if (selectedCount === 1) {
			const doc = documents.find((d) => d.id === selectedDocIds[0]);
			return doc ? doc.title : '1 document';
		}
		return `${selectedCount} legislation docs`;
	});

	$effect(() => {
		loadDocuments();
	});

	async function loadDocuments() {
		loading = true;
		error = null;
		try {
			const resp = await apiFetch<{ items: DocRefDocument[] }>('/api/docref/documents');
			documents = resp.items;
		} catch (e) {
			if (e instanceof ApiError && e.status === 404) {
				// Extension not available — hide component
				documents = [];
			} else {
				error = e instanceof ApiError ? e.message : 'Failed to load documents';
			}
		}
		loading = false;
	}

	async function importDocument(doc: DocRefDocument) {
		if (importingIds.has(doc.id)) return;
		importingIds = new Set([...importingIds, doc.id]);
		try {
			await apiFetch(`/api/docref/documents/${doc.id}/import`, {
				method: 'POST',
			});
			await loadDocuments();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Import failed';
		}
		const next = new Set(importingIds);
		next.delete(doc.id);
		importingIds = next;
	}

	function toggleSelection(docId: string) {
		if (selectedDocIds.includes(docId)) {
			onchange(selectedDocIds.filter((id) => id !== docId));
		} else {
			onchange([...selectedDocIds, docId]);
		}
	}

	function isImporting(docId: string): boolean {
		return importingIds.has(docId);
	}

	$effect(() => {
		if (open && searchInput) {
			searchInput.focus();
		}
		if (!open) {
			searchQuery = '';
		}
	});
</script>

<div class="relative">
	<label class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">Legislation</label>
	<button
		type="button"
		onclick={() => { open = !open; }}
		class="flex w-full items-center justify-between rounded border px-3 py-1.5 text-left text-sm"
		style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); min-width: 250px"
	>
		<span class:text-muted={selectedCount === 0} style={selectedCount === 0 ? 'color: var(--color-muted)' : ''}>
			{summaryText}
		</span>
		<svg class="h-4 w-4" style="color: var(--color-muted)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	{#if open}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="absolute z-50 mt-1 w-full rounded border shadow-lg"
			style="border-color: var(--color-border); background: var(--color-surface)"
		>
			{#if loading}
				<p class="p-3 text-sm" style="color: var(--color-muted)">Loading documents...</p>
			{:else if error}
				<p class="p-3 text-sm" style="color: var(--color-danger)">{error}</p>
			{:else if documents.length === 0}
				<p class="p-3 text-sm" style="color: var(--color-muted)">No documents available.</p>
			{:else}
				<div class="border-b px-3 py-2" style="border-color: var(--color-border)">
					<input
						bind:this={searchInput}
						bind:value={searchQuery}
						type="text"
						placeholder="Search legislation..."
						class="w-full rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					/>
				</div>
				<div class="max-h-64 overflow-y-auto">
				{#each filteredDocuments as doc (doc.id)}
					<div
						class="flex items-center gap-2 border-b px-3 py-2"
						style="border-color: var(--color-border)"
					>
						{#if doc.status === 'imported'}
							<!-- Checkbox for imported docs -->
							<input
								type="checkbox"
								checked={selectedDocIds.includes(doc.id)}
								onchange={() => toggleSelection(doc.id)}
								class="h-4 w-4 rounded"
							/>
						{:else if isImporting(doc.id) || doc.status === 'importing'}
							<!-- Spinner for importing -->
							<svg class="h-4 w-4 animate-spin" style="color: var(--color-primary)" viewBox="0 0 24 24" fill="none">
								<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.25" />
								<path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" opacity="0.75" />
							</svg>
						{:else if doc.status === 'error'}
							<!-- Error icon -->
							<svg class="h-4 w-4" style="color: var(--color-danger)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						{:else}
							<!-- Empty space for alignment -->
							<span class="inline-block h-4 w-4"></span>
						{/if}

						<button
							type="button"
							class="flex-1 text-left text-sm"
							style="color: var(--color-fg)"
							onclick={() => {
								if (doc.status === 'imported') {
									toggleSelection(doc.id);
								} else if (doc.status === 'available' || doc.status === 'error') {
									importDocument(doc);
								}
							}}
							disabled={isImporting(doc.id) || doc.status === 'importing'}
						>
							<span class="font-medium">{doc.title}</span>
							<span class="ml-1 text-xs" style="color: var(--color-muted)">({doc.latest_version})</span>
						</button>

						{#if doc.status === 'imported'}
							<!-- Blue tick indicator -->
							<svg class="h-4 w-4 flex-none" style="color: #3b82f6" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
							</svg>
						{:else if doc.status === 'available'}
							<span class="text-xs" style="color: var(--color-muted)">Click to import</span>
						{:else if doc.status === 'error'}
							<span class="text-xs" style="color: var(--color-danger)" title={doc.error_message || 'Import failed'}>Retry</span>
						{/if}
					</div>
				{/each}
				{#if filteredDocuments.length === 0}
					<p class="p-3 text-sm" style="color: var(--color-muted)">No matching legislation.</p>
				{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>

{#if open}
	<!-- Backdrop to close dropdown -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-40"
		onclick={() => { open = false; }}
		onkeydown={(e) => { if (e.key === 'Escape') open = false; }}
	></div>
{/if}
