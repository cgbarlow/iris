<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import { getActiveSetId } from '$lib/stores/activeSet.svelte.js';
	import { getActiveCollectionId } from '$lib/stores/activeCollection.svelte.js';
	import SetQA from '$lib/components/SetQA.svelte';
	import MultiSetSelector from '$lib/components/MultiSetSelector.svelte';
	import DocRefSelector from '$lib/components/DocRefSelector.svelte';
	import FileUploader from '$lib/components/FileUploader.svelte';
	import type { UploadedFile } from '$lib/components/FileUploader.svelte';
	import type { IrisSet, IrisCollection } from '$lib/types/api';

	type Extension = {
		id: string;
		is_enabled: boolean;
	};

	let allSets = $state<IrisSet[]>([]);
	let collections = $state<IrisCollection[]>([]);
	let loading = $state(true);
	let docrefEnabled = $state(false);

	const activeSetId = $derived(getActiveSetId());
	const activeCollectionId = $derived(getActiveCollectionId());

	let selectedCollectionId = $state('');
	let selectedSetIds = $state<string[]>([]);
	let selectedPackageIds = $state<string[]>([]);
	let selectedDocRefIds = $state<string[]>([]);
	let uploadedFiles = $state<UploadedFile[]>([]);

	// Tab state
	let activeTab = $state<'context' | 'request'>('context');

	// DocRef document metadata (received from DocRefSelector callback)
	let docRefDocuments = $state<{ id: string; title: string }[]>([]);

	// Package metadata by set (received from MultiSetSelector callback)
	let packagesBySet = $state<Record<string, { id: string; name: string }[]>>({});

	// Filter sets by selected collection
	let displayedSets = $derived(
		selectedCollectionId
			? allSets.filter((s) => s.collection_id === selectedCollectionId)
			: allSets
	);

	// Ready files: uploaded, no error, not still uploading
	let readyFiles = $derived(uploadedFiles.filter((f) => !f.uploading && !f.error));

	// Derive a stable key for SetQA re-render
	let contextKey = $derived(
		selectedSetIds.slice().sort().join(',') + '|' +
		selectedDocRefIds.slice().sort().join(',') + '|' +
		readyFiles.map((f) => f.id).sort().join(',')
	);
	let hasContext = $derived(selectedSetIds.length > 0 || selectedDocRefIds.length > 0 || readyFiles.length > 0);

	// Summary of selected context for display on the Chat tab
	let contextSummary = $derived.by(() => {
		const setLabels = allSets
			.filter((s) => selectedSetIds.includes(s.id))
			.map((s) => {
				const pkgs = (packagesBySet[s.id] ?? [])
					.filter((p) => selectedPackageIds.includes(p.id));
				if (pkgs.length > 0) {
					return `${s.name} (${pkgs.map((p) => p.name).join(', ')})`;
				}
				return s.name;
			});
		const docNames = docRefDocuments
			.filter((d) => selectedDocRefIds.includes(d.id))
			.map((d) => d.title);
		const fileNames = readyFiles.map((f) => f.filename);
		return [...setLabels, ...docNames, ...fileNames].join(', ');
	});

	$effect(() => {
		loadData();
	});

	$effect(() => {
		// Auto-select active collection if available
		if (activeCollectionId && !selectedCollectionId) {
			selectedCollectionId = activeCollectionId;
		}
	});

	async function loadData() {
		loading = true;
		try {
			const [setsResp, collectionsResp] = await Promise.all([
				apiFetch<{ items: IrisSet[] }>('/api/sets'),
				apiFetch<{ items: IrisCollection[] }>('/api/collections'),
			]);
			allSets = setsResp.items;
			collections = collectionsResp.items;

			// Check if DocRef extension is enabled
			try {
				const extResp = await apiFetch<{ items: Extension[] }>('/api/extensions');
				docrefEnabled = extResp.items.some((e) => e.id === 'docref' && e.is_enabled);
			} catch {
				// Extensions API may not be available
			}
		} catch {
			// ignore
		}
		loading = false;
	}

	function handleCollectionChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		selectedCollectionId = select.value;
		// When collection changes, pre-select all sets in the collection
		if (selectedCollectionId) {
			const collectionSets = allSets.filter((s) => s.collection_id === selectedCollectionId);
			selectedSetIds = collectionSets.map((s) => s.id);
		} else {
			// Keep current selection when clearing collection filter
		}
	}
</script>

<svelte:head>
	<title>Ask AI — Iris</title>
</svelte:head>

