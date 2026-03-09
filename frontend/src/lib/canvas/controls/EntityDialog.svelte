<script lang="ts">
	/** Dialog for creating/editing entities on the canvas — with notation dropdown (ADR-081). */
	import DOMPurify from 'dompurify';
	import {
		SIMPLE_ENTITY_TYPES,
		UML_ENTITY_TYPES,
		ARCHIMATE_ENTITY_TYPES,
		C4_ENTITY_TYPES,
		SIMPLE_DIAGRAM_TYPE_FILTER,
		UML_DIAGRAM_TYPE_FILTER,
		ARCHIMATE_DIAGRAM_TYPE_LAYERS,
		C4_DIAGRAM_TYPE_LEVELS,
		type SimpleEntityType,
		type NotationType,
	} from '$lib/types/canvas';
	import TagInput from '$lib/components/TagInput.svelte';
	import NotationPills from '$lib/components/NotationPills.svelte';
	import C4TypePicker from '$lib/c4/C4TypePicker.svelte';
	import { getDefaultNotation } from '$lib/stores/defaultNotation.svelte';

	interface Props {
		open: boolean;
		mode: 'create' | 'edit';
		notation?: NotationType;
		diagramType?: string;
		initialName?: string;
		initialType?: SimpleEntityType;
		initialDescription?: string;
		initialTags?: string[];
		suggestions?: string[];
		inheritedTags?: string[];
		onsave: (name: string, type: SimpleEntityType, description: string, tags?: string[], notation?: string) => void;
		oncancel: () => void;
	}

	let {
		open,
		mode,
		notation = 'simple',
		diagramType,
		initialName = '',
		initialType = 'component',
		initialDescription = '',
		initialTags = [],
		suggestions = [],
		inheritedTags = [],
		onsave,
		oncancel,
	}: Props = $props();

	let name = $state('');
	let entityType = $state<SimpleEntityType>('component');
	let selectedNotation = $state<string>('simple');
	let selectedLayer = $state<string>('');
	let showAllTypes = $state(false);
	let description = $state('');
	let tags = $state<string[]>([]);
	let dialogEl: HTMLDialogElement | undefined = $state();

	/** Layer labels for ArchiMate. */
	const ARCHIMATE_LAYER_LABELS: Record<string, string> = {
		business: 'Business',
		application: 'Application',
		technology: 'Technology',
		motivation: 'Motivation',
		strategy: 'Strategy',
		implementation_migration: 'Implementation & Migration',
	};

	/** Available ArchiMate layers, filtered by diagram type when applicable. */
	let archimateLayerOptions = $derived.by(() => {
		let entries = Object.entries(ARCHIMATE_LAYER_LABELS);
		if (!showAllTypes && diagramType && ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType] !== undefined && ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType] !== null) {
			const allowed = ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType]!;
			entries = entries.filter(([value]) => allowed.includes(value));
		}
		return entries.map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
	});

	/** C4 scope labels — core static model vs deployment (supporting). */
	const C4_SCOPE_LABELS: Record<string, string> = {
		core: 'Core',
		deployment: 'Deployment',
	};

	/** C4 level → scope mapping. */
	const C4_LEVEL_TO_SCOPE: Record<string, string> = {
		system_context: 'core',
		container: 'core',
		component: 'core',
		code: 'core',
		deployment: 'deployment',
	};

	/** Available C4 scopes, filtered by diagram type when applicable. */
	let c4ScopeOptions = $derived.by(() => {
		let entries = Object.entries(C4_SCOPE_LABELS);
		if (!showAllTypes && diagramType && C4_DIAGRAM_TYPE_LEVELS[diagramType] !== undefined && C4_DIAGRAM_TYPE_LEVELS[diagramType] !== null) {
			const allowedLevels = C4_DIAGRAM_TYPE_LEVELS[diagramType]!;
			// Map allowed levels to their scopes
			const allowedScopes = new Set(allowedLevels.map((l) => C4_LEVEL_TO_SCOPE[l]).filter(Boolean));
			entries = entries.filter(([value]) => allowedScopes.has(value));
		}
		return entries.map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
	});

	/** Compute available entity types based on selected notation, diagram type, and sub-filter (ADR-082). */
	let entityTypeOptions = $derived.by(() => {
		let types: { key: string; label: string; icon: string }[];
		switch (selectedNotation) {
			case 'uml': {
				let filtered = UML_ENTITY_TYPES;
				// Apply diagram-type filter for UML (filters by type key)
				if (!showAllTypes && diagramType && UML_DIAGRAM_TYPE_FILTER[diagramType] !== undefined && UML_DIAGRAM_TYPE_FILTER[diagramType] !== null) {
					const allowed = UML_DIAGRAM_TYPE_FILTER[diagramType]!;
					filtered = filtered.filter((t) => allowed.includes(t.key));
				}
				types = filtered.map((t) => ({ key: t.key as string, label: t.label, icon: t.icon }));
				break;
			}
			case 'archimate': {
				let filtered = ARCHIMATE_ENTITY_TYPES;
				if (selectedLayer) {
					filtered = filtered.filter((t) => t.layer === selectedLayer);
				}
				types = filtered.map((t) => ({ key: t.key as string, label: t.label, icon: t.icon }));
				break;
			}
			case 'c4': {
				let filtered = C4_ENTITY_TYPES;
				if (selectedLayer) {
					filtered = filtered.filter((t) => C4_LEVEL_TO_SCOPE[t.level] === selectedLayer);
				}
				types = filtered.map((t) => ({ key: t.key as string, label: t.label, icon: t.icon }));
				break;
			}
			default: {
				let filtered = SIMPLE_ENTITY_TYPES;
				if (!showAllTypes && diagramType && SIMPLE_DIAGRAM_TYPE_FILTER[diagramType] !== undefined && SIMPLE_DIAGRAM_TYPE_FILTER[diagramType] !== null) {
					const allowed = SIMPLE_DIAGRAM_TYPE_FILTER[diagramType]!;
					// Always include note and boundary (universal annotation types)
					filtered = filtered.filter((t) => allowed.includes(t.key) || t.key === 'note' || t.key === 'boundary');
				}
				types = filtered.map((t) => ({ key: t.key as string, label: t.label, icon: t.icon }));
				break;
			}
		}
		return types.sort((a, b) => a.label.localeCompare(b.label));
	});

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			name = initialName;
			entityType = initialType;
			showAllTypes = false;
			const n = notation || getDefaultNotation();
			selectedNotation = n;
			// Auto-select layer/scope: if diagram-type filtering leaves only 1 option, select it
			if (n === 'archimate' && diagramType && !showAllTypes && ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType] !== undefined && ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType] !== null) {
				const allowed = ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType]!;
				selectedLayer = allowed.length === 1 ? allowed[0] : '';
			} else if (n === 'c4') {
				if (diagramType && !showAllTypes && C4_DIAGRAM_TYPE_LEVELS[diagramType] !== undefined && C4_DIAGRAM_TYPE_LEVELS[diagramType] !== null) {
					const allowedLevels = C4_DIAGRAM_TYPE_LEVELS[diagramType]!;
					const allowedScopes = [...new Set(allowedLevels.map((l) => C4_LEVEL_TO_SCOPE[l]).filter(Boolean))];
					selectedLayer = allowedScopes.length === 1 ? allowedScopes[0] : '';
				} else {
					selectedLayer = 'core';
				}
			} else {
				selectedLayer = '';
			}
			description = initialDescription;
			tags = [...initialTags];
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleNotationChange() {
		// Reset sub-filter when notation changes — default C4 to 'core'
		selectedLayer = selectedNotation === 'c4' ? 'core' : '';
		// When notation changes, reset entity type to first type of new notation
		const types = entityTypeOptions;
		if (types.length > 0 && !types.some((t) => t.key === entityType)) {
			entityType = types[0].key as SimpleEntityType;
		}
	}

	function handleLayerChange() {
		// When layer changes, reset entity type to first type of new layer
		const types = entityTypeOptions;
		if (types.length > 0 && !types.some((t) => t.key === entityType)) {
			entityType = types[0].key as SimpleEntityType;
		}
	}

	function handleShowAllChange() {
		// When toggling show-all, reset layer and entity type if needed
		if (!showAllTypes) {
			// Re-apply layer filtering
			if (selectedNotation === 'archimate' && diagramType && ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType] !== undefined && ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType] !== null) {
				const allowed = ARCHIMATE_DIAGRAM_TYPE_LAYERS[diagramType]!;
				if (!allowed.includes(selectedLayer)) selectedLayer = allowed.length === 1 ? allowed[0] : '';
			} else if (selectedNotation === 'c4' && diagramType && C4_DIAGRAM_TYPE_LEVELS[diagramType] !== undefined && C4_DIAGRAM_TYPE_LEVELS[diagramType] !== null) {
				const allowedLevels = C4_DIAGRAM_TYPE_LEVELS[diagramType]!;
				const allowedScopes = [...new Set(allowedLevels.map((l) => C4_LEVEL_TO_SCOPE[l]).filter(Boolean))];
				if (!allowedScopes.includes(selectedLayer)) selectedLayer = allowedScopes.length === 1 ? allowedScopes[0] : '';
			}
		} else {
			// Showing all — reset layer to show everything
			if (selectedNotation === 'c4') selectedLayer = 'core';
			else if (selectedNotation === 'archimate') selectedLayer = '';
		}
		// Reset entity type if current selection no longer valid
		const types = entityTypeOptions;
		if (types.length > 0 && !types.some((t) => t.key === entityType)) {
			entityType = types[0].key as SimpleEntityType;
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
		const sanitizedDesc = DOMPurify.sanitize(description.trim());
		if (sanitizedName) {
			if (mode === 'edit') {
				onsave(sanitizedName, entityType, sanitizedDesc, tags, selectedNotation);
			} else {
				onsave(sanitizedName, entityType, sanitizedDesc, undefined, selectedNotation);
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
		aria-labelledby="entity-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="entity-dialog-title" class="text-lg font-bold">
			{mode === 'create' ? 'Create Element' : 'Edit Element'}
		</h2>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="entity-name" class="block text-sm font-medium">Name</label>
				<input
					id="entity-name"
					bind:value={name}
					required
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			{#if diagramType}
				<input type="hidden" name="entity-notation" value={selectedNotation} />
			{:else}
				<div>
					<label class="block text-sm font-medium mb-1">Notation</label>
					<NotationPills
						value={selectedNotation}
						onchange={(n) => { selectedNotation = n; handleNotationChange(); }}
					/>
				</div>
			{/if}

			{#if selectedNotation === 'archimate' && archimateLayerOptions.length > 1}
				<div>
					<label for="entity-layer" class="block text-sm font-medium">Layer</label>
					<select
						id="entity-layer"
						bind:value={selectedLayer}
						onchange={handleLayerChange}
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						<option value="">All Layers</option>
						{#each archimateLayerOptions as layer}
							<option value={layer.value}>{layer.label}</option>
						{/each}
					</select>
				</div>
			{:else if selectedNotation === 'c4' && c4ScopeOptions.length > 1}
				<div>
					<label for="entity-scope" class="block text-sm font-medium">Scope</label>
					<select
						id="entity-scope"
						bind:value={selectedLayer}
						onchange={handleLayerChange}
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						<option value="">All</option>
						{#each c4ScopeOptions as scope}
							<option value={scope.value}>{scope.label}</option>
						{/each}
					</select>
				</div>
			{/if}

			<div>
				<label for="entity-type" class="block text-sm font-medium">
					{#if diagramType && !showAllTypes}
						Type <span class="text-xs font-normal" style="color: var(--color-muted)">(filtered by {selectedNotation} notation)</span>
					{:else}
						Type
					{/if}
				</label>
				{#if selectedNotation === 'c4'}
					<div class="mt-1">
						<C4TypePicker
							value={entityType}
							onchange={(t) => { entityType = t; }}
							compact
						/>
					</div>
				{:else}
					<select
						id="entity-type"
						bind:value={entityType}
						class="mt-1 w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						{#each entityTypeOptions as t}
							<option value={t.key}>{t.icon} {t.label}</option>
						{/each}
					</select>
				{/if}
				{#if diagramType}
					<label class="mt-1.5 flex items-center gap-1.5 text-xs cursor-pointer" style="color: var(--color-muted)">
						<input type="checkbox" bind:checked={showAllTypes} onchange={handleShowAllChange} />
						Show all types
					</label>
				{/if}
			</div>

			<div>
				<label for="entity-description" class="block text-sm font-medium">Description</label>
				<textarea
					id="entity-description"
					bind:value={description}
					rows="3"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				></textarea>
			</div>

			{#if mode === 'edit'}
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
