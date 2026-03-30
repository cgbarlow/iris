<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import { getActiveSetId } from '$lib/stores/activeSet.svelte.js';
	import { getActiveCollectionId } from '$lib/stores/activeCollection.svelte.js';
	import SetQA from '$lib/components/SetQA.svelte';
	import MultiSetSelector from '$lib/components/MultiSetSelector.svelte';
	import DocRefSelector from '$lib/components/DocRefSelector.svelte';
	import FileUploader from '$lib/components/FileUploader.svelte';
	import type { UploadedFile } from '$lib/components/FileUploader.svelte';
	import type { IrisSet, IrisCollection, Diagram } from '$lib/types/api';

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
	let selectedDiagramIds = $state<string[]>([]);
	let allDiagrams = $state<Diagram[]>([]);
	let diagramDropdownOpen = $state(false);
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

	// Diagrams filtered by selected sets
	let displayedDiagrams = $derived(
		selectedSetIds.length > 0
			? allDiagrams.filter((d) => selectedSetIds.includes(d.set_id ?? ''))
			: allDiagrams
	);

	// Ready files: uploaded, no error, not still uploading
	let readyFiles = $derived(uploadedFiles.filter((f) => !f.uploading && !f.error));

	// Derive a stable key for SetQA re-render
	let contextKey = $derived(
		selectedSetIds.slice().sort().join(',') + '|' +
		selectedDocRefIds.slice().sort().join(',') + '|' +
		selectedDiagramIds.slice().sort().join(',') + '|' +
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
		const diagramNames = allDiagrams
			.filter((d) => selectedDiagramIds.includes(d.id))
			.map((d) => d.name);
		const fileNames = readyFiles.map((f) => f.filename);
		const parts = [...setLabels, ...docNames, ...fileNames];
		if (diagramNames.length > 0) parts.push(`Diagrams: ${diagramNames.join(', ')}`);
		return parts.join(', ');
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

	$effect(() => {
		// Load diagrams when selected sets change
		loadDiagrams(selectedSetIds);
	});

	async function loadDiagrams(setIds: string[]) {
		if (setIds.length === 0) {
			allDiagrams = [];
			selectedDiagramIds = [];
			return;
		}
		try {
			const results = await Promise.all(
				setIds.map((sid) =>
					apiFetch<{ items: Diagram[] }>(`/api/diagrams?set_id=${sid}&page_size=100`)
				)
			);
			allDiagrams = results.flatMap((r) => r.items);
			// Remove selections that are no longer in the list
			const validIds = new Set(allDiagrams.map((d) => d.id));
			selectedDiagramIds = selectedDiagramIds.filter((id) => validIds.has(id));
		} catch {
			allDiagrams = [];
		}
	}

	let diagramSummaryText = $derived.by(() => {
		if (selectedDiagramIds.length === 0) return 'All diagrams';
		if (selectedDiagramIds.length === 1) {
			const d = allDiagrams.find((d) => d.id === selectedDiagramIds[0]);
			return d ? d.name : '1 diagram';
		}
		return `${selectedDiagramIds.length} diagrams`;
	});

	function toggleDiagram(id: string) {
		if (selectedDiagramIds.includes(id)) {
			selectedDiagramIds = selectedDiagramIds.filter((d) => d !== id);
		} else {
			selectedDiagramIds = [...selectedDiagramIds, id];
		}
	}

	function selectAllDiagrams() {
		selectedDiagramIds = displayedDiagrams.map((d) => d.id);
	}

	function clearDiagrams() {
		selectedDiagramIds = [];
	}

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

	function resetSelections() {
		selectedCollectionId = '';
		selectedSetIds = [];
		selectedPackageIds = [];
		selectedDiagramIds = [];
		selectedDocRefIds = [];
		uploadedFiles = [];
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
	<title>Iris AI</title>
</svelte:head>

<div class="flex flex-col" style="height: calc(100vh - 56px - 48px); overflow: hidden">
	<div class="flex-none">
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Iris AI</h1>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			Chat with AI to explore, analyse, and create architecture models.
		</p>
	</div>

	<!-- Tab bar -->
	<div class="mt-3 flex flex-none gap-0 border-b" style="border-color: var(--color-border)" role="tablist" aria-label="Iris AI sections">
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
			<div class="mt-4 grid items-end gap-4" style="max-width: 800px; grid-template-columns: 1fr 1fr 1fr">
				<div style="min-width: 0">
					{#if collections.length > 0}
						<label for="ask-collection" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">Collection</label>
						<select
							id="ask-collection"
							value={selectedCollectionId}
							onchange={handleCollectionChange}
							class="w-full rounded border px-3 py-1.5 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						>
							<option value="">All collections</option>
							{#each collections as c (c.id)}
								<option value={c.id}>{c.name} ({c.set_count})</option>
							{/each}
						</select>
					{:else}
						<label class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">Collection</label>
						<div class="rounded border px-3 py-1.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-muted)">No collections</div>
					{/if}
				</div>
				<div style="min-width: 0">
					<MultiSetSelector
						sets={displayedSets}
						selectedIds={selectedSetIds}
						onchange={(ids) => { selectedSetIds = ids; }}
						{selectedPackageIds}
						onpackagechange={(ids) => { selectedPackageIds = ids; }}
						onpackages={(pkgs) => { packagesBySet = pkgs; }}
					/>
				</div>
				<div style="position: relative; min-width: 0">
					<label class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">Diagrams</label>
					<button
						type="button"
						onclick={() => { diagramDropdownOpen = !diagramDropdownOpen; }}
						class="w-full truncate rounded border px-3 py-1.5 text-left text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); padding-right: 2rem; background-image: url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M2 4l4 4 4-4'/%3E%3C/svg%3E&quot;); background-repeat: no-repeat; background-position: right 0.5rem center;"
					>
						{diagramSummaryText}
					</button>

					{#if diagramDropdownOpen}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div
							style="position: fixed; inset: 0; z-index: 9"
							onclick={() => { diagramDropdownOpen = false; }}
						></div>
						<div
							class="rounded border shadow-lg"
							style="position: absolute; top: 100%; left: 0; z-index: 10; margin-top: 4px; min-width: 320px; max-height: 400px; background: var(--color-surface); border-color: var(--color-border); overflow: hidden; display: flex; flex-direction: column"
						>
							<div class="flex items-center gap-2 border-b px-3 py-2" style="border-color: var(--color-border)">
								<button type="button" onclick={selectAllDiagrams} class="text-xs" style="color: var(--color-primary)">Select all</button>
								<button type="button" onclick={clearDiagrams} class="text-xs" style="color: var(--color-muted)">Clear</button>
							</div>
							<div style="overflow-y: auto; max-height: 360px">
								{#each displayedDiagrams as d (d.id)}
									<label
										class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm transition-colors"
										style="color: var(--color-fg)"
										onmouseenter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg)'; }}
										onmouseleave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
									>
										<input
											type="checkbox"
											checked={selectedDiagramIds.includes(d.id)}
											onchange={() => toggleDiagram(d.id)}
											style="accent-color: var(--color-primary)"
										/>
										<span class="flex-1 truncate">{d.name}</span>
										<span class="text-xs" style="color: var(--color-muted)">{d.diagram_type}</span>
									</label>
								{/each}
								{#if displayedDiagrams.length === 0}
									<div class="px-3 py-2 text-xs" style="color: var(--color-muted)">
										{selectedSetIds.length === 0 ? 'Select sets first' : 'No diagrams available'}
									</div>
								{/if}
							</div>
						</div>
					{/if}
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
			<div class="mt-3 flex gap-2">
				<button
					onclick={resetSelections}
					class="rounded border px-4 py-2 text-sm"
					style="border-color: var(--color-border); color: var(--color-muted)"
				>
					Reset
				</button>
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
						<SetQA setIds={selectedSetIds} collectionId={selectedCollectionId || undefined} packageIds={selectedPackageIds.length > 0 ? selectedPackageIds : undefined} diagramIds={selectedDiagramIds.length > 0 ? selectedDiagramIds : undefined} docrefDocIds={selectedDocRefIds.length > 0 ? selectedDocRefIds : undefined} fileContexts={readyFiles.length > 0 ? readyFiles.map((f) => ({ filename: f.filename, text: f.extracted_text })) : undefined} />
					{/key}
				</div>
			{:else}
				<p class="mt-4 text-sm" style="color: var(--color-muted)">Select at least one set{docrefEnabled ? ', legislation document,' : ''} or upload a file to start asking questions.</p>
			{/if}
		{/if}
	</div>
</div>