<div class="flex flex-col" style="height: calc(100vh - 56px - 48px); overflow: hidden">
	<div class="flex-none">
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Ask AI</h1>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			Ask questions about your architecture models.
		</p>
	</div>

	<!-- Tab bar -->
	<div class="mt-3 flex flex-none gap-0 border-b" style="border-color: var(--color-border)" role="tablist" aria-label="Ask AI sections">
		<button
			role="tab"
			aria-selected={activeTab === 'context'}
			onclick={() => (activeTab = 'context')}
			class="px-5 py-2 text-sm font-medium transition-colors"
			style="color: {activeTab === 'context' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'context' ? 'var(--color-primary)' : 'transparent'}; margin-bottom: -1px"
		>
			Context
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'request'}
			onclick={() => (activeTab = 'request')}
			class="px-5 py-2 text-sm font-medium transition-colors"
			style="color: {activeTab === 'request' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'request' ? 'var(--color-primary)' : 'transparent'}; margin-bottom: -1px"
		>
			Chat
		</button>
	</div>

	<!-- Context tab panel -->
	<div role="tabpanel" class="flex-1 overflow-y-auto" style={activeTab === 'context' ? '' : 'display: none'}>
		{#if loading}
			<p class="mt-4 text-sm" style="color: var(--color-muted)">Loading...</p>
		{:else}
			<div class="mt-4 flex flex-wrap items-end gap-4" style="max-width: 800px">
				{#if collections.length > 0}
					<div>
						<label for="ask-collection" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">Collection</label>
						<select
							id="ask-collection"
							value={selectedCollectionId}
							onchange={handleCollectionChange}
							class="rounded border px-3 py-1.5 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); min-width: 200px"
						>
							<option value="">All collections</option>
							{#each collections as c (c.id)}
								<option value={c.id}>{c.name} ({c.set_count})</option>
							{/each}
						</select>
					</div>
				{/if}
				<div>
					<MultiSetSelector
						sets={displayedSets}
						selectedIds={selectedSetIds}
						onchange={(ids) => { selectedSetIds = ids; }}
						{selectedPackageIds}
						onpackagechange={(ids) => { selectedPackageIds = ids; }}
						onpackages={(pkgs) => { packagesBySet = pkgs; }}
					/>
				</div>
			</div>
			{#if docrefEnabled}
				<div class="mt-3" style="max-width: 800px">
					<DocRefSelector
						selectedDocIds={selectedDocRefIds}
						onchange={(ids) => { selectedDocRefIds = ids; }}
						ondocuments={(docs) => { docRefDocuments = docs; }}
					/>
				</div>
			{/if}
			<div class="mt-3" style="max-width: 800px">
				<FileUploader
					files={uploadedFiles}
					onchange={(f) => { uploadedFiles = f; }}
				/>
			</div>
			<div class="mt-3">
				<button
					onclick={() => (activeTab = 'request')}
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: {hasContext ? 'var(--color-primary)' : 'var(--color-muted)'}; cursor: {hasContext ? 'pointer' : 'not-allowed'}"
					disabled={!hasContext}
				>
					Chat
				</button>
			</div>
		{/if}
	</div>

	<!-- Request tab panel -->
	<div
		role="tabpanel"
		class="flex flex-1 flex-col overflow-hidden"
		style={activeTab === 'request' ? '' : 'display: none'}
	>
		{#if !loading}
			<!-- Context summary line -->
			{#if contextSummary}
				<p class="mt-3 flex-none text-sm" style="color: var(--color-muted)">
					{contextSummary}
				</p>
			{:else}
				<p class="mt-3 flex-none text-sm" style="color: var(--color-muted)">
					No context selected. Go to the Context tab to select sets{docrefEnabled ? ', legislation,' : ''} or upload files.
				</p>
			{/if}

			<!-- Chat area -->
			{#if hasContext}
				<div class="mt-2 flex-1 overflow-hidden">
					{#key contextKey}
						<SetQA setIds={selectedSetIds} collectionId={selectedCollectionId || undefined} packageIds={selectedPackageIds.length > 0 ? selectedPackageIds : undefined} docrefDocIds={selectedDocRefIds.length > 0 ? selectedDocRefIds : undefined} fileContexts={readyFiles.length > 0 ? readyFiles.map((f) => ({ filename: f.filename, text: f.extracted_text })) : undefined} />
					{/key}
				</div>
			{:else}
				<p class="mt-4 text-sm" style="color: var(--color-muted)">Select at least one set{docrefEnabled ? ', legislation document,' : ''} or upload a file to start asking questions.</p>
			{/if}
		{/if}
	</div>
</div>
