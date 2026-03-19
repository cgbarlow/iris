<script lang="ts">
	/** Dialog for creating/editing diagrams — notation-first flow (ADR-081). */
	import DOMPurify from 'dompurify';
	import TagInput from '$lib/components/TagInput.svelte';
	import NotationPills from '$lib/components/NotationPills.svelte';
	import { apiFetch } from '$lib/utils/api';
	import type { DiagramTypeRegistry, NotationMapping } from '$lib/types/api';
	import { getDefaultNotation } from '$lib/stores/defaultNotation.svelte';

	interface Props {
		open: boolean;
		mode: 'create' | 'edit';
		initialName?: string;
		initialType?: string;
		initialNotation?: string;
		initialDescription?: string;
		initialTags?: string[];
		initialIsTemplate?: boolean;
		suggestions?: string[];
		inheritedTags?: string[];
		onsave: (name: string, diagramType: string, description: string, tags?: string[], isTemplate?: boolean, notation?: string) => void;
		oncancel: () => void;
	}

	let {
		open,
		mode,
		initialName = '',
		initialType = 'component',
		initialNotation = '',
		initialDescription = '',
		initialTags = [],
		initialIsTemplate = false,
		suggestions = [],
		inheritedTags = [],
		onsave,
		oncancel,
	}: Props = $props();

	let name = $state('');
	let diagramType = $state('');
	let notation = $state('');
	let description = $state('');
	let tags = $state<string[]>([]);
	let isTemplate = $state(false);
	let dialogEl: HTMLDialogElement | undefined = $state();

	// Registry data
	let registryTypes = $state<DiagramTypeRegistry[]>([]);
	let registryLoaded = $state(false);

	/** Hardcoded notation→type fallback mapping (from ADR-079 matrix). */
	const NOTATION_TYPE_FALLBACK: Record<string, { value: string; label: string }[]> = {
		simple: [
			{ value: 'component', label: 'Component' },
			{ value: 'sequence', label: 'Sequence' },
			{ value: 'deployment', label: 'Deployment' },
			{ value: 'process', label: 'Process' },
			{ value: 'roadmap', label: 'Roadmap' },
			{ value: 'free_form', label: 'Free Form' },
			{ value: 'use_case', label: 'Use Case' },
			{ value: 'state_machine', label: 'State Machine' },
			{ value: 'system_context', label: 'System Context' },
			{ value: 'container', label: 'Container' },
		],
		uml: [
			{ value: 'component', label: 'Component' },
			{ value: 'sequence', label: 'Sequence' },
			{ value: 'class', label: 'Class' },
			{ value: 'deployment', label: 'Deployment' },
			{ value: 'process', label: 'Process' },
			{ value: 'free_form', label: 'Free Form' },
			{ value: 'use_case', label: 'Use Case' },
			{ value: 'state_machine', label: 'State Machine' },
		],
		archimate: [
			{ value: 'component', label: 'Component' },
			{ value: 'deployment', label: 'Deployment' },
			{ value: 'process', label: 'Process' },
			{ value: 'free_form', label: 'Free Form' },
			{ value: 'roadmap', label: 'Roadmap' },
			{ value: 'motivation', label: 'Motivation' },
			{ value: 'strategy', label: 'Strategy' },
		],
		c4: [
			{ value: 'component', label: 'Component' },
			{ value: 'deployment', label: 'Deployment' },
			{ value: 'free_form', label: 'Free Form' },
			{ value: 'sequence', label: 'Sequence' },
			{ value: 'system_context', label: 'System Context' },
			{ value: 'container', label: 'Container' },
		],
	};

	/** Diagram types filtered by the selected notation. */
	let filteredTypes = $derived.by(() => {
		if (registryTypes.length > 0) {
			return registryTypes
				.filter((t) => t.notations.some((n) => n.notation_id === notation))
				.map((t) => ({ value: t.id, label: t.name }));
		}
		return NOTATION_TYPE_FALLBACK[notation] ?? NOTATION_TYPE_FALLBACK['simple'];
	});

	async function loadRegistry() {
		if (registryLoaded) return;
		try {
			registryTypes = await apiFetch<DiagramTypeRegistry[]>('/api/registry/diagram-types');
			registryLoaded = true;
		} catch {
			registryTypes = [];
		}
	}

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			loadRegistry();
			name = initialName;
			description = initialDescription;
			tags = [...initialTags];
			isTemplate = initialIsTemplate;
			// Set notation: use initial if provided, otherwise user default
			notation = initialNotation || getDefaultNotation();
			diagramType = initialType;
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleNotationChange() {
		// When notation changes, reset diagram type to first available type
		const types = filteredTypes;
		if (types.length > 0 && !types.some((t) => t.value === diagramType)) {
			diagramType = types[0].value;
		}
	}

	function handleAddTag(tag: string) {
		if (!tags.includes(tag)) {
			tags = [...tags, tag];
		}
	}

	function handleRemoveTag(tag: string) {
		tags = tags.filter((t) => t !== tag);
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		const sanitizedName = DOMPurify.sanitize(name.trim());
		const sanitizedType = DOMPurify.sanitize(diagramType.trim());
		const sanitizedDesc = DOMPurify.sanitize(description.trim());
		if (sanitizedName && sanitizedType) {
			if (mode === 'edit') {
				onsave(sanitizedName, sanitizedType, sanitizedDesc, tags, isTemplate, notation || undefined);
			} else {
				onsave(sanitizedName, sanitizedType, sanitizedDesc, undefined, undefined, notation || undefined);
			}
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			oncancel();
		}
	}
