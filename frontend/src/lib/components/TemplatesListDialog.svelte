<script lang="ts">
	/**
	 * Element template browser (v6.8.0, ADR-191, issue #153).
	 *
	 * Lists set-scoped + global element templates and lets the user
	 * either inspect one (link to `/element-templates/{id}`) or
	 * instantiate a new element from it. The "use template" flow asks
	 * for a name in a follow-up prompt and POSTs to
	 * `/api/elements` with `{ name, set_id, template_id }` — the
	 * backend applies the template's whitelisted fields server-side
	 * (ADR-191 §"apply_template_to_create_body").
	 */
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
		created_at: string;
		updated_at: string;
		created_by_username: string;
	}

	interface PaginatedTemplates {
		items: ElementTemplate[];
		total: number;
		page: number;
		page_size: number;
	}

	interface Props {
		open: boolean;
		setId: string;
		oncancel: () => void;
		onuse: (createdElementId: string) => void;
	}

	let { open, setId, oncancel, onuse }: Props = $props();

	let dialogEl: HTMLDialogElement | undefined = $state();
	let templates = $state<ElementTemplate[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);

	// Inline "use template" mini-form state
	let useTarget = $state<ElementTemplate | null>(null);
	let newName = $state('');
	let useSubmitting = $state(false);

	async function loadTemplates() {
		loading = true;
		error = null;
		try {
			const params = new URLSearchParams();
			if (setId) params.set('set_id', setId);
			params.set('include_global', 'true');
			params.set('page_size', '100');
			const data = await apiFetch<PaginatedTemplates>(
				`/api/element-templates?${params}`,
			);
			templates = data.items;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to load templates';
			templates = [];
		}
		loading = false;
	}

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			loadTemplates();
			useTarget = null;
			newName = '';
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function startUse(t: ElementTemplate) {
		useTarget = t;
		newName = '';
	}

	function cancelUse() {
		useTarget = null;
		newName = '';
	}

	async function confirmUse(event: SubmitEvent) {
		event.preventDefault();
		if (!useTarget || !newName.trim()) return;
		useSubmitting = true;
		const sanitizedName = DOMPurify.sanitize(newName.trim());
		try {
			const body: Record<string, unknown> = {
				template_id: useTarget.id,
				name: sanitizedName,
			};
			if (setId) body.set_id = setId;
			const created = await apiFetch<{ id: string }>('/api/elements', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			useTarget = null;
			newName = '';
			onuse(created.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create from template';
		}
		useSubmitting = false;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			if (useTarget) {
				cancelUse();
			} else {
				oncancel();
			}
		}
	}
</script>

{#if open}
	<dialog
		bind:this={dialogEl}
		onkeydown={handleKeydown}
		aria-labelledby="templates-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 560px; max-width: 90vw; max-height: 80vh; overflow: auto"
	>
		<div class="flex items-start justify-between gap-4">
			<div>
				<h2 id="templates-dialog-title" class="text-lg font-bold">Element Templates</h2>
				<p class="mt-1 text-sm" style="color: var(--color-muted)">
					Choose a template to create a new element with pre-filled fields.
				</p>
			</div>
			<button
				type="button"
				onclick={oncancel}
				aria-label="Close"
				class="rounded p-1"
				style="color: var(--color-muted)"
			>
				✕
			</button>
		</div>

		{#if error}
			<p class="mt-4 text-sm" role="alert" style="color: var(--color-danger)">{error}</p>
		{/if}

		{#if loading}
			<p class="mt-6 text-sm" style="color: var(--color-muted)">Loading templates…</p>
		{:else if templates.length === 0}
			<p class="mt-6 text-sm" style="color: var(--color-muted)">
				No templates available. Open an element and choose "Save as template" to create one.
			</p>
		{:else if useTarget}
			<form onsubmit={confirmUse} class="mt-6 flex flex-col gap-4">
				<div>
					<p class="text-sm" style="color: var(--color-muted)">
						Creating an element from <strong style="color: var(--color-fg)">{useTarget.name}</strong>.
						Pre-filled fields: {useTarget.included_fields.join(', ')}.
					</p>
				</div>
				<div>
					<label for="template-new-name" class="block text-sm font-medium">Element name</label>
					<input
						id="template-new-name"
						bind:value={newName}
						required
						autocomplete="off"
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					/>
				</div>
				<div class="flex justify-end gap-3">
					<button
						type="button"
						onclick={cancelUse}
						class="rounded px-4 py-2 text-sm"
						style="border: 1px solid var(--color-border); color: var(--color-fg)"
					>
						Back
					</button>
					<button
						type="submit"
						disabled={useSubmitting || !newName.trim()}
						class="rounded px-4 py-2 text-sm text-white disabled:opacity-50"
						style="background-color: var(--color-primary)"
					>
						{useSubmitting ? 'Creating…' : 'Create element'}
					</button>
				</div>
			</form>
		{:else}
			<table class="mt-6 w-full text-sm">
				<thead>
					<tr style="border-bottom: 1px solid var(--color-border)">
						<th class="py-2 pr-4 text-left font-medium" style="color: var(--color-muted)">Name</th>
						<th class="py-2 pr-4 text-left font-medium" style="color: var(--color-muted)">Scope</th>
						<th class="py-2 pr-4 text-left font-medium" style="color: var(--color-muted)">Captured fields</th>
						<th class="py-2 text-left font-medium" style="color: var(--color-muted)">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each templates as t (t.id)}
						<tr style="border-bottom: 1px solid var(--color-border)">
							<td class="py-2 pr-4">
								<a href="/element-templates/{t.id}" class="underline" style="color: var(--color-primary)">{t.name}</a>
								{#if t.description}
									<div class="mt-0.5 text-xs" style="color: var(--color-muted)">{t.description}</div>
								{/if}
							</td>
							<td class="py-2 pr-4">
								{#if t.is_global}
									<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); border: 1px solid var(--color-border)">Global</span>
								{:else}
									<span class="text-xs" style="color: var(--color-muted)">{t.set_name ?? t.set_id ?? ''}</span>
								{/if}
							</td>
							<td class="py-2 pr-4 text-xs" style="color: var(--color-muted)">{t.included_fields.join(', ')}</td>
							<td class="py-2">
								<button
									type="button"
									onclick={() => startUse(t)}
									class="rounded px-3 py-1 text-xs text-white"
									style="background-color: var(--color-primary)"
								>
									Use
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</dialog>
{/if}
