<script lang="ts">
	import DOMPurify from 'dompurify';
	import {
		createNamedPrompt,
		deleteNamedPrompt,
		listEffectiveNamedPromptsForCollection,
		listEffectiveNamedPromptsForSet,
		listNamedPromptsForScope,
		updateNamedPrompt,
	} from '$lib/api/named-prompts';
	import {
		NAMED_PROMPT_BODY_MAX,
		NAMED_PROMPT_DESCRIPTION_MAX,
		NAMED_PROMPT_NAME_RE,
		type NamedPrompt,
		type ScopeType,
	} from '$lib/types/named-prompts';

	interface Props {
		scope_type: ScopeType;
		scope_id: string;
	}

	const { scope_type, scope_id }: Props = $props();

	let own = $state<NamedPrompt[]>([]);
	let inherited = $state<NamedPrompt[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let savingIds = $state<Set<string>>(new Set());

	// New-prompt form state.
	let showAddRow = $state(false);
	let newName = $state('');
	let newDescription = $state('');
	let newBody = $state('');
	let creating = $state(false);
	let createError = $state<string | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			own = await listNamedPromptsForScope(scope_type, scope_id);
			if (scope_type === 'set') {
				const effective = await listEffectiveNamedPromptsForSet(scope_id);
				const ownNames = new Set(own.map((p) => p.name));
				inherited = effective.filter((p) => p.scope_type === 'collection' && !ownNames.has(p.name));
			} else {
				// Collections have no parent scope.
				const effective = await listEffectiveNamedPromptsForCollection(scope_id);
				inherited = effective.filter((p) => p.scope_id !== scope_id);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load prompts';
		}
		loading = false;
	}

	$effect(() => {
		// Reload when scope changes.
		void scope_id;
		void scope_type;
		load();
	});

	function _sanitize(text: string): string {
		return DOMPurify.sanitize(text);
	}

	function _markSaving(id: string, on: boolean) {
		const next = new Set(savingIds);
		if (on) next.add(id);
		else next.delete(id);
		savingIds = next;
	}

	async function handleCreate() {
		createError = null;
		const name = newName.trim();
		const description = newDescription.trim();
		const body = newBody.trim();

		if (!NAMED_PROMPT_NAME_RE.test(name)) {
			createError = 'Name must start with a lowercase letter and contain only lowercase letters, digits, and hyphens.';
			return;
		}
		if (description.length < 1 || description.length > NAMED_PROMPT_DESCRIPTION_MAX) {
			createError = `Description must be 1–${NAMED_PROMPT_DESCRIPTION_MAX} characters.`;
			return;
		}
		if (body.length < 1 || body.length > NAMED_PROMPT_BODY_MAX) {
			createError = `Body must be 1–${NAMED_PROMPT_BODY_MAX} characters.`;
			return;
		}

		creating = true;
		try {
			const created = await createNamedPrompt({
				scope_type,
				scope_id,
				name,
				description: _sanitize(description),
				body: _sanitize(body),
			});
			own = [...own, created].sort((a, b) => a.name.localeCompare(b.name));
			showAddRow = false;
			newName = '';
			newDescription = '';
			newBody = '';
		} catch (e) {
			createError = e instanceof Error ? e.message : 'Failed to create prompt';
		}
		creating = false;
	}

	async function handleSave(prompt: NamedPrompt, description: string, body: string) {
		_markSaving(prompt.id, true);
		try {
			const updated = await updateNamedPrompt(prompt.id, {
				description: _sanitize(description.trim()),
				body: _sanitize(body.trim()),
			});
			own = own.map((p) => (p.id === updated.id ? updated : p));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save prompt';
		}
		_markSaving(prompt.id, false);
	}

	async function handleDelete(prompt: NamedPrompt) {
		if (!confirm(`Delete prompt "${prompt.name}"? This cannot be undone.`)) return;
		_markSaving(prompt.id, true);
		try {
			await deleteNamedPrompt(prompt.id);
			own = own.filter((p) => p.id !== prompt.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete prompt';
		}
		_markSaving(prompt.id, false);
	}
</script>

<section class="mt-6">
	<div class="flex items-center justify-between">
		<h2 class="text-base font-semibold" style="color: var(--color-fg)">Prompts</h2>
		<button
			type="button"
			onclick={() => { showAddRow = !showAddRow; createError = null; }}
			class="rounded px-3 py-1 text-sm"
			style="background: var(--color-primary); color: var(--color-bg)"
		>
			{showAddRow ? 'Cancel' : '+ Add prompt'}
		</button>
	</div>
	<p class="mt-1 text-xs" style="color: var(--color-muted)">
		User-picked named prompts surfaced via MCP. Unlike the System prompt, named prompts do not auto-apply to Ask Iris.
	</p>

	{#if loading}
		<p class="mt-3 text-sm" style="color: var(--color-muted)">Loading prompts…</p>
	{/if}
	{#if error}
		<p class="mt-3 text-sm text-red-600">{error}</p>
	{/if}

	{#if showAddRow}
		<div class="mt-3 rounded border p-3" style="border-color: var(--color-border)">
			<div class="grid grid-cols-1 gap-2 md:grid-cols-2">
				<input
					type="text"
					bind:value={newName}
					placeholder="prompt-name (lowercase, hyphens)"
					maxlength="64"
					class="rounded border px-2 py-1 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
				<input
					type="text"
					bind:value={newDescription}
					placeholder="Short description shown in the MCP picker"
					maxlength={NAMED_PROMPT_DESCRIPTION_MAX}
					class="rounded border px-2 py-1 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>
			<textarea
				bind:value={newBody}
				rows="6"
				maxlength={NAMED_PROMPT_BODY_MAX}
				placeholder="Prompt body (markdown OK)"
				class="mt-2 w-full rounded border px-2 py-1 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); font-family: var(--font-mono, monospace)"
			></textarea>
			{#if createError}
				<p class="mt-2 text-xs text-red-600">{createError}</p>
			{/if}
			<div class="mt-2 flex justify-end gap-2">
				<button
					type="button"
					onclick={handleCreate}
					disabled={creating}
					class="rounded px-3 py-1 text-sm"
					style="background: var(--color-primary); color: var(--color-bg)"
				>
					{creating ? 'Saving…' : 'Save'}
				</button>
			</div>
		</div>
	{/if}

	{#if own.length > 0}
		<ul class="mt-3 space-y-3">
			{#each own as prompt (prompt.id)}
				<li class="rounded border p-3" style="border-color: var(--color-border)">
					{@render promptRow(prompt)}
				</li>
			{/each}
		</ul>
	{/if}

	{#if inherited.length > 0}
		<h3 class="mt-6 text-sm font-medium" style="color: var(--color-muted)">
			Inherited from parent
		</h3>
		<ul class="mt-2 space-y-3">
			{#each inherited as prompt (prompt.id)}
				<li class="rounded border p-3" style="border-color: var(--color-border); opacity: 0.7">
					<div class="text-sm font-medium" style="color: var(--color-fg)">{prompt.name}</div>
					<p class="mt-1 text-xs" style="color: var(--color-muted)">{prompt.description}</p>
					<p class="mt-1 text-xs italic" style="color: var(--color-muted)">
						Edit on the parent {prompt.scope_type}'s page.
					</p>
				</li>
			{/each}
		</ul>
	{/if}
</section>

{#snippet promptRow(prompt: NamedPrompt)}
	{@const isSaving = savingIds.has(prompt.id)}
	{@const initialDescription = prompt.description}
	{@const initialBody = prompt.body}
	{@render editor(prompt, initialDescription, initialBody, isSaving)}
{/snippet}

{#snippet editor(prompt: NamedPrompt, initialDescription: string, initialBody: string, isSaving: boolean)}
	<div>
		<div class="flex items-center justify-between">
			<div class="text-sm font-medium" style="color: var(--color-fg)">{prompt.name}</div>
			<button
				type="button"
				onclick={() => handleDelete(prompt)}
				disabled={isSaving}
				class="text-xs"
				style="color: var(--color-danger, #b00)"
			>Delete</button>
		</div>
		<form
			class="mt-2"
			onsubmit={(e) => {
				e.preventDefault();
				const form = e.currentTarget as HTMLFormElement;
				const data = new FormData(form);
				const desc = String(data.get('description') ?? '');
				const body = String(data.get('body') ?? '');
				handleSave(prompt, desc, body);
			}}
		>
			<input
				type="text"
				name="description"
				value={initialDescription}
				maxlength={NAMED_PROMPT_DESCRIPTION_MAX}
				class="w-full rounded border px-2 py-1 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
			<textarea
				name="body"
				rows="6"
				maxlength={NAMED_PROMPT_BODY_MAX}
				class="mt-2 w-full rounded border px-2 py-1 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); font-family: var(--font-mono, monospace)"
				>{initialBody}</textarea>
			<div class="mt-2 flex justify-end">
				<button
					type="submit"
					disabled={isSaving}
					class="rounded px-3 py-1 text-sm"
					style="background: var(--color-primary); color: var(--color-bg)"
				>
					{isSaving ? 'Saving…' : 'Save'}
				</button>
			</div>
		</form>
	</div>
{/snippet}
