<script lang="ts">
	/**
	 * Element template detail page (v6.8.0, ADR-191, issue #153).
	 *
	 * Shows scope, source element, captured fields, and the snapshot
	 * of the data that will be applied to new elements. Provides a
	 * "Create element from template" affordance that mirrors the
	 * one in the elements-list Templates dialog.
	 */
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import DOMPurify from 'dompurify';
	import { apiFetch, ApiError } from '$lib/utils/api';

	interface ElementTemplate {
		id: string;
		name: string;
		description: string | null;
		set_id: string | null;
		set_name: string | null;
		is_global: boolean;
		source_element_id: string | null;
		source_element_name: string | null;
		included_fields: string[];
		template_data: Record<string, unknown>;
		markdown_stamp: string | null;
		created_at: string;
		updated_at: string;
		created_by_username: string;
	}

	let tpl = $state<ElementTemplate | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let useFormOpen = $state(false);
	let newName = $state('');
	let submitting = $state(false);
	let deleting = $state(false);
	let showConfirmDelete = $state(false);

	// SPEC-211-c (v6.24.0): inline stamp editor state.
	let stampEditOpen = $state(false);
	let stampDraft = $state('');
	let stampSaving = $state(false);
	let stampError = $state<string | null>(null);

	function startStampEdit() {
		if (!tpl) return;
		stampDraft = tpl.markdown_stamp ?? '';
		stampError = null;
		stampEditOpen = true;
	}

	function cancelStampEdit() {
		stampEditOpen = false;
		stampError = null;
	}

	async function saveStamp() {
		if (!tpl || stampSaving) return;
		stampSaving = true;
		stampError = null;
		try {
			// PUT carries only the fields we want to change. The
			// backend (ADR-211) accepts markdown_stamp as a partial
			// update; setting it to '' clears the stamp.
			const updated = await apiFetch<ElementTemplate>(
				`/api/element-templates/${tpl.id}`,
				{
					method: 'PUT',
					body: JSON.stringify({
						markdown_stamp: stampDraft,
					}),
				},
			);
			tpl = updated;
			stampEditOpen = false;
		} catch (e) {
			stampError = e instanceof ApiError ? e.message : 'Failed to save stamp';
		}
		stampSaving = false;
	}

	$effect(() => {
		const id = page.params.id;
		if (id) load(id);
	});

	async function load(id: string) {
		loading = true;
		error = null;
		try {
			tpl = await apiFetch<ElementTemplate>(`/api/element-templates/${id}`);
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Template not found'
				: 'Failed to load template';
		}
		loading = false;
	}

	async function createFromTemplate(event: SubmitEvent) {
		event.preventDefault();
		if (!tpl || !newName.trim() || submitting) return;
		submitting = true;
		try {
			const body: Record<string, unknown> = {
				template_id: tpl.id,
				name: DOMPurify.sanitize(newName.trim()),
			};
			if (tpl.set_id) body.set_id = tpl.set_id;
			const created = await apiFetch<{ id: string }>('/api/elements', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			goto(`/elements/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create element';
		}
		submitting = false;
	}

	async function handleDelete() {
		if (!tpl) return;
		deleting = true;
		try {
			await apiFetch(`/api/element-templates/${tpl.id}`, { method: 'DELETE' });
			goto('/elements');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete template';
			deleting = false;
		}
	}

	function renderValue(value: unknown): string {
		if (value === null || value === undefined) return '—';
		if (typeof value === 'string') return value;
		if (typeof value === 'number' || typeof value === 'boolean') return String(value);
		try {
			return JSON.stringify(value, null, 2);
		} catch {
			return String(value);
		}
	}
</script>

<svelte:head>
	<title>{tpl?.name ?? 'Element Template'} — Iris</title>
</svelte:head>

{#if loading}
	<div class="p-8" role="status"><p style="color: var(--color-muted)">Loading template…</p></div>
{:else if error}
	<div class="p-8" role="alert">
		<p style="color: var(--color-danger)">{error}</p>
		<button onclick={() => goto('/elements')} class="mt-4 rounded px-4 py-2 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
			Back to Elements
		</button>
	</div>
{:else if tpl}
	<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
		<ol class="flex items-baseline gap-1">
			<li><a href="/elements" style="color: var(--color-primary)">Elements</a></li>
			<li><span aria-hidden="true">/</span></li>
			<li>Templates</li>
			<li><span aria-hidden="true">/</span></li>
			<li aria-current="page">{tpl.name}</li>
		</ol>
	</nav>

	<div class="flex items-start justify-between gap-4">
		<div>
			<div class="flex flex-wrap items-center gap-3">
				<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{tpl.name}</h1>
				{#if tpl.is_global}
					<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)">Global</span>
				{:else if tpl.set_name}
					<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-muted); border: 1px solid var(--color-border)">{tpl.set_name}</span>
				{/if}
			</div>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">Element template</p>
		</div>
		<div class="flex gap-2">
			<button
				onclick={() => { useFormOpen = true; newName = ''; }}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-primary)"
			>
				Create element from template
			</button>
			<button
				onclick={() => (showConfirmDelete = true)}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-danger)"
			>
				Delete
			</button>
		</div>
	</div>

	{#if tpl.description}
		<p class="mt-3 text-sm" style="color: var(--color-fg)">{tpl.description}</p>
	{/if}

	{#if useFormOpen}
		<form onsubmit={createFromTemplate} class="mt-6 rounded border p-4" style="border-color: var(--color-border); background: var(--color-surface)">
			<label for="new-from-template" class="block text-sm font-medium" style="color: var(--color-fg)">New element name</label>
			<input
				id="new-from-template"
				bind:value={newName}
				required
				autocomplete="off"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
			<div class="mt-3 flex justify-end gap-2">
				<button type="button" onclick={() => (useFormOpen = false)} class="rounded px-4 py-2 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
					Cancel
				</button>
				<button type="submit" disabled={submitting || !newName.trim()} class="rounded px-4 py-2 text-sm text-white disabled:opacity-50" style="background-color: var(--color-primary)">
					{submitting ? 'Creating…' : 'Create'}
				</button>
			</div>
		</form>
	{/if}

	<section class="mt-8">
		<h2 class="text-base font-semibold" style="color: var(--color-fg)">Metadata</h2>
		<dl class="mt-3 grid gap-3" style="grid-template-columns: auto 1fr">
			<dt class="text-sm font-medium" style="color: var(--color-muted)">Source element</dt>
			<dd class="text-sm" style="color: var(--color-fg)">
				{#if tpl.source_element_name}
					<a href="/elements/{tpl.source_element_id}" style="color: var(--color-primary)">
						{tpl.source_element_name}
					</a>
				{:else}
					<span style="color: var(--color-muted)">(source element deleted)</span>
				{/if}
			</dd>
			<dt class="text-sm font-medium" style="color: var(--color-muted)">Created by</dt>
			<dd class="text-sm" style="color: var(--color-fg)">{tpl.created_by_username}</dd>
			<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
			<dd class="text-sm" style="color: var(--color-fg)">{tpl.created_at}</dd>
			<dt class="text-sm font-medium" style="color: var(--color-muted)">Updated</dt>
			<dd class="text-sm" style="color: var(--color-fg)">{tpl.updated_at}</dd>
		</dl>
	</section>

	<section class="mt-8">
		<div class="flex items-center justify-between">
			<h2 class="text-base font-semibold" style="color: var(--color-fg)">Markdown stamp</h2>
			{#if !stampEditOpen}
				<button onclick={startStampEdit} class="rounded px-3 py-1 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
					{tpl.markdown_stamp ? 'Edit stamp' : 'Add stamp'}
				</button>
			{/if}
		</div>
		<p class="mt-1 text-xs" style="color: var(--color-muted)">
			Smart-markdown fragment surfaced in the picker when this template is in scope for the selected element (ADR-211).
			Use <code>{'{{self:name}}'}</code>, <code>{'{{self:attr:&lt;path&gt;}}'}</code>, etc. — at insert time <code>self</code> is replaced with the element's id.
			Trailing <code>=</code> on an attribute path marks a fillable slot (e.g.&nbsp;<code>{'{{self:attr:attributes/Quantity/type=}}'}</code>).
		</p>
		{#if stampEditOpen}
			<div class="mt-3">
				<textarea
					bind:value={stampDraft}
					rows="4"
					class="w-full rounded border px-3 py-2 font-mono text-xs"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					placeholder="{`{{self:attr:attributes/Quantity/type=}} {{self:attr:attributes/Unit/type}} {{self:name}}`}"
					aria-label="Markdown stamp body"
				></textarea>
				{#if stampError}
					<p class="mt-2 text-sm" style="color: var(--color-danger)">{stampError}</p>
				{/if}
				<div class="mt-2 flex justify-end gap-2">
					<button onclick={cancelStampEdit} disabled={stampSaving} class="rounded px-4 py-2 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
						Cancel
					</button>
					<button onclick={saveStamp} disabled={stampSaving} class="rounded px-4 py-2 text-sm text-white disabled:opacity-50" style="background-color: var(--color-primary)">
						{stampSaving ? 'Saving…' : 'Save stamp'}
					</button>
				</div>
			</div>
		{:else if tpl.markdown_stamp}
			<pre class="mt-3 overflow-x-auto rounded border p-3 font-mono text-xs" style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)">{tpl.markdown_stamp}</pre>
		{:else}
			<p class="mt-3 text-sm" style="color: var(--color-muted)">No stamp set.</p>
		{/if}
	</section>

	<section class="mt-8">
		<h2 class="text-base font-semibold" style="color: var(--color-fg)">Captured fields</h2>
		<p class="mt-1 text-xs" style="color: var(--color-muted)">
			These values will be used to pre-fill new elements created from this template. Explicit fields on the create request override these defaults.
		</p>
		<div class="mt-3 overflow-x-auto">
			<table class="w-full text-sm" style="color: var(--color-fg)">
				<thead>
					<tr style="border-bottom: 1px solid var(--color-border)">
						<th class="py-2 pr-4 text-left font-medium" style="color: var(--color-muted)">Field</th>
						<th class="py-2 text-left font-medium" style="color: var(--color-muted)">Value</th>
					</tr>
				</thead>
				<tbody>
					{#each tpl.included_fields as f (f)}
						<tr style="border-bottom: 1px solid var(--color-border)">
							<td class="py-2 pr-4 font-mono text-xs">{f}</td>
							<td class="py-2"><pre class="whitespace-pre-wrap text-xs" style="color: var(--color-fg)">{renderValue(tpl.template_data[f])}</pre></td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>

	{#if showConfirmDelete}
		<div style="position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.4)">
			<div class="rounded-lg p-6 shadow-lg" style="background: var(--color-bg); border: 1px solid var(--color-border); width: 420px; max-width: 90vw">
				<h3 class="text-lg font-semibold" style="color: var(--color-fg)">Delete template</h3>
				<p class="mt-2 text-sm" style="color: var(--color-muted)">
					Delete '{tpl.name}'? Elements already created from this template are unaffected.
				</p>
				<div class="mt-4 flex justify-end gap-2">
					<button onclick={() => (showConfirmDelete = false)} class="rounded px-4 py-2 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">
						Cancel
					</button>
					<button onclick={handleDelete} disabled={deleting} class="rounded px-4 py-2 text-sm text-white disabled:opacity-50" style="background-color: var(--color-danger)">
						{deleting ? 'Deleting…' : 'Delete'}
					</button>
				</div>
			</div>
		</div>
	{/if}
{/if}
