<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { AIProvider } from '$lib/types/api';

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

	// Form fields
	let form = $state({
		name: '',
		provider_type: 'openai' as typeof PROVIDER_TYPES[number],
		base_url: '',
		api_key_env_var: '',
		model: '',
		system_prompt: '',
		timeout_ms: 30000,
		retries: 3,
		is_default: false,
		is_active: true,
		temperature: '',
		max_tokens: '',
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
		form = {
			name: '',
			provider_type: 'openai',
			base_url: '',
			api_key_env_var: '',
			model: '',
			system_prompt: '',
			timeout_ms: 30000,
			retries: 3,
			is_default: false,
			is_active: true,
			temperature: '',
			max_tokens: '',
		};
		showModal = true;
	}

	function openEdit(p: AIProvider) {
		editingId = p.id;
		modalError = null;
		const params = p.parameters as Record<string, unknown>;
		form = {
			name: p.name,
			provider_type: p.provider_type as typeof PROVIDER_TYPES[number],
			base_url: p.base_url ?? '',
			api_key_env_var: p.api_key_env_var ?? '',
			model: p.model,
			system_prompt: p.system_prompt ?? '',
			timeout_ms: p.timeout_ms,
			retries: p.retries,
			is_default: p.is_default,
			is_active: p.is_active,
			temperature: params.temperature != null ? String(params.temperature) : '',
			max_tokens: params.max_tokens != null ? String(params.max_tokens) : '',
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
		const parameters: Record<string, number> = {};
		if (form.temperature !== '') parameters.temperature = Number(form.temperature);
		if (form.max_tokens !== '') parameters.max_tokens = Number(form.max_tokens);

		const body = {
			name: form.name,
			provider_type: form.provider_type,
			base_url: form.base_url || null,
			api_key_env_var: form.api_key_env_var || null,
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
</script>

<svelte:head>
	<title>AI Providers — Iris Admin</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/admin" style="color: var(--color-primary)">Admin</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">AI Providers</li>
	</ol>
</nav>

<div class="mb-4 flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">AI Providers</h1>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			Configure LLM providers for Set Q&amp;A. API keys are read from environment variables at call time.
		</p>
	</div>
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
									<span class="text-xs" style="color: var(--color-danger)" title={testResults[p.id].error}>error</span>
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
					API key env var <span style="color: var(--color-muted)">(env var name, e.g. OPENAI_API_KEY)</span>
					<input type="text" bind:value={form.api_key_env_var}
						class="rounded border px-3 py-2 font-mono"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						placeholder="OPENAI_API_KEY" />
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