</script>

{#if open}
	<dialog
		bind:this={dialogEl}
		onkeydown={handleKeydown}
		aria-labelledby="diagram-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="diagram-dialog-title" class="text-lg font-bold">
			{mode === 'create' ? 'Create Diagram' : 'Edit Diagram'}
		</h2>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="diagram-name" class="block text-sm font-medium">Name</label>
				<input
					id="diagram-name"
					bind:value={name}
					required
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			<div>
				<label class="block text-sm font-medium mb-1">Notation</label>
				<NotationPills
					value={notation}
					onchange={(n) => { notation = n; handleNotationChange(); }}
				/>
			</div>

			<div>
				<label for="diagram-type" class="block text-sm font-medium">Diagram Type</label>
				{#if mode === 'create'}
					<select
						id="diagram-type"
						bind:value={diagramType}
						required
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						<option value="" disabled>Select a type…</option>
						{#each filteredTypes as t}
							<option value={t.value}>{t.label}</option>
						{/each}
					</select>
				{:else}
					<input
						id="diagram-type"
						value={diagramType}
						readonly
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-muted)"
					/>
				{/if}
			</div>

			<div>
				<label for="diagram-description" class="block text-sm font-medium">Description</label>
				<textarea
					id="diagram-description"
					bind:value={description}
					rows="3"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				></textarea>
			</div>

			{#if mode === 'edit'}
				<div>
					<label class="flex items-center gap-2 text-sm font-medium cursor-pointer">
						<input
							type="checkbox"
							bind:checked={isTemplate}
							aria-label="Mark as template"
						/>
						Template
					</label>
					<p class="mt-1 text-xs" style="color: var(--color-muted)">Mark this diagram as a reusable template</p>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2">Tags</label>
					<TagInput
						{tags}
						onaddtag={handleAddTag}
						onremovetag={handleRemoveTag}
						{inheritedTags}
						{suggestions}
					/>
				</div>
			{/if}

			<div class="flex justify-end gap-3">
				<button
					type="button"
					onclick={oncancel}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					Cancel
				</button>
				<button
					type="submit"
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					{mode === 'create' ? 'Create' : 'Save'}
				</button>
			</div>
		</form>
	</dialog>
{/if}
