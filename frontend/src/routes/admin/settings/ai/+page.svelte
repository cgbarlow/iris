<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { AIProvider } from '$lib/types/api';

	type CreationPrompt = {
		id: string;
		name: string;
		description: string | null;
		purpose: string;  // 'creation_format' | 'response_format' (v5.12.0+)
		layer: string;
		notation: string | null;
		diagram_type: string | null;
		prompt_text: string;
		display_order: number;
		is_active: boolean;
	};

	type Notation = { id: string; name: string };
	type DiagramType = { id: string; name: string };

	const PURPOSES = ['creation_format', 'response_format'] as const;
	const LAYERS = ['base', 'notation', 'diagram_type', 'override'] as const;

	function appliesToLabel(p: { layer: string; notation: string | null; diagram_type: string | null }): string {
		// ADR-158 (v5.13.0): make the cascade behaviour visible — addresses the
		// "ArchiMate Process Layout has no notation" confusion. Coerce empty
		// strings to null so the live-preview hint in the create form works
		// when the user picks "— none —".
		const n = p.notation || null;
		const d = p.diagram_type || null;
		if (p.layer === 'base') return 'Any notation × Any diagram type';
		if (p.layer === 'override') return n ? `Override: ${n} (replaces all layers)` : 'Override (no notation set — invalid)';
		if (p.layer === 'notation') return n ? `${n} × any diagram type` : 'Notation layer (no notation set — invalid)';
		// layer === 'diagram_type'
		const notationPart = n ?? 'Any notation';
		const dtPart = d ?? '?';
		return `${notationPart} × ${dtPart} diagrams`;
	}

	const PROVIDER_TYPES = ['openai', 'anthropic', 'ollama', 'lmstudio', 'openrouter', 'custom'] as const;

	let providers = $state<AIProvider[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	// Modal state
	let showModal = $state(false);
	let editingId = $state<string | null>(null);
	let saving = $state(false);
	let modalError = $state<string | null>(null);

	// Delete confirmation
	let deletingId = $state<string | null>(null);

	// Test result per provider
	let testResults = $state<Record<string, { ok: boolean; latency_ms?: number; error?: string; testing?: boolean }>>({});

	// Advanced settings toggle (ADR-114)
	let showAdvanced = $state(false);

	// Form fields
	let form = $state({
		name: '',
		provider_type: 'openai' as typeof PROVIDER_TYPES[number],
		base_url: '',
		api_key: '',
		model: '',
		system_prompt: '',
		timeout_ms: 30000,
		retries: 3,
		is_default: false,
		is_active: true,
		temperature: '',
		max_tokens: '',
		top_p: '',
		top_k: '',
		min_p: '',
		frequency_penalty: '',
		presence_penalty: '',
		stop: '',
	});

	$effect(() => {
		loadProviders();
	});

	async function loadProviders() {
		loading = true;
		error = null;
		try {
			providers = await apiFetch<AIProvider[]>('/api/ai/providers');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to load providers';
		}
		loading = false;
	}

	function openCreate() {
		editingId = null;
		modalError = null;
		showAdvanced = false;
		form = {
			name: '',
			provider_type: 'openai',
			base_url: '',
			api_key: '',
			model: '',
			system_prompt: '',
			timeout_ms: 30000,
			retries: 3,
			is_default: false,
			is_active: true,
			temperature: '',
			max_tokens: '',
			top_p: '',
			top_k: '',
			min_p: '',
			frequency_penalty: '',
			presence_penalty: '',
			stop: '',
		};
		showModal = true;
	}

	function openEdit(p: AIProvider) {
		editingId = p.id;
		modalError = null;
		const params = p.parameters as Record<string, unknown>;
		// Auto-expand advanced section if any advanced params are set
		showAdvanced = [params.top_p, params.top_k, params.min_p,
			params.frequency_penalty, params.presence_penalty, params.stop].some(v => v != null);
		form = {
			name: p.name,
			provider_type: p.provider_type as typeof PROVIDER_TYPES[number],
			base_url: p.base_url ?? '',
			api_key: '',  // never pre-filled — leave blank to keep existing key
			model: p.model,
			system_prompt: p.system_prompt ?? '',
			timeout_ms: p.timeout_ms,
			retries: p.retries,
			is_default: p.is_default,
			is_active: p.is_active,
			temperature: params.temperature != null ? String(params.temperature) : '',
			max_tokens: params.max_tokens != null ? String(params.max_tokens) : '',
			top_p: params.top_p != null ? String(params.top_p) : '',
			top_k: params.top_k != null ? String(params.top_k) : '',
			min_p: params.min_p != null ? String(params.min_p) : '',
			frequency_penalty: params.frequency_penalty != null ? String(params.frequency_penalty) : '',
			presence_penalty: params.presence_penalty != null ? String(params.presence_penalty) : '',
			stop: Array.isArray(params.stop) ? (params.stop as string[]).join(', ') : '',
		};
		showModal = true;
	}

	function closeModal() {
		showModal = false;
		editingId = null;
	}

	async function saveProvider() {
		saving = true;
		modalError = null;
		const parameters: Record<string, number | string[]> = {};
		if (form.temperature !== '') parameters.temperature = Number(form.temperature);
		if (form.max_tokens !== '') parameters.max_tokens = Number(form.max_tokens);
		if (form.top_p !== '') parameters.top_p = Number(form.top_p);
		if (form.top_k !== '') parameters.top_k = Number(form.top_k);
		if (form.min_p !== '') parameters.min_p = Number(form.min_p);
		if (form.frequency_penalty !== '') parameters.frequency_penalty = Number(form.frequency_penalty);
		if (form.presence_penalty !== '') parameters.presence_penalty = Number(form.presence_penalty);
		if (form.stop !== '') parameters.stop = form.stop.split(',').map(s => s.trim()).filter(Boolean);

		const body = {
			name: form.name,
			provider_type: form.provider_type,
			base_url: form.base_url || null,
			api_key: form.api_key || null,
			model: form.model,
			parameters,
			system_prompt: form.system_prompt || null,
			timeout_ms: form.timeout_ms,
			retries: form.retries,
			is_default: form.is_default,
			is_active: form.is_active,
		};

		try {
			if (editingId) {
				await apiFetch(`/api/ai/providers/${editingId}`, {
					method: 'PUT',
					body: JSON.stringify(body),
				});
			} else {
				await apiFetch('/api/ai/providers', {
					method: 'POST',
					body: JSON.stringify(body),
				});
			}
			closeModal();
			await loadProviders();
			success = editingId ? 'Provider updated.' : 'Provider created.';
			setTimeout(() => { success = null; }, 3000);
		} catch (e) {
			modalError = e instanceof ApiError ? e.message : 'Save failed';
		}
		saving = false;
	}

	async function deleteProvider(id: string) {
		try {
			await apiFetch(`/api/ai/providers/${id}`, { method: 'DELETE' });
			deletingId = null;
			await loadProviders();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Delete failed';
			deletingId = null;
		}
	}

	async function testProvider(id: string) {
		testResults[id] = { ok: false, testing: true };
		try {
			const result = await apiFetch<{ ok: boolean; latency_ms?: number; error?: string }>(
				`/api/ai/providers/${id}/test`,
				{ method: 'POST' }
			);
			testResults[id] = result;
		} catch (e) {
			testResults[id] = { ok: false, error: e instanceof ApiError ? e.message : 'Test failed' };
		}
	}

	async function setDefault(id: string) {
		try {
			await apiFetch(`/api/ai/providers/${id}/default`, { method: 'POST' });
			await loadProviders();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to set default';
		}
	}

	// ── Creation Prompts (v5.13.0 / ADR-158: filter + CRUD redesign) ──────────
	let creationPrompts = $state<CreationPrompt[]>([]);
	let promptsLoading = $state(true);
	let promptError = $state<string | null>(null);
	let availableNotations = $state<Notation[]>([]);
	let availableDiagramTypes = $state<DiagramType[]>([]);

	// Filter state (URL-state-backed for purpose + layer; matches /views convention).
	const urlPurpose = typeof window !== 'undefined'
		? new URLSearchParams(window.location.search).get('purpose')
		: null;
	const urlLayer = typeof window !== 'undefined'
		? new URLSearchParams(window.location.search).get('layer')
		: null;
	let purposeFilter = $state(urlPurpose ?? '');
	let layerFilter = $state(urlLayer ?? '');
	let notationFilter = $state('');
	let diagramTypeFilter = $state('');
	let statusFilter = $state(''); // '', 'active', 'inactive'
	let searchText = $state('');
	let sortBy = $state<'name' | 'layer' | 'updated'>('layer');

	// Edit / add / delete state.
	let editingPrompt = $state<CreationPrompt | null>(null);
	let promptEditText = $state('');
	let promptEditName = $state('');
	let promptEditDescription = $state('');
	let promptEditNotation = $state('');
	let promptEditDiagramType = $state('');
	let promptSaving = $state(false);

	let creatingPrompt = $state(false);
	let createForm = $state({
		name: '',
		description: '',
		purpose: 'creation_format' as 'creation_format' | 'response_format',
		layer: 'diagram_type' as typeof LAYERS[number],
		notation: '',
		diagram_type: '',
		prompt_text: '',
	});
	let createSaving = $state(false);
	let createError = $state<string | null>(null);

	let deletingPromptId = $state<string | null>(null);

	$effect(() => {
		loadCreationPrompts();
		loadAxes();
	});

	async function loadCreationPrompts() {
		promptsLoading = true;
		try {
			creationPrompts = await apiFetch<CreationPrompt[]>('/api/ai/creation-prompts');
		} catch {
			// silently ignore — section just won't render
		}
		promptsLoading = false;
	}

	async function loadAxes() {
		try {
			availableNotations = await apiFetch<Notation[]>('/api/notations');
		} catch {
			availableNotations = [];
		}
		try {
			availableDiagramTypes = await apiFetch<DiagramType[]>('/api/diagram-types');
		} catch {
			availableDiagramTypes = [];
		}
	}

	const filteredPrompts = $derived.by(() => {
		const q = searchText.toLowerCase().trim();
		return creationPrompts
			.filter((p) => {
				if (purposeFilter && (p.purpose ?? 'creation_format') !== purposeFilter) return false;
				if (layerFilter && p.layer !== layerFilter) return false;
				if (notationFilter && (p.notation ?? '') !== notationFilter) return false;
				if (diagramTypeFilter && (p.diagram_type ?? '') !== diagramTypeFilter) return false;
				if (statusFilter === 'active' && !p.is_active) return false;
				if (statusFilter === 'inactive' && p.is_active) return false;
				if (q) {
					if (!p.name.toLowerCase().includes(q)
						&& !(p.description?.toLowerCase().includes(q) ?? false)) {
						return false;
					}
				}
				return true;
			})
			.sort((a, b) => {
				if (sortBy === 'name') return a.name.localeCompare(b.name);
				if (sortBy === 'updated') return 0;  // server already returns by purpose, layer, display_order
				// 'layer'
				const layerOrder = ['base', 'notation', 'diagram_type', 'override'];
				const ai = layerOrder.indexOf(a.layer);
				const bi = layerOrder.indexOf(b.layer);
				if (ai !== bi) return ai - bi;
				return a.name.localeCompare(b.name);
			});
	});

	function resetFilters() {
		purposeFilter = '';
		layerFilter = '';
		notationFilter = '';
		diagramTypeFilter = '';
		statusFilter = '';
		searchText = '';
		sortBy = 'layer';
	}

	// Sync purpose + layer filters to URL params for shareability (matches /views).
	$effect(() => {
		if (typeof window === 'undefined') return;
		const url = new URL(window.location.href);
		if (purposeFilter) url.searchParams.set('purpose', purposeFilter);
		else url.searchParams.delete('purpose');
		if (layerFilter) url.searchParams.set('layer', layerFilter);
		else url.searchParams.delete('layer');
		window.history.replaceState({}, '', url);
	});

	function openPromptEdit(p: CreationPrompt) {
		editingPrompt = p;
		promptEditText = p.prompt_text;
		promptEditName = p.name;
		promptEditDescription = p.description ?? '';
		promptEditNotation = p.notation ?? '';
		promptEditDiagramType = p.diagram_type ?? '';
		promptError = null;
	}

	function closePromptEdit() {
		editingPrompt = null;
	}

	async function savePrompt() {
		if (!editingPrompt) return;
		promptSaving = true;
		promptError = null;
		try {
			await apiFetch(`/api/ai/creation-prompts/${editingPrompt.id}`, {
				method: 'PUT',
				body: JSON.stringify({
					name: promptEditName,
					description: promptEditDescription || null,
					notation: promptEditNotation,
					diagram_type: promptEditDiagramType,
					prompt_text: promptEditText,
				}),
			});
			closePromptEdit();
			await loadCreationPrompts();
		} catch (e) {
			promptError = e instanceof ApiError ? e.message : 'Save failed';
		}
		promptSaving = false;
	}

	async function togglePromptActive(p: CreationPrompt) {
		try {
			await apiFetch(`/api/ai/creation-prompts/${p.id}`, {
				method: 'PUT',
				body: JSON.stringify({ is_active: !p.is_active }),
			});
			await loadCreationPrompts();
		} catch (e) {
			promptError = e instanceof ApiError ? e.message : 'Toggle failed';
		}
	}

	function openCreatePrompt() {
		creatingPrompt = true;
		createForm = {
			name: '',
			description: '',
			purpose: 'creation_format',
			layer: 'diagram_type',
			notation: '',
			diagram_type: '',
			prompt_text: '',
		};
		createError = null;
	}

	function closeCreatePrompt() {
		creatingPrompt = false;
		createError = null;
	}

	const createConflict = $derived.by(() => {
		// Live conflict check: does an active row already cover this (purpose, layer, notation, diagram_type)?
		if (!creatingPrompt) return null;
		const conflict = creationPrompts.find((p) =>
			p.is_active
			&& (p.purpose ?? 'creation_format') === createForm.purpose
			&& p.layer === createForm.layer
			&& (p.notation ?? '') === createForm.notation
			&& (p.diagram_type ?? '') === createForm.diagram_type
		);
		return conflict ? conflict.name : null;
	});

	async function saveCreatePrompt() {
		createSaving = true;
		createError = null;
		try {
			const body: Record<string, unknown> = {
				name: createForm.name,
				description: createForm.description || null,
				purpose: createForm.purpose,
				layer: createForm.layer,
				prompt_text: createForm.prompt_text,
				is_active: true,
			};
			if (createForm.notation) body.notation = createForm.notation;
			if (createForm.diagram_type) body.diagram_type = createForm.diagram_type;
			await apiFetch('/api/ai/creation-prompts', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			closeCreatePrompt();
			await loadCreationPrompts();
		} catch (e) {
			createError = e instanceof ApiError ? e.message : 'Create failed';
		}
		createSaving = false;
	}

	async function confirmDeletePrompt() {
		if (!deletingPromptId) return;
		try {
			await apiFetch(`/api/ai/creation-prompts/${deletingPromptId}`, { method: 'DELETE' });
			deletingPromptId = null;
			await loadCreationPrompts();
		} catch (e) {
			promptError = e instanceof ApiError ? e.message : 'Delete failed';
			deletingPromptId = null;
		}
	}
</script>

<div class="mb-4 flex items-center justify-between">
	<p style="color: var(--color-muted)">
		Configure LLM providers and AI settings. API keys are stored securely and never returned by the API.
	</p>
	<button
		onclick={openCreate}
		class="rounded px-4 py-2 text-sm text-white"
		style="background-color: var(--color-primary)"
	>
		Add Provider
	</button>
</div>

{#if error}
	<div role="alert" class="mb-4 rounded border p-3 text-sm"
		style="border-color: var(--color-danger); color: var(--color-danger)">{error}</div>
{/if}
{#if success}
	<div role="status" class="mb-4 rounded border p-3 text-sm"
		style="border-color: var(--color-success, #16a34a); color: var(--color-success, #16a34a)">{success}</div>
{/if}

{#if loading}
	<p style="color: var(--color-muted)">Loading...</p>
{:else if providers.length === 0}
	<p class="mt-6 text-sm" style="color: var(--color-muted)">No providers configured. Add one to enable AI Q&amp;A.</p>
{:else}
	<div class="overflow-x-auto rounded border" style="border-color: var(--color-border)">
		<table class="w-full text-sm" style="color: var(--color-fg)">
			<thead>
				<tr style="background: var(--color-surface); border-bottom: 1px solid var(--color-border)">
					<th class="px-4 py-2 text-left font-medium">Name</th>
					<th class="px-4 py-2 text-left font-medium">Type</th>
					<th class="px-4 py-2 text-left font-medium">Model</th>
					<th class="px-4 py-2 text-left font-medium">Status</th>
					<th class="px-4 py-2 text-right font-medium">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each providers as p (p.id)}
					<tr style="border-bottom: 1px solid var(--color-border)">
						<td class="px-4 py-2 font-medium">
							{p.name}
							{#if p.is_default}
								<span class="ml-2 rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-800">default</span>
							{/if}
						</td>
						<td class="px-4 py-2 font-mono text-xs">{p.provider_type}</td>
						<td class="px-4 py-2 font-mono text-xs">{p.model}</td>
						<td class="px-4 py-2">
							{#if !p.is_active}
								<span class="text-xs" style="color: var(--color-muted)">inactive</span>
							{:else if testResults[p.id]?.testing}
								<span class="text-xs" style="color: var(--color-muted)">testing…</span>
							{:else if testResults[p.id] != null}
								{#if testResults[p.id].ok}
									<span class="text-xs text-green-600">ok ({testResults[p.id].latency_ms}ms)</span>
								{:else}
									<span class="text-xs font-medium" style="color: var(--color-danger)">error</span>
								{#if testResults[p.id].error}
									<div class="mt-0.5 text-xs break-all" style="color: var(--color-danger); opacity: 0.8">{testResults[p.id].error}</div>
								{/if}
								{/if}
							{:else}
								<span class="text-xs" style="color: var(--color-muted)">—</span>
							{/if}
						</td>
						<td class="px-4 py-2 text-right">
							<div class="flex items-center justify-end gap-2">
								{#if !p.is_default}
									<button onclick={() => setDefault(p.id)}
										class="rounded px-2 py-1 text-xs"
										style="border: 1px solid var(--color-border); color: var(--color-muted)">
										Set default
									</button>
								{/if}
								<button onclick={() => testProvider(p.id)}
									class="rounded px-2 py-1 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-fg)">
									Test
								</button>
								<button onclick={() => openEdit(p)}
									class="rounded px-2 py-1 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-fg)">
									Edit
								</button>
								<button onclick={() => { deletingId = p.id; }}
									class="rounded px-2 py-1 text-xs"
									style="border: 1px solid var(--color-danger); color: var(--color-danger)">
									Delete
								</button>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<!-- Add/Edit modal -->
{#if showModal}
	<div role="dialog" aria-modal="true" aria-label="{editingId ? 'Edit' : 'Add'} AI Provider"
		class="fixed inset-0 z-50 flex items-center justify-center"
		style="background: rgba(0,0,0,0.5)">
		<div class="w-full max-w-lg overflow-y-auto rounded border p-6 shadow-xl"
			style="max-height: 90vh; background: var(--color-bg); border-color: var(--color-border)">
			<h2 class="mb-4 text-lg font-semibold" style="color: var(--color-fg)">
				{editingId ? 'Edit Provider' : 'Add Provider'}
			</h2>

			{#if modalError}
				<div role="alert" class="mb-4 rounded border p-3 text-sm"
					style="border-color: var(--color-danger); color: var(--color-danger)">{modalError}</div>
			{/if}

			<div class="flex flex-col gap-3">
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Name
					<input type="text" bind:value={form.name} maxlength="100"
						class="rounded border px-3 py-2"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						placeholder="Production GPT-4o" />
				</label>

				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Provider type
					<select bind:value={form.provider_type}
						class="rounded border px-3 py-2"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
						{#each PROVIDER_TYPES as t}
							<option value={t}>{t}</option>
						{/each}
					</select>
				</label>

				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Model
					<input type="text" bind:value={form.model} maxlength="200"
						class="rounded border px-3 py-2"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						placeholder="gpt-4o" />
				</label>

				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Base URL <span style="color: var(--color-muted)">(optional — uses provider default if blank)</span>
					<input type="url" bind:value={form.base_url}
						class="rounded border px-3 py-2"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						placeholder="https://api.openai.com/v1" />
				</label>

				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					API key
					{#if editingId}
						<span style="color: var(--color-muted)">(leave blank to keep existing key)</span>
					{/if}
					<input type="password" bind:value={form.api_key} autocomplete="new-password"
						class="rounded border px-3 py-2"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						placeholder={editingId ? '••••••••' : 'sk-...'} />
				</label>

				<div class="grid grid-cols-2 gap-3">
					<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
						Temperature <span style="color: var(--color-muted)">(0–2)</span>
						<input type="number" bind:value={form.temperature} min="0" max="2" step="0.1"
							class="rounded border px-3 py-2"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
							placeholder="0.7" />
					</label>
					<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
						Max tokens
						<input type="number" bind:value={form.max_tokens} min="1"
							class="rounded border px-3 py-2"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
							placeholder="4096" />
					</label>
				</div>

				<!-- Advanced Settings toggle (ADR-114) -->
				<button
					type="button"
					onclick={() => { showAdvanced = !showAdvanced; }}
					class="flex items-center gap-2 text-sm font-medium w-full py-2"
					style="color: var(--color-fg)"
					aria-expanded={showAdvanced}
				>
					<span aria-hidden="true">{showAdvanced ? '▼' : '▶'}</span>
					Advanced Settings
					<span class="text-xs" style="color: var(--color-muted)">(optional)</span>
				</button>

				{#if showAdvanced}
					<div class="flex flex-col gap-3 pl-4 border-l-2" style="border-color: var(--color-border)">
						<div class="grid grid-cols-3 gap-3">
							<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
								Top P <span style="color: var(--color-muted)">(0–1)</span>
								<input type="number" bind:value={form.top_p} min="0" max="1" step="0.05"
									class="rounded border px-3 py-2"
									style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									placeholder="0.9" />
							</label>
							<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
								Top K <span style="color: var(--color-muted)">(≥1)</span>
								<input type="number" bind:value={form.top_k} min="1" step="1"
									class="rounded border px-3 py-2"
									style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									placeholder="40" />
							</label>
							<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
								Min P <span style="color: var(--color-muted)">(0–1)</span>
								<input type="number" bind:value={form.min_p} min="0" max="1" step="0.05"
									class="rounded border px-3 py-2"
									style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									placeholder="0.05" />
							</label>
						</div>
						<div class="grid grid-cols-2 gap-3">
							<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
								Frequency penalty <span style="color: var(--color-muted)">(-2–2)</span>
								<input type="number" bind:value={form.frequency_penalty} min="-2" max="2" step="0.1"
									class="rounded border px-3 py-2"
									style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									placeholder="0" />
							</label>
							<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
								Presence penalty <span style="color: var(--color-muted)">(-2–2)</span>
								<input type="number" bind:value={form.presence_penalty} min="-2" max="2" step="0.1"
									class="rounded border px-3 py-2"
									style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									placeholder="0" />
							</label>
						</div>
						<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
							Stop sequences <span style="color: var(--color-muted)">(comma-separated)</span>
							<input type="text" bind:value={form.stop}
								class="rounded border px-3 py-2"
								style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
								placeholder="e.g. END, \n" />
						</label>
					</div>
				{/if}

				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					System prompt <span style="color: var(--color-muted)">(optional)</span>
					<textarea bind:value={form.system_prompt} rows="3"
						class="rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						placeholder="You are a helpful architecture assistant..."></textarea>
				</label>

				<div class="grid grid-cols-2 gap-3">
					<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
						Timeout (ms)
						<input type="number" bind:value={form.timeout_ms} min="1000" max="300000"
							class="rounded border px-3 py-2"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
					</label>
					<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
						Retries
						<input type="number" bind:value={form.retries} min="0" max="10"
							class="rounded border px-3 py-2"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
					</label>
				</div>

				<div class="flex gap-4">
					<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
						<input type="checkbox" bind:checked={form.is_default} />
						Set as default
					</label>
					<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
						<input type="checkbox" bind:checked={form.is_active} />
						Active
					</label>
				</div>
			</div>

			<div class="mt-5 flex justify-end gap-3">
				<button onclick={closeModal}
					class="rounded border px-4 py-2 text-sm"
					style="border-color: var(--color-border); color: var(--color-fg)">
					Cancel
				</button>
				<button onclick={saveProvider} disabled={saving}
					class="rounded px-4 py-2 text-sm text-white disabled:opacity-50"
					style="background-color: var(--color-primary)">
					{saving ? 'Saving…' : editingId ? 'Update' : 'Create'}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- ── Creation / Response Prompts Section (ADR-158, v5.13.0) ─────────── -->
<div class="mt-10">
	<div class="mb-3 flex items-center justify-between">
		<div>
			<h2 class="text-xl font-bold" style="color: var(--color-fg)">AI Prompts</h2>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">
				Layered prompts used for diagram creation (ADR-094-B / ADR-132) and response formatting (ADR-157). Filter, edit, enable/disable, add, and delete from this page. The cascade applies in order: override (replaces all) > base > notation > diagram_type.
			</p>
		</div>
		<button
			onclick={openCreatePrompt}
			class="rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-primary); white-space: nowrap"
		>
			+ Add prompt
		</button>
	</div>

	{#if promptError}
		<div role="alert" class="mb-3 rounded border p-3 text-sm"
			style="border-color: var(--color-danger); color: var(--color-danger)">{promptError}</div>
	{/if}

	<!-- Filter row (mirrors /views inline pattern) -->
	<div class="mb-3 flex flex-wrap items-center gap-2 rounded border p-3"
		style="border-color: var(--color-border); background: var(--color-surface)">
		<select
			bind:value={purposeFilter}
			class="rounded border px-2 py-1 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			aria-label="Filter by purpose"
		>
			<option value="">All purposes</option>
			{#each PURPOSES as p}
				<option value={p}>{p}</option>
			{/each}
		</select>
		<select
			bind:value={layerFilter}
			class="rounded border px-2 py-1 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			aria-label="Filter by layer"
		>
			<option value="">All layers</option>
			{#each LAYERS as l}
				<option value={l}>{l}</option>
			{/each}
		</select>
		<select
			bind:value={notationFilter}
			class="rounded border px-2 py-1 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			aria-label="Filter by notation"
		>
			<option value="">All notations</option>
			{#each availableNotations as n (n.id)}
				<option value={n.id}>{n.name}</option>
			{/each}
		</select>
		<select
			bind:value={diagramTypeFilter}
			class="rounded border px-2 py-1 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			aria-label="Filter by diagram type"
		>
			<option value="">All diagram types</option>
			{#each availableDiagramTypes as d (d.id)}
				<option value={d.id}>{d.name}</option>
			{/each}
		</select>
		<select
			bind:value={statusFilter}
			class="rounded border px-2 py-1 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			aria-label="Filter by status"
		>
			<option value="">All statuses</option>
			<option value="active">Active only</option>
			<option value="inactive">Inactive only</option>
		</select>
		<input
			type="text"
			bind:value={searchText}
			placeholder="Search name + description..."
			class="flex-1 rounded border px-2 py-1 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); min-width: 200px"
			aria-label="Search prompts"
		/>
		<select
			bind:value={sortBy}
			class="rounded border px-2 py-1 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			aria-label="Sort by"
		>
			<option value="layer">Sort: layer</option>
			<option value="name">Sort: name</option>
		</select>
		<button
			onclick={resetFilters}
			class="text-sm underline"
			style="color: var(--color-muted)"
		>
			Reset filters
		</button>
		<span class="ml-auto text-xs" style="color: var(--color-muted)">
			{filteredPrompts.length} of {creationPrompts.length}
		</span>
	</div>

	{#if creatingPrompt}
		<div class="mb-3 rounded border p-4"
			style="border-color: var(--color-border); background: var(--color-surface)">
			<h3 class="mb-3 text-base font-semibold" style="color: var(--color-fg)">New prompt</h3>
			{#if createError}
				<div role="alert" class="mb-3 rounded border p-3 text-sm"
					style="border-color: var(--color-danger); color: var(--color-danger)">{createError}</div>
			{/if}
			<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Name
					<input type="text" bind:value={createForm.name}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
				</label>
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Description (optional)
					<input type="text" bind:value={createForm.description}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
				</label>
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Purpose
					<select bind:value={createForm.purpose}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
						{#each PURPOSES as p}
							<option value={p}>{p}</option>
						{/each}
					</select>
				</label>
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Layer
					<select bind:value={createForm.layer}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
						{#each LAYERS as l}
							<option value={l}>{l}</option>
						{/each}
					</select>
				</label>
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Notation (optional)
					<select bind:value={createForm.notation}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
						<option value="">— none —</option>
						{#each availableNotations as n (n.id)}
							<option value={n.id}>{n.name}</option>
						{/each}
					</select>
				</label>
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Diagram type (optional)
					<select bind:value={createForm.diagram_type}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
						<option value="">— none —</option>
						{#each availableDiagramTypes as d (d.id)}
							<option value={d.id}>{d.name}</option>
						{/each}
					</select>
				</label>
			</div>
			<label class="mt-3 flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
				Prompt text
				<textarea bind:value={createForm.prompt_text} rows="10"
					class="rounded border px-2 py-1 font-mono text-xs"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); resize: vertical"></textarea>
			</label>
			<p class="mt-2 text-xs" style="color: var(--color-muted)">
				Will apply to: <strong>{appliesToLabel({ layer: createForm.layer, notation: createForm.notation || null, diagram_type: createForm.diagram_type || null })}</strong>
			</p>
			{#if createConflict}
				<p class="mt-2 text-xs" style="color: var(--color-danger)">
					An active prompt already exists for this combination: <strong>{createConflict}</strong>. Disable that prompt first or pick a different combination.
				</p>
			{/if}
			<div class="mt-3 flex justify-end gap-3">
				<button onclick={closeCreatePrompt}
					class="rounded border px-4 py-2 text-sm"
					style="border-color: var(--color-border); color: var(--color-fg)">
					Cancel
				</button>
				<button onclick={saveCreatePrompt} disabled={createSaving || !createForm.name || !createForm.prompt_text || createConflict !== null}
					class="rounded px-4 py-2 text-sm text-white disabled:opacity-50"
					style="background-color: var(--color-primary)">
					{createSaving ? 'Saving…' : 'Create'}
				</button>
			</div>
		</div>
	{/if}

	{#if promptsLoading}
		<p style="color: var(--color-muted)">Loading…</p>
	{:else if filteredPrompts.length === 0}
		<p class="text-sm" style="color: var(--color-muted)">
			{creationPrompts.length === 0 ? 'No prompts found.' : 'No prompts match these filters.'}
		</p>
	{:else}
		<div class="overflow-x-auto rounded border" style="border-color: var(--color-border)">
			<table class="w-full text-sm" style="color: var(--color-fg)">
				<thead>
					<tr style="background: var(--color-surface); border-bottom: 1px solid var(--color-border)">
						<th class="px-4 py-2 text-left font-medium">Name</th>
						<th class="px-4 py-2 text-left font-medium">Purpose</th>
						<th class="px-4 py-2 text-left font-medium">Layer</th>
						<th class="px-4 py-2 text-left font-medium">Applies to</th>
						<th class="px-4 py-2 text-left font-medium">Status</th>
						<th class="px-4 py-2 text-right font-medium">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each filteredPrompts as p (p.id)}
						<tr style="border-bottom: 1px solid var(--color-border); opacity: {p.is_active ? '1' : '0.55'}">
							<td class="px-4 py-2">
								<div class="font-medium">{p.name}</div>
								{#if p.description}
									<div class="text-xs" style="color: var(--color-muted)">{p.description}</div>
								{/if}
							</td>
							<td class="px-4 py-2 font-mono text-xs">{p.purpose ?? 'creation_format'}</td>
							<td class="px-4 py-2 font-mono text-xs">{p.layer}</td>
							<td class="px-4 py-2 text-xs">{appliesToLabel(p)}</td>
							<td class="px-4 py-2 text-xs">
								<button
									onclick={() => togglePromptActive(p)}
									class="rounded px-2 py-1 text-xs"
									style="border: 1px solid var(--color-border); color: {p.is_active ? 'var(--color-success, #16a34a)' : 'var(--color-muted)'}; background: var(--color-bg)"
									aria-label="Toggle active status"
								>
									{p.is_active ? '● active' : '○ inactive'}
								</button>
							</td>
							<td class="px-4 py-2 text-right">
								<button
									onclick={() => openPromptEdit(p)}
									class="rounded px-2 py-1 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-fg)"
								>
									Edit
								</button>
								<button
									onclick={() => { deletingPromptId = p.id; }}
									class="ml-2 rounded px-2 py-1 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-danger)"
								>
									Delete
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<!-- Edit prompt modal (ADR-158, v5.13.0: extended to edit name/description/notation/diagram_type) -->
{#if editingPrompt}
	<div role="dialog" aria-modal="true" aria-label="Edit AI prompt"
		class="fixed inset-0 z-50 flex items-center justify-center"
		style="background: rgba(0,0,0,0.5)">
		<div class="w-full max-w-3xl overflow-y-auto rounded border p-6 shadow-xl"
			style="max-height: 90vh; background: var(--color-bg); border-color: var(--color-border)">
			<h2 class="mb-1 text-lg font-semibold" style="color: var(--color-fg)">Edit prompt</h2>
			<p class="mb-4 text-xs" style="color: var(--color-muted)">
				purpose: {editingPrompt.purpose ?? 'creation_format'} · layer: {editingPrompt.layer}
				(both immutable — delete and re-create to move between purposes/layers)
			</p>

			{#if promptError}
				<div role="alert" class="mb-3 rounded border p-3 text-sm"
					style="border-color: var(--color-danger); color: var(--color-danger)">{promptError}</div>
			{/if}

			<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Name
					<input type="text" bind:value={promptEditName}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
				</label>
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Description
					<input type="text" bind:value={promptEditDescription}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" />
				</label>
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Notation
					<select bind:value={promptEditNotation}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
						<option value="">— none —</option>
						{#each availableNotations as n (n.id)}
							<option value={n.id}>{n.name}</option>
						{/each}
					</select>
				</label>
				<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
					Diagram type
					<select bind:value={promptEditDiagramType}
						class="rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
						<option value="">— none —</option>
						{#each availableDiagramTypes as d (d.id)}
							<option value={d.id}>{d.name}</option>
						{/each}
					</select>
				</label>
			</div>

			<label class="mt-4 flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
				Prompt text
				<textarea
					bind:value={promptEditText}
					rows="16"
					class="rounded border px-3 py-2 font-mono text-xs"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); resize: vertical"
				></textarea>
			</label>

			<p class="mt-2 text-xs" style="color: var(--color-muted)">
				Will apply to: <strong>{appliesToLabel({ layer: editingPrompt.layer, notation: promptEditNotation || null, diagram_type: promptEditDiagramType || null })}</strong>
			</p>

			<div class="mt-4 flex justify-end gap-3">
				<button onclick={closePromptEdit}
					class="rounded border px-4 py-2 text-sm"
					style="border-color: var(--color-border); color: var(--color-fg)">
					Cancel
				</button>
				<button onclick={savePrompt} disabled={promptSaving}
					class="rounded px-4 py-2 text-sm text-white disabled:opacity-50"
					style="background-color: var(--color-primary)">
					{promptSaving ? 'Saving…' : 'Save'}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Delete prompt confirmation (ADR-158, v5.13.0) -->
{#if deletingPromptId}
	{@const pp = creationPrompts.find(x => x.id === deletingPromptId)}
	<div role="dialog" aria-modal="true" aria-label="Confirm delete prompt"
		class="fixed inset-0 z-50 flex items-center justify-center"
		style="background: rgba(0,0,0,0.5)">
		<div class="rounded border p-6 shadow-xl"
			style="background: var(--color-bg); border-color: var(--color-border); min-width: 360px">
			<h2 class="mb-2 text-base font-semibold" style="color: var(--color-fg)">Delete prompt?</h2>
			<p class="mb-4 text-sm" style="color: var(--color-muted)">
				Delete <strong>{pp?.name}</strong>? This is a hard delete. To preserve content while suppressing it from the cascade, use the inactive toggle instead.
			</p>
			<div class="flex justify-end gap-3">
				<button onclick={() => { deletingPromptId = null; }}
					class="rounded border px-4 py-2 text-sm"
					style="border-color: var(--color-border); color: var(--color-fg)">
					Cancel
				</button>
				<button onclick={confirmDeletePrompt}
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: var(--color-danger)">
					Delete
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Delete confirmation -->
{#if deletingId}
	{@const p = providers.find(x => x.id === deletingId)}
	<div role="dialog" aria-modal="true" aria-label="Confirm delete"
		class="fixed inset-0 z-50 flex items-center justify-center"
		style="background: rgba(0,0,0,0.5)">
		<div class="rounded border p-6 shadow-xl"
			style="background: var(--color-bg); border-color: var(--color-border); min-width: 320px">
			<h2 class="mb-2 text-base font-semibold" style="color: var(--color-fg)">Delete provider?</h2>
			<p class="mb-4 text-sm" style="color: var(--color-muted)">
				Delete <strong>{p?.name}</strong>? This cannot be undone.
			</p>
			<div class="flex justify-end gap-3">
				<button onclick={() => { deletingId = null; }}
					class="rounded border px-4 py-2 text-sm"
					style="border-color: var(--color-border); color: var(--color-fg)">
					Cancel
				</button>
				<button onclick={() => deleteProvider(deletingId!)}
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: var(--color-danger)">
					Delete
				</button>
			</div>
		</div>
	</div>
{/if}
