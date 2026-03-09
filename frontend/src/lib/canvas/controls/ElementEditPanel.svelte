<script lang="ts">
	/**
	 * ElementEditPanel: Inline element editor for the canvas sidebar.
	 * Two modes:
	 * 1. Linked (entityId provided): loads/saves via element API, supports tags.
	 * 2. Unlinked (no entityId): edits canvas node data directly via DOM event.
	 * Emits 'elementeditsaved' CustomEvent on save so the page can update the
	 * canvas node to reflect changes.
	 */
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Element } from '$lib/types/api';
	import type { NotationType } from '$lib/types/canvas';
	import {
		SIMPLE_ENTITY_TYPES,
		UML_ENTITY_TYPES,
		ARCHIMATE_ENTITY_TYPES,
		C4_ENTITY_TYPES,
	} from '$lib/types/canvas';
	import C4TypePicker from '$lib/c4/C4TypePicker.svelte';
	import DOMPurify from 'dompurify';

	interface Props {
		entityId?: string | null;
		nodeId: string;
		notation?: NotationType;
		/** Fallback label for unlinked nodes. */
		nodeLabel?: string;
		/** Fallback description for unlinked nodes. */
		nodeDescription?: string;
		/** Fallback entity type for unlinked nodes. */
		nodeEntityType?: string;
	}

	let { entityId, nodeId, notation, nodeLabel = '', nodeDescription = '', nodeEntityType = 'component' }: Props = $props();

	const isLinked = $derived(!!entityId);

	let element = $state<Element | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);

	let editName = $state('');
	let editDescription = $state('');
	let editElementType = $state('');
	let editTags = $state<string[]>([]);
	let newTag = $state('');

	// Track original values for unlinked dirty detection
	let origName = $state('');
	let origDescription = $state('');
	let origEntityType = $state('');

	const dirty = $derived.by(() => {
		if (isLinked) {
			if (!element) return false;
			return (
				editName !== element.name ||
				editDescription !== (element.description ?? '') ||
				editElementType !== element.element_type ||
				JSON.stringify(editTags.slice().sort()) !== JSON.stringify((element.tags ?? []).slice().sort())
			);
		}
		return (
			editName !== origName ||
			editDescription !== origDescription ||
			editElementType !== origEntityType
		);
	});

	const entityTypeOptions = $derived.by(() => {
		const n = element?.notation ?? notation ?? 'simple';
		switch (n) {
			case 'uml': return UML_ENTITY_TYPES.map((t) => ({ key: t.key, label: t.label, icon: t.icon }));
			case 'archimate': return ARCHIMATE_ENTITY_TYPES.map((t) => ({ key: t.key, label: t.label, icon: t.icon }));
			case 'c4': return C4_ENTITY_TYPES.map((t) => ({ key: t.key, label: t.label, icon: t.icon }));
			default: return SIMPLE_ENTITY_TYPES.map((t) => ({ key: t.key, label: t.label, icon: t.icon }));
		}
	});

	const effectiveNotation = $derived(element?.notation ?? notation ?? 'simple');

	$effect(() => {
		if (entityId) {
			void entityId;
			loadElement();
		} else {
			// Unlinked node: populate from props
			editName = nodeLabel;
			editDescription = nodeDescription;
			editElementType = nodeEntityType;
			origName = nodeLabel;
			origDescription = nodeDescription;
			origEntityType = nodeEntityType;
			element = null;
			loading = false;
		}
	});

	async function loadElement() {
		loading = true;
		error = null;
		try {
			element = await apiFetch<Element>(`/api/elements/${entityId}`);
			editName = element.name;
			editDescription = element.description ?? '';
			editElementType = element.element_type;
			editTags = [...(element.tags ?? [])];
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to load element';
		}
		loading = false;
	}

	async function save() {
		saving = true;
		error = null;

		const sanitizedName = DOMPurify.sanitize(editName).trim();
		const sanitizedDesc = DOMPurify.sanitize(editDescription).trim();
		if (!sanitizedName) {
			error = 'Name is required';
			saving = false;
			return;
		}

		if (isLinked && element) {
			try {
				await apiFetch(`/api/elements/${element.id}`, {
					method: 'PUT',
					headers: { 'If-Match': String(element.current_version) },
					body: JSON.stringify({
						name: sanitizedName,
						element_type: editElementType || element.element_type,
						description: sanitizedDesc,
						change_summary: 'Updated from diagram editor',
					}),
				});

				// Sync tags
				const oldTags = element.tags ?? [];
				const toAdd = editTags.filter((t) => !oldTags.includes(t));
				const toRemove = oldTags.filter((t) => !editTags.includes(t));
				for (const tag of toAdd) {
					await apiFetch(`/api/elements/${element.id}/tags`, {
						method: 'POST',
						body: JSON.stringify({ tag }),
					});
				}
				for (const tag of toRemove) {
					await apiFetch(`/api/elements/${element.id}/tags/${encodeURIComponent(tag)}`, {
						method: 'DELETE',
					});
				}

				// Notify parent to update canvas node
				document.dispatchEvent(
					new CustomEvent('elementeditsaved', {
						detail: {
							nodeId,
							name: sanitizedName,
							description: sanitizedDesc,
							elementType: editElementType,
						},
					}),
				);

				// Reload to get fresh version number
				await loadElement();
			} catch (e) {
				error = e instanceof ApiError ? e.message : 'Failed to save element';
			}
		} else {
			// Unlinked node: update canvas data directly via event
			document.dispatchEvent(
				new CustomEvent('elementeditsaved', {
					detail: {
						nodeId,
						name: sanitizedName,
						description: sanitizedDesc,
						elementType: editElementType,
					},
				}),
			);
			origName = sanitizedName;
			origDescription = sanitizedDesc;
			origEntityType = editElementType;
			editName = sanitizedName;
			editDescription = sanitizedDesc;
		}
		saving = false;
	}

	function discard() {
		if (isLinked && element) {
			editName = element.name;
			editDescription = element.description ?? '';
			editElementType = element.element_type;
			editTags = [...(element.tags ?? [])];
		} else {
			editName = origName;
			editDescription = origDescription;
			editElementType = origEntityType;
		}
		error = null;
		emitPreview();
	}

	function addTag() {
		const tag = newTag.trim();
		if (tag && !editTags.includes(tag)) {
			editTags = [...editTags, tag];
		}
		newTag = '';
	}

	function removeTag(tag: string) {
		editTags = editTags.filter((t) => t !== tag);
	}

	function emitPreview() {
		document.dispatchEvent(
			new CustomEvent('elementeditpreview', {
				detail: { nodeId, name: editName, description: editDescription, elementType: editElementType },
			}),
		);
	}

	function handleTagKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addTag();
		}
	}
</script>

<div class="rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
	<h4 class="mb-2 text-xs font-semibold uppercase" style="color: var(--color-muted)">Element Details</h4>

	{#if loading}
		<p class="text-xs" style="color: var(--color-muted)">Loading...</p>
	{:else if error && !editName}
		<p class="text-xs" style="color: var(--color-danger, #ef4444)">{error}</p>
	{:else}
		<div class="flex flex-col gap-2">
			{#if error}
				<p class="text-xs" style="color: var(--color-danger, #ef4444)">{error}</p>
			{/if}
			<label class="text-xs" style="color: var(--color-fg)">
				Name
				<input
					type="text"
					bind:value={editName}
					oninput={emitPreview}
					class="mt-0.5 block w-full rounded border px-2 py-1 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</label>

			<label class="text-xs" style="color: var(--color-fg)">
				Description
				<textarea
					bind:value={editDescription}
					oninput={emitPreview}
					rows="3"
					class="mt-0.5 block w-full rounded border px-2 py-1 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				></textarea>
			</label>

			<div class="text-xs" style="color: var(--color-fg)">
				<span>Type</span>
				{#if effectiveNotation === 'c4'}
					<div class="mt-0.5">
						<C4TypePicker
							compact
							value={editElementType}
							onchange={(t) => { editElementType = t; emitPreview(); }}
						/>
					</div>
				{:else}
					<select
						bind:value={editElementType}
						onchange={emitPreview}
						class="mt-0.5 block w-full rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						{#each entityTypeOptions as t}
							<option value={t.key}>{t.icon} {t.label}</option>
						{/each}
					</select>
				{/if}
			</div>

			{#if isLinked}
				<div class="text-xs" style="color: var(--color-fg)">
					<span>Tags</span>
					<div class="mt-0.5 flex flex-wrap gap-1">
						{#each editTags as tag}
							<span class="inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">
								{tag}
								<button onclick={() => removeTag(tag)} class="ml-0.5 text-xs leading-none" style="color: white; opacity: 0.7" aria-label="Remove tag {tag}">&times;</button>
							</span>
						{/each}
					</div>
					<div class="mt-1 flex gap-1">
						<input
							type="text"
							bind:value={newTag}
							onkeydown={handleTagKeydown}
							placeholder="Add tag..."
							class="flex-1 rounded border px-2 py-0.5 text-xs"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
						<button
							onclick={addTag}
							disabled={!newTag.trim()}
							class="rounded px-2 py-0.5 text-xs disabled:opacity-50"
							style="border: 1px solid var(--color-border); color: var(--color-fg)"
						>
							Add
						</button>
					</div>
				</div>
			{/if}

			<div class="mt-1 flex items-center gap-2">
				<button
					onclick={save}
					disabled={!dirty || saving}
					class="rounded px-2 py-1 text-xs text-white disabled:opacity-50"
					style="background-color: var(--color-success, #16a34a)"
				>
					{saving ? 'Saving...' : 'Save'}
				</button>
				<button
					onclick={discard}
					disabled={!dirty}
					class="rounded px-2 py-1 text-xs disabled:opacity-50"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					Discard
				</button>
				{#if dirty}
					<span class="text-xs" style="color: var(--color-muted)">Unsaved</span>
				{/if}
			</div>

			{#if isLinked && element}
				<a
					href="/elements/{element.id}"
					class="mt-1 block text-center rounded px-2 py-1 text-xs"
					style="border: 1px solid var(--color-primary); color: var(--color-primary)"
				>
					Open Full Element Page
				</a>
			{/if}
		</div>
	{/if}
</div>
