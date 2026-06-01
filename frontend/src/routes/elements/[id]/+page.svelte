<script lang="ts">
	import { page } from '$app/state';
	import { canWrite } from '$lib/stores/auth.svelte.js';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { joinTaggedValue, splitTaggedValue } from '$lib/utils/taggedValues';
	import { openScenia } from '$lib/scenia/config.js';
	import { addAiContextItem, removeAiContextItem, getAiContextItems } from '$lib/stores/aiContext.svelte.js';
	import { recordVisit } from '$lib/stores/visitHistory.svelte.js';

	import type {
		Element,
		ElementVersion,
		Relationship,
		RelationshipListResponse,
		ElementDiagramRef,
		Bookmark,
	} from '$lib/types/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import EntityImagesEditor from '$lib/components/EntityImagesEditor.svelte';
	import TagInput from '$lib/components/TagInput.svelte';
	import CommentsPanel from '$lib/components/CommentsPanel.svelte';
	import VersionHistory from '$lib/components/VersionHistory.svelte';
	import CreateTemplateDialog from '$lib/components/CreateTemplateDialog.svelte';
	import DiagramPicker from '$lib/components/DiagramPicker.svelte';
	import HierarchySidebar from '$lib/components/HierarchySidebar.svelte';
	import type { Diagram } from '$lib/types/api';
	import { Accordion } from 'bits-ui';
	import DOMPurify from 'dompurify';
	import {
		SIMPLE_ENTITY_TYPES,
		UML_ENTITY_TYPES,
		ARCHIMATE_ENTITY_TYPES,
		C4_ENTITY_TYPES,
	} from '$lib/types/canvas';
	import C4TypePicker from '$lib/c4/C4TypePicker.svelte';
	import C4TypeGlyph from '$lib/c4/C4TypeGlyph.svelte';

	let entity = $state<Element | null>(null);
	let versions = $state<ElementVersion[]>([]);
	let relationships = $state<Relationship[]>([]);
	let usedInModels = $state<ElementDiagramRef[]>([]);
	let inheritedTags = $state<string[]>([]);
	let allTags = $state<string[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	// ADR-208 (v6.16.0): tab order Relationships, Details, Version History.
	// The `diagrams` value is accepted but coerced to 'relationships' if a
	// persisted set preference still carries it from before the merge.
	let activeTab = $state<'details' | 'versions' | 'relationships'>('relationships');
	let userSelectedTab = $state(false);
	let packageMemberships = $state<{id: string; name: string}[]>([]);
	// ADR-232 (issue 3): the shared hierarchy sidebar, collapsed by default.
	let sidebarOpen = $state(false);
	// ADR-231: child elements owned by this element (containment hierarchy).
	let childElements = $state<{id: string; name: string; element_type: string}[]>([]);
	let showDeleteDialog = $state(false);
	let showSaveTemplateDialog = $state(false);
	let isBookmarked = $state(false);
	let bookmarkLoading = $state(false);

	// AI context state
	let contextItems = $derived(getAiContextItems());
	let isInContext = $derived(entity ? contextItems.some((i) => i.id === entity!.id) : false);

	// Inline metadata editing state
	let editingDetails = $state(false);
	let detailsDirty = $state(false);
	let savingDetails = $state(false);
	let editName = $state('');
	let editDescription = $state('');
	let editTags = $state<string[]>([]);
	let editAttributes = $state<{name: string; type: string; scope: string; notes: string; lower_bound: string; upper_bound: string}[]>([]);
	// ADR-184 — element ↔ package optional membership. ``null`` means
	// no package; empty string is treated identically to null in the
	// submit logic.
	let editPackageId = $state<string | null>(null);
	interface PackageOption { id: string; name: string }
	let setPackages = $state<PackageOption[]>([]);
	let editElementType = $state('');
	// ADR-228 — `metadata` is now editable. Status + the eleven extended
	// scalars get plain text inputs in edit mode; tagged_values become
	// an editable grid with #NOTES# split per row.
	let editStatus = $state('');
	let editStereotype = $state('');
	let editMetaVersion = $state('');
	let editScope = $state('');
	let editAbstract = $state('');
	let editPersistence = $state('');
	let editAuthor = $state('');
	let editComplexity = $state('');
	let editPhase = $state('');
	let editCreatedDate = $state('');
	let editModifiedDate = $state('');
	let editGenType = $state('');
	let editTaggedValues = $state<{ property: string; value: string; notes: string }[]>([]);
	// ADR-221 — element → detail diagram drill link. ``detailDiagramName``
	// is the resolved name shown in read mode; the edit-mode picker
	// updates ``editDetailDiagramId`` / ``editDetailDiagramName``.
	let detailDiagramName = $state<string | null>(null);
	let editDetailDiagramId = $state<string | null>(null);
	let editDetailDiagramName = $state<string | null>(null);
	let showDetailDiagramPicker = $state(false);

	/** Entity type options for the current element's notation. */
	const entityTypeOptions = $derived.by(() => {
		if (!entity) return [];
		switch (entity.notation) {
			case 'uml': return UML_ENTITY_TYPES.map((t) => ({ key: t.key, label: t.label, icon: t.icon }));
			case 'archimate': return ARCHIMATE_ENTITY_TYPES.map((t) => ({ key: t.key, label: t.label, icon: t.icon }));
			case 'c4': return C4_ENTITY_TYPES.map((t) => ({ key: t.key, label: t.label, icon: t.icon }));
			default: return SIMPLE_ENTITY_TYPES.map((t) => ({ key: t.key, label: t.label, icon: t.icon }));
		}
	});

	// Loading states per tab
	let versionsLoading = $state(false);
	let relationshipsLoading = $state(false);
	let diagramsLoading = $state(false);

	$effect(() => {
		const id = page.params.id;
		if (id) loadEntity(id);
	});

	// Auto-enter edit mode when ?edit=true is in the URL
	$effect(() => {
		if (entity && !loading && page.url.searchParams.get('edit') === 'true') {
			enterDetailsEdit();
		}
	});

	// Track dirty state for inline editing
	$effect(() => {
		if (!editingDetails || !entity) return;
		const nameChanged = editName !== entity.name;
		const descChanged = editDescription !== (entity.description ?? '');
		const origTags = entity.tags ?? [];
		const tagsChanged = JSON.stringify(editTags.slice().sort()) !== JSON.stringify(origTags.slice().sort());
		const origAttrs = (entity.data as Record<string, unknown>)?.attributes;
		const attrsChanged = JSON.stringify(editAttributes) !== JSON.stringify(
			Array.isArray(origAttrs) ? origAttrs.map((a: any) => ({ name: a.name ?? '', type: a.type ?? '', scope: a.scope ?? 'Public', notes: a.notes ?? '', lower_bound: a.lower_bound ?? '', upper_bound: a.upper_bound ?? '' })) : []
		);
		const typeChanged = editElementType !== entity.element_type;
		const pkgChanged = (editPackageId ?? null) !== ((entity as any).package_id ?? null);
		const detailDiagramChanged = (editDetailDiagramId ?? null) !== (entity.detail_diagram_id ?? null);
		// ADR-228: any edit to status / the eleven extended scalars /
		// the tagged-values rows flips the dirty flag. Compare the
		// rebuilt metadata against the entity's current value — same
		// JSON-equality approach used for attributes above.
		const origMeta = (entity.metadata ?? {}) as Record<string, unknown>;
		const editedMeta: Record<string, unknown> = { ...origMeta };
		const apply = (k: string, v: string) => {
			if (v.trim()) editedMeta[k] = v;
			else delete editedMeta[k];
		};
		apply('status', editStatus);
		apply('stereotype', editStereotype);
		apply('version', editMetaVersion);
		apply('scope', editScope);
		apply('abstract', editAbstract);
		apply('persistence', editPersistence);
		apply('author', editAuthor);
		apply('complexity', editComplexity);
		apply('phase', editPhase);
		apply('created_date', editCreatedDate);
		apply('modified_date', editModifiedDate);
		apply('gen_type', editGenType);
		const rebuiltTV = editTaggedValues
			.filter((r) => r.property.trim())
			.map((r) => ({
				property: r.property,
				value: joinTaggedValue(r.value, r.notes) || null,
			}));
		if (rebuiltTV.length) editedMeta.tagged_values = rebuiltTV;
		else delete editedMeta.tagged_values;
		const metaChanged = JSON.stringify(editedMeta) !== JSON.stringify(origMeta);
		detailsDirty = nameChanged || descChanged || tagsChanged || attrsChanged || typeChanged || pkgChanged || detailDiagramChanged || metaChanged;
	});

	async function loadEntity(id: string) {
		loading = true;
		error = null;
		try {
			entity = await apiFetch<Element>(`/api/elements/${id}`);
			recordVisit({ id: entity.id, type: 'element', name: entity.name, detail: entity.element_type, setId: entity.set_id ?? undefined, setName: entity.set_name ?? undefined, description: entity.description ?? undefined, href: `/elements/${entity.id}` });
			// Load tab data in parallel
			await Promise.all([
				loadVersions(id),
				loadRelationships(id),
				loadDiagrams(id),
				loadPackageMemberships(id),
				loadChildElements(id),
				loadDetailDiagramName(),
				loadAllTags(),
				loadBookmarkStatus(id),
			]);
			// ADR-208 (v6.16.0): seed activeTab from the parent set's
			// element_tab_default unless the user has already clicked a
			// tab. Mirrors the v6.14.0 view-page pattern.
			if (!userSelectedTab && entity.set_id) {
				try {
					const setData = await apiFetch<{element_tab_default?: string}>(`/api/sets/${entity.set_id}`);
					const preferred = setData.element_tab_default;
					if (preferred === 'relationships' || preferred === 'details' || preferred === 'versions') {
						activeTab = preferred;
					} else {
						// 'diagrams' or any unknown value → coerce to relationships
						// (the standalone diagrams tab no longer exists).
						activeTab = 'relationships';
					}
				} catch {
					activeTab = 'relationships';
				}
			}
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Element not found'
				: 'Failed to load element';
		}
		loading = false;
	}

	async function loadPackageMemberships(id: string) {
		try {
			packageMemberships = await apiFetch<{id: string; name: string}[]>(`/api/elements/${id}/package-memberships`);
		} catch {
			packageMemberships = [];
		}
	}

	// ADR-231: direct child elements in the containment hierarchy.
	async function loadChildElements(id: string) {
		try {
			childElements = await apiFetch<{id: string; name: string; element_type: string}[]>(`/api/elements/${id}/children`);
		} catch {
			childElements = [];
		}
	}

	// ADR-221: resolve the detail diagram's name for the read-mode drill
	// link. Element responses carry only the id.
	async function loadDetailDiagramName() {
		const detailId = entity?.detail_diagram_id ?? null;
		if (!detailId) {
			detailDiagramName = null;
			return;
		}
		try {
			const d = await apiFetch<Diagram>(`/api/diagrams/${detailId}`);
			detailDiagramName = d.name;
		} catch {
			detailDiagramName = null;
		}
	}

	async function loadVersions(id: string) {
		versionsLoading = true;
		try {
			versions = await apiFetch<ElementVersion[]>(`/api/elements/${id}/versions`);
		} catch {
			versions = [];
		}
		versionsLoading = false;
	}

	async function handleElementRollback(version: number) {
		if (!entity) return;
		try {
			await apiFetch(`/api/elements/${entity.id}/rollback`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', 'If-Match': String(entity.current_version) },
				body: JSON.stringify({ target_version: version }),
			});
			await loadEntity(entity.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Rollback failed';
		}
	}

	async function loadRelationships(id: string) {
		relationshipsLoading = true;
		try {
			const data = await apiFetch<RelationshipListResponse>(`/api/relationships?element_id=${id}`);
			relationships = data.items;
		} catch {
			relationships = [];
		}
		relationshipsLoading = false;
	}

	async function loadDiagrams(id: string) {
		diagramsLoading = true;
		try {
			usedInModels = await apiFetch<ElementDiagramRef[]>(`/api/elements/${id}/diagrams`);
			// Compute inherited tags from diagrams this element appears in
			const diagramTags = new Set<string>();
			for (const ref of usedInModels) {
				try {
					const m = await apiFetch<{ tags?: string[] }>(`/api/diagrams/${ref.diagram_id}`);
					if (m.tags) m.tags.forEach((t) => diagramTags.add(t));
				} catch { /* skip inaccessible diagrams */ }
			}
			// Exclude own tags from inherited
			const ownTags = new Set(entity?.tags ?? []);
			inheritedTags = [...diagramTags].filter((t) => !ownTags.has(t)).sort();
		} catch {
			usedInModels = [];
			inheritedTags = [];
		}
		diagramsLoading = false;
	}

	async function loadAllTags() {
		try {
			allTags = await apiFetch<string[]>('/api/elements/tags/all');
		} catch {
			allTags = [];
		}
	}

	async function loadBookmarkStatus(id: string) {
		try {
			const bookmarks = await apiFetch<Bookmark[]>('/api/bookmarks');
			isBookmarked = bookmarks.some((b) => b.element_id === id);
		} catch {
			isBookmarked = false;
		}
	}

	async function toggleBookmark() {
		if (!entity || bookmarkLoading) return;
		bookmarkLoading = true;
		try {
			if (isBookmarked) {
				await apiFetch(`/api/elements/${entity.id}/bookmark`, { method: 'DELETE' });
				isBookmarked = false;
			} else {
				await apiFetch(`/api/elements/${entity.id}/bookmark`, { method: 'POST' });
				isBookmarked = true;
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update bookmark';
		}
		bookmarkLoading = false;
	}

	async function enterDetailsEdit() {
		if (!entity) return;
		editName = entity.name;
		editDescription = entity.description ?? '';
		editElementType = entity.element_type;
		editTags = [...(entity.tags ?? [])];
		const srcAttrs = (entity.data as Record<string, unknown>)?.attributes;
		editAttributes = Array.isArray(srcAttrs)
			? srcAttrs.map((a: any) => ({ name: a.name ?? '', type: a.type ?? '', scope: a.scope ?? 'Public', notes: a.notes ?? '', lower_bound: a.lower_bound ?? '', upper_bound: a.upper_bound ?? '' }))
			: [];
		editPackageId = (entity as any).package_id ?? null;
		editDetailDiagramId = entity.detail_diagram_id ?? null;
		editDetailDiagramName = detailDiagramName;
		// ADR-228: seed metadata edit state from `entity.metadata`. Each
		// blank string corresponds to "field unset" so the existing
		// {#if meta?.field} display behaviour is preserved on save.
		const md = (entity.metadata ?? {}) as Record<string, unknown>;
		editStatus = (md.status as string | undefined) ?? '';
		editStereotype = (md.stereotype as string | undefined) ?? '';
		editMetaVersion = (md.version as string | undefined) ?? '';
		editScope = (md.scope as string | undefined) ?? '';
		editAbstract = (md.abstract as string | undefined) ?? '';
		editPersistence = (md.persistence as string | undefined) ?? '';
		editAuthor = (md.author as string | undefined) ?? '';
		editComplexity = (md.complexity as string | undefined) ?? '';
		editPhase = (md.phase as string | undefined) ?? '';
		editCreatedDate = (md.created_date as string | undefined) ?? '';
		editModifiedDate = (md.modified_date as string | undefined) ?? '';
		editGenType = (md.gen_type as string | undefined) ?? '';
		const tvs = Array.isArray(md.tagged_values) ? md.tagged_values : [];
		editTaggedValues = (tvs as Array<{ property?: string; value?: string | null }>)
			.map((tv) => ({
				property: tv.property ?? '',
				...splitTaggedValue(tv.value),
			}));
		// Load packages scoped to the element's set so the picker stays
		// constrained to a consistent group (ADR-184).
		try {
			if (entity.set_id) {
				const resp = await apiFetch<{ items: PackageOption[] }>(
					`/api/packages?set_id=${encodeURIComponent(entity.set_id)}&page_size=100`
				);
				setPackages = resp.items ?? [];
			} else {
				setPackages = [];
			}
		} catch {
			setPackages = [];
		}
		editingDetails = true;
		detailsDirty = false;
	}

	async function saveEntityMetadata() {
		if (!entity) return;
		savingDetails = true;
		error = null;
		try {
			const sanitizedName = DOMPurify.sanitize(editName).trim();
			const sanitizedDesc = DOMPurify.sanitize(editDescription).trim();
			if (!sanitizedName) {
				error = 'Name is required';
				savingDetails = false;
				return;
			}
			const updatedData = { ...(entity.data ?? {}) } as Record<string, unknown>;
			if (editAttributes.length > 0) {
				updatedData.attributes = editAttributes.filter(a => a.name.trim());
			} else {
				delete updatedData.attributes;
			}
			const putBody: Record<string, unknown> = {
				name: sanitizedName,
				// v6.39.0 (ADR-228): `element_type` is intentionally omitted —
				// `ElementUpdate` doesn't accept it (element type is immutable
				// after creation per ADR-178). Previously included as dead bytes.
				description: sanitizedDesc,
				data: updatedData,
				change_summary: 'Updated element details',
			};
			// ADR-184 tri-state: include the key (set / null) when the
			// user picked a value or explicitly cleared via the "None"
			// option. ``editPackageId === undefined`` would mean "leave
			// untouched" but we initialise it to either the current
			// value or null on entry, so always include it here.
			putBody.package_id = editPackageId ?? null;
			// ADR-221 tri-state — same convention as package_id: always
			// include the key (set / null) since we seed it on edit entry.
			putBody.detail_diagram_id = editDetailDiagramId ?? null;
			// ADR-228: assemble the updated metadata from edit state and
			// include it in the PUT body. Preserves any keys we didn't
			// surface in the editor; deletes scalars the user blanked
			// out; reassembles tagged-value `value` from the split
			// editor form, dropping blank-property rows.
			const baseMeta = (entity.metadata ?? {}) as Record<string, unknown>;
			const updatedMeta: Record<string, unknown> = { ...baseMeta };
			const setOrDelete = (k: string, v: string) => {
				if (v.trim()) updatedMeta[k] = v;
				else delete updatedMeta[k];
			};
			setOrDelete('status', editStatus);
			setOrDelete('stereotype', editStereotype);
			setOrDelete('version', editMetaVersion);
			setOrDelete('scope', editScope);
			setOrDelete('abstract', editAbstract);
			setOrDelete('persistence', editPersistence);
			setOrDelete('author', editAuthor);
			setOrDelete('complexity', editComplexity);
			setOrDelete('phase', editPhase);
			setOrDelete('created_date', editCreatedDate);
			setOrDelete('modified_date', editModifiedDate);
			setOrDelete('gen_type', editGenType);
			const rebuiltTV = editTaggedValues
				.filter((r) => r.property.trim())
				.map((r) => ({
					property: r.property,
					value: joinTaggedValue(r.value, r.notes) || null,
				}));
			if (rebuiltTV.length) updatedMeta.tagged_values = rebuiltTV;
			else delete updatedMeta.tagged_values;
			putBody.metadata = updatedMeta;
			await apiFetch(`/api/elements/${entity.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(entity.current_version) },
				body: JSON.stringify(putBody),
			});

			// Sync tags
			const oldTags = entity.tags ?? [];
			const toAdd = editTags.filter((t) => !oldTags.includes(t));
			const toRemove = oldTags.filter((t) => !editTags.includes(t));
			for (const tag of toAdd) {
				await apiFetch(`/api/elements/${entity.id}/tags`, {
					method: 'POST',
					body: JSON.stringify({ tag }),
				});
			}
			for (const tag of toRemove) {
				await apiFetch(`/api/elements/${entity.id}/tags/${encodeURIComponent(tag)}`, {
					method: 'DELETE',
				});
			}

			editingDetails = false;
			detailsDirty = false;
			await loadEntity(entity.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update element';
		}
		savingDetails = false;
	}

	function discardDetailsChanges() {
		editingDetails = false;
		detailsDirty = false;
	}

	async function handleClone() {
		if (!entity) return;
		try {
			// Issue #173 item 1: explicitly pass set_id so the clone lands in
			// the source's set, not the default. The backend's create_element
			// defaults set_id when absent, which is what produced the bug.
			const created = await apiFetch<Element>('/api/elements', {
				method: 'POST',
				body: JSON.stringify({
					element_type: entity.element_type,
					name: `${entity.name} (Copy)`,
					description: entity.description ?? '',
					data: entity.data ?? {},
					set_id: entity.set_id,
				}),
			});
			await goto(`/elements/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to clone element';
		}
	}

	async function handleDelete() {
		if (!entity) return;
		try {
			await apiFetch(`/api/elements/${entity.id}`, {
				method: 'DELETE',
				headers: { 'If-Match': String(entity.current_version) },
			});
			showDeleteDialog = false;
			await goto('/elements');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete element';
		}
	}
</script>

<svelte:head>
	<title>{entity?.name ?? 'Element Detail'} — Iris</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex flex-nowrap items-baseline gap-1 overflow-x-auto whitespace-nowrap">
		<li><a href="/elements" style="color: var(--color-primary)">Elements</a></li>
		<li class="flex items-baseline gap-1">
			<span aria-hidden="true">/</span>
			<span aria-current="page">{entity?.name ?? page.params.id}</span>
		</li>
	</ol>
</nav>

{#if loading}
	<p style="color: var(--color-muted)">Loading element...</p>
{:else if error}
	<div role="alert" class="rounded border p-4" style="border-color: var(--color-danger); color: var(--color-danger)">
		{error}
	</div>
{:else if entity}
	<div class="flex gap-4 items-start">
	{#if entity.set_id}
		<HierarchySidebar setId={entity.set_id} currentId={entity.id} bind:open={sidebarOpen} />
	{/if}
	<div class="min-w-0 flex-1">
	<div class="flex flex-wrap items-center justify-between gap-2">
		<div>
			<div class="flex flex-wrap items-center gap-3">
				<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{entity.name}</h1>
				{#if entity.set_name}
					<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-muted); border: 1px solid var(--color-border)">{entity.set_name}</span>
				{/if}
			</div>
			<p class="mt-1 text-sm flex items-center gap-2 flex-wrap" style="color: var(--color-muted)">
				<span>{entity.element_type}</span>
				{#if entity.notation && entity.notation !== 'simple'}
					<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)">{entity.notation}</span>
				{/if}
				{#if entity.stereotype}
					<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)" title="Stereotype">«{entity.stereotype}»</span>
				{/if}
			</p>
		</div>
		<div class="flex gap-2">
			{#if entity.element_type.startsWith('scenia_')}
				<button
					onclick={() => openScenia(entity.set_id, entity.id)}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-success, #22c55e); color: var(--color-success, #22c55e); background: transparent; cursor: pointer"
				>
					View in Scenia
				</button>
			{/if}
			<button
				onclick={toggleBookmark}
				disabled={bookmarkLoading}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid {isBookmarked ? 'var(--color-primary)' : 'var(--color-border)'}; color: {isBookmarked ? 'var(--color-primary)' : 'var(--color-fg)'}; background: {isBookmarked ? 'var(--color-surface, transparent)' : 'transparent'}"
			>
				{isBookmarked ? 'Bookmarked' : 'Bookmark'}
			</button>
			<button
				onclick={handleClone}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Clone
			</button>
			<button
				onclick={() => (showSaveTemplateDialog = true)}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Save as template
			</button>
			{#if canWrite(entity?.collection_id)}
			<button
				onclick={() => (showDeleteDialog = true)}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-danger)"
			>
				Delete
			</button>
			{/if}
		</div>
	</div>

	<!-- Tab navigation. ADR-208 (v6.16.0): Relationships first; the
		 old "Used In Diagrams" tab is folded into Relationships as a
		 section, alongside the new Package membership section. -->
	<div class="mt-6 flex items-center gap-1 border-b" style="border-color: var(--color-border)">
		{#if entity.set_id}
			<button onclick={() => (sidebarOpen = !sidebarOpen)} aria-label="Toggle hierarchy sidebar" aria-pressed={sidebarOpen} class="rounded p-1" title="Show the set hierarchy">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="20" height="20"
					style="color: {sidebarOpen ? 'var(--color-primary)' : 'var(--color-muted)'}">
					<path d="M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z"/>
				</svg>
			</button>
		{/if}
		<div class="flex gap-1 overflow-x-auto" role="tablist" aria-label="Element sections">
		<button
			role="tab"
			aria-selected={activeTab === 'relationships'}
			onclick={() => { activeTab = 'relationships'; userSelectedTab = true; }}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'relationships' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'relationships' ? 'var(--color-primary)' : 'transparent'}"
		>
			Relationships
			{#if relationships.length > 0 || usedInModels.length > 0 || packageMemberships.length > 0}
				{@const _relTotal = relationships.length + usedInModels.length + packageMemberships.length}
				<span
					style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: var(--color-primary); margin-left: 4px; vertical-align: middle;"
					aria-label="{_relTotal} relationship{_relTotal === 1 ? '' : 's'}"
				></span>
			{/if}
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'details'}
			onclick={() => { activeTab = 'details'; userSelectedTab = true; }}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'details' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'details' ? 'var(--color-primary)' : 'transparent'}"
		>
			Details
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'versions'}
			onclick={() => { activeTab = 'versions'; userSelectedTab = true; }}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'versions' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'versions' ? 'var(--color-primary)' : 'transparent'}"
		>
			Version History
		</button>
		</div>
	</div>

	<!-- Tab panels -->
	<div class="mt-4" role="tabpanel">
		{#if activeTab === 'details'}
			{@const modifiedByUsername = versions.length > 0 ? (versions[0].created_by_username ?? versions[0].created_by) : (entity.created_by_username ?? entity.created_by)}
			<!-- Inline edit toolbar -->
			<div class="mb-3 flex items-center gap-2">
				{#if editingDetails}
					<button
						onclick={saveEntityMetadata}
						disabled={!detailsDirty || savingDetails}
						class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
						style="background-color: var(--color-success, #16a34a)"
					>
						{savingDetails ? 'Saving...' : 'Save'}
					</button>
					<button
						onclick={discardDetailsChanges}
						class="rounded px-3 py-1.5 text-sm"
						style="border: 1px solid var(--color-border); color: var(--color-fg)"
					>
						Discard
					</button>
					{#if detailsDirty}
						<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
					{/if}
				{:else if canWrite(entity?.collection_id)}
					<button
						onclick={enterDetailsEdit}
						class="rounded px-3 py-1.5 text-sm text-white"
						style="background-color: var(--color-primary)"
					>
						Edit Details
					</button>
				{/if}
			</div>

			<Accordion.Root type="single" value="summary">
				<!-- Overview group (open by default) -->
				<Accordion.Item value="summary" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Overview
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4 overflow-x-auto">
						<dl class="detail-grid grid gap-3">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">Name</dt>
							<dd>
								{#if editingDetails}
									<input
										type="text"
										bind:value={editName}
										class="w-full rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									/>
								{:else}
									<span style="color: var(--color-fg)">{entity.name}</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
							<dd>
								{#if editingDetails}
									<textarea
										bind:value={editDescription}
										rows="3"
										class="w-full rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									></textarea>
								{:else}
									<span style="color: var(--color-fg)">{entity.description ?? 'No description'}</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Type</dt>
							<dd>
								{#if editingDetails}
									{#if entity.notation === 'c4'}
										<C4TypePicker
											compact
											value={editElementType}
											onchange={(t) => { editElementType = t; }}
										/>
									{:else}
										<select
											bind:value={editElementType}
											class="w-full rounded border px-2 py-1 text-sm"
											style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
										>
											{#each entityTypeOptions as t}
												<option value={t.key}>{t.icon} {t.label}</option>
											{/each}
										</select>
									{/if}
								{:else}
									{#if entity.notation === 'c4'}
										<span class="inline-flex items-center gap-1" style="color: var(--color-fg)">
											<C4TypeGlyph type={entity.element_type} size={14} />
											{C4_ENTITY_TYPES.find(t => t.key === entity.element_type)?.label ?? entity.element_type}
										</span>
									{:else}
										<span style="color: var(--color-fg)">{entity.element_type}</span>
									{/if}
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Notation</dt>
							<dd style="color: var(--color-fg)">{entity.notation ?? 'simple'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Set</dt>
							<dd>
								<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-fg)">
									{entity.set_name ?? 'Default'}
								</span>
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Package</dt>
							<dd>
								{#if editingDetails}
									<select
										bind:value={editPackageId}
										class="rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
										aria-label="Package membership"
									>
										<option value={null}>None</option>
										{#each setPackages as pkg}
											<option value={pkg.id}>{pkg.name}</option>
										{/each}
									</select>
								{:else if (entity as any).package_id}
									<a
										href={`/packages/${(entity as any).package_id}`}
										class="rounded px-2 py-0.5 text-sm underline"
										style="background: var(--color-surface); color: var(--color-fg)"
									>
										{(entity as any).package_name ?? (entity as any).package_id}
									</a>
								{:else}
									<span style="color: var(--color-muted)">None</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Detail view</dt>
							<dd>
								{#if editingDetails}
									{#if editDetailDiagramId}
										<div class="flex items-center gap-1.5">
											<span class="truncate text-sm" style="color: var(--color-fg)" title={editDetailDiagramName ?? editDetailDiagramId}>
												{editDetailDiagramName ?? editDetailDiagramId}
											</span>
											<button
												type="button"
												onclick={() => (showDetailDiagramPicker = true)}
												class="shrink-0 rounded border px-2 py-0.5 text-xs"
												style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
											>Change</button>
											<button
												type="button"
												onclick={() => { editDetailDiagramId = null; editDetailDiagramName = null; }}
												title="Clear detail view"
												class="shrink-0 px-1 text-sm leading-none"
												style="color: var(--color-muted); background: none; border: none; cursor: pointer"
											>&times;</button>
										</div>
									{:else}
										<button
											type="button"
											onclick={() => (showDetailDiagramPicker = true)}
											class="rounded border px-2 py-1 text-xs"
											style="border-color: var(--color-border); border-style: dashed; background: none; color: var(--color-primary); cursor: pointer"
										>Set detail view</button>
									{/if}
								{:else if entity.detail_diagram_id}
									<a
										href={`/views/${entity.detail_diagram_id}`}
										class="rounded px-2 py-0.5 text-sm underline"
										style="background: var(--color-surface); color: var(--color-fg)"
										title="Drill into the diagram that elaborates this element"
									>
										{detailDiagramName ?? entity.detail_diagram_id}
									</a>
								{:else}
									<span style="color: var(--color-muted)">None</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Tags</dt>
							<dd>
								{#if editingDetails}
									<TagInput
										tags={editTags}
										onaddtag={(tag) => { editTags = [...editTags, tag]; }}
										onremovetag={(tag) => { editTags = editTags.filter(t => t !== tag); }}
										{inheritedTags}
										suggestions={allTags}
									/>
								{:else if (entity.tags ?? []).length > 0 || inheritedTags.length > 0}
									<div class="flex flex-wrap gap-1">
										{#each (entity.tags ?? []) as tag}
											<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
										{/each}
										{#each inheritedTags as tag}
											<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-muted); color: white; opacity: 0.5" title="Inherited tag">{tag}</span>
										{/each}
									</div>
								{:else}
									<span style="color: var(--color-muted)">None</span>
								{/if}
							</dd>
						</dl>
					</Accordion.Content>
				</Accordion.Item>

				<!-- Attributes group -->
				{@const elemData = entity.data as Record<string, unknown> | null | undefined}
				{@const elemAttrs = Array.isArray(elemData?.attributes) ? elemData.attributes as {name: string; type: string; scope?: string; notes?: string; default?: string; lower_bound?: string; upper_bound?: string; stereotype?: string}[] : []}
				{#if elemAttrs.length > 0 || editingDetails}
					<Accordion.Item value="attributes" class="border-b" style="border-color: var(--color-border)">
						<Accordion.Header>
							<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
								Attributes ({editingDetails ? editAttributes.length : elemAttrs.length})
								<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
							</Accordion.Trigger>
						</Accordion.Header>
						<Accordion.Content class="pb-4 overflow-x-auto">
							{#if editingDetails}
								<table class="w-full text-sm" style="color: var(--color-fg)">
									<thead>
										<tr style="border-bottom: 1px solid var(--color-border)">
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Scope</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Name</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Type</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Lower</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Upper</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Notes</th>
											<th class="py-1 text-left font-medium" style="color: var(--color-muted)"></th>
										</tr>
									</thead>
									<tbody>
										{#each editAttributes as attr, i}
											<tr style="border-bottom: 1px solid var(--color-border)">
												<td class="py-1 pr-2">
													<select bind:value={attr.scope} class="w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
														<option value="Public">+ Public</option>
														<option value="Private">- Private</option>
														<option value="Protected"># Protected</option>
														<option value="Package">~ Package</option>
													</select>
												</td>
												<td class="py-1 pr-2"><input type="text" bind:value={attr.name} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="name" /></td>
												<td class="py-1 pr-2"><input type="text" bind:value={attr.type} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="type" /></td>
												<td class="py-1 pr-2" style="width:3rem"><input type="text" bind:value={attr.lower_bound} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="0" /></td>
												<td class="py-1 pr-2" style="width:3rem"><input type="text" bind:value={attr.upper_bound} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="*" /></td>
												<td class="py-1 pr-2"><input type="text" bind:value={attr.notes} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="notes" /></td>
												<td class="py-1">
													<button onclick={() => { editAttributes = editAttributes.filter((_, idx) => idx !== i); }} class="text-xs px-1 rounded" style="color: var(--color-danger)" title="Remove attribute">✕</button>
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
								<button
									onclick={() => { editAttributes = [...editAttributes, {name: '', type: '', scope: 'Public', notes: '', lower_bound: '', upper_bound: ''}]; }}
									class="mt-2 rounded px-2 py-1 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-fg)"
								>
									+ Add Attribute
								</button>
							{:else}
								<table class="w-full text-sm" style="color: var(--color-fg)">
									<thead>
										<tr style="border-bottom: 1px solid var(--color-border)">
											<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Vis</th>
											<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Name</th>
											<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Type</th>
											<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Multiplicity</th>
											<th class="py-1 text-left font-medium" style="color: var(--color-muted)">Notes</th>
										</tr>
									</thead>
									<tbody>
										{#each elemAttrs as attr}
											<tr style="border-bottom: 1px solid var(--color-border)">
												<td class="py-1 pr-4 font-mono">{attr.scope === 'Private' ? '-' : attr.scope === 'Protected' ? '#' : attr.scope === 'Package' ? '~' : '+'}</td>
												<td class="py-1 pr-4 font-medium">{attr.name}</td>
												<td class="py-1 pr-4">{attr.type || '—'}</td>
												<td class="py-1 pr-4">{attr.lower_bound && attr.upper_bound ? `${attr.lower_bound}..${attr.upper_bound}` : '—'}</td>
												<td class="py-1 text-xs" style="color: var(--color-muted)">{attr.notes || ''}</td>
											</tr>
										{/each}
									</tbody>
								</table>
							{/if}
						</Accordion.Content>
					</Accordion.Item>
				{/if}

				<!-- Details group (collapsed) -->
				<Accordion.Item value="element-details" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Details
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4 overflow-x-auto">
						<dl class="detail-grid grid gap-3">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">ID</dt>
							<dd class="text-sm" style="color: var(--color-fg)">{entity.id}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Version</dt>
							<dd style="color: var(--color-fg)">{entity.current_version ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
							<dd style="color: var(--color-fg)">{entity.created_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created By</dt>
							<dd style="color: var(--color-fg)">{entity.created_by_username ?? entity.created_by}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified</dt>
							<dd style="color: var(--color-fg)">{entity.updated_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified By</dt>
							<dd style="color: var(--color-fg)">{modifiedByUsername}</dd>

							{#if editingDetails || (entity.metadata as Record<string, unknown> | null | undefined)?.status}
								<dt class="text-sm font-medium" style="color: var(--color-muted)">Status</dt>
								<dd style="color: var(--color-fg)">
									{#if editingDetails}
										<!-- v6.39.2: the v6.39.1 `<input list>` + `<datalist>`
											 approach was filtering the dropdown to entries
											 matching the current input text. With the cell
											 already showing "Approved", Chrome only surfaced
											 the matching entry — looking to the user like an
											 empty dropdown carrying just the existing value.
											 Pair a real <select> for quick-pick with a text
											 input for custom values; both bind the same
											 `editStatus` state, so changes in either
											 propagate. -->
										<div class="flex gap-2">
											<select
												bind:value={editStatus}
												aria-label="Status quick-pick"
												class="rounded border px-2 py-1 text-sm"
												style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
											>
												<option value="">—</option>
												<option value="Approved">Approved</option>
												<option value="Proposed">Proposed</option>
												<option value="Implemented">Implemented</option>
												<option value="Validated">Validated</option>
												<option value="Mandatory">Mandatory</option>
												{#if editStatus && !['', 'Approved', 'Proposed', 'Implemented', 'Validated', 'Mandatory'].includes(editStatus)}
													<!-- Preserve any non-standard existing value so
														 the select reflects state correctly without
														 forcing the user to retype it. -->
													<option value={editStatus}>{editStatus}</option>
												{/if}
											</select>
											<input
												type="text"
												bind:value={editStatus}
												aria-label="Status"
												placeholder="or type a custom value"
												class="flex-1 rounded border px-2 py-1 text-sm"
												style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
											/>
										</div>
									{:else}
										{(entity.metadata as Record<string, unknown>).status}
									{/if}
								</dd>
							{/if}
						</dl>
					</Accordion.Content>
				</Accordion.Item>

				<!-- Extended group (collapsed) -->
				<Accordion.Item value="extended" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Extended
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4 overflow-x-auto">
						{@const meta = entity.metadata as Record<string, unknown> | null | undefined}
						{@const hasMeta = !!(meta && (meta.stereotype || meta.version || meta.scope || meta.abstract || meta.persistence || meta.author || meta.complexity || meta.phase || meta.created_date || meta.modified_date || meta.gen_type || (Array.isArray(meta.tagged_values) && (meta.tagged_values as unknown[]).length > 0)))}
						{#if hasMeta || editingDetails}
							<!-- ADR-228: each row shows in edit mode regardless of
								 whether the underlying metadata key is set, so the
								 user can add or clear it. Tailwind classes mirror
								 the Attributes editor at lines 854-907. -->
							{#snippet scalarRow(label: string, displayValue: string, ariaLabel: string, get: () => string, set: (v: string) => void)}
								{#if editingDetails || displayValue}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">{label}</dt>
									<dd style="color: var(--color-fg)">
										{#if editingDetails}
											<input
												type="text"
												value={get()}
												oninput={(e) => set((e.currentTarget as HTMLInputElement).value)}
												aria-label={ariaLabel}
												class="w-full rounded border px-2 py-1 text-sm"
												style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
											/>
										{:else}
											{displayValue}
										{/if}
									</dd>
								{/if}
							{/snippet}
							<dl class="detail-grid grid gap-3">
								{@render scalarRow('Stereotype', (meta?.stereotype as string) ?? '', 'Stereotype', () => editStereotype, (v) => (editStereotype = v))}
								{@render scalarRow('Metadata Version', (meta?.version as string) ?? '', 'Metadata Version', () => editMetaVersion, (v) => (editMetaVersion = v))}
								{@render scalarRow('Scope', (meta?.scope as string) ?? '', 'Scope', () => editScope, (v) => (editScope = v))}
								{@render scalarRow('Abstract', meta?.abstract ? 'Yes' : '', 'Abstract', () => editAbstract, (v) => (editAbstract = v))}
								{@render scalarRow('Persistence', (meta?.persistence as string) ?? '', 'Persistence', () => editPersistence, (v) => (editPersistence = v))}
								{@render scalarRow('Author', (meta?.author as string) ?? '', 'Author', () => editAuthor, (v) => (editAuthor = v))}
								{@render scalarRow('Complexity', (meta?.complexity as string) ?? '', 'Complexity', () => editComplexity, (v) => (editComplexity = v))}
								{@render scalarRow('Phase', (meta?.phase as string) ?? '', 'Phase', () => editPhase, (v) => (editPhase = v))}
								{@render scalarRow('EA Created Date', (meta?.created_date as string) ?? '', 'EA Created Date', () => editCreatedDate, (v) => (editCreatedDate = v))}
								{@render scalarRow('EA Modified Date', (meta?.modified_date as string) ?? '', 'EA Modified Date', () => editModifiedDate, (v) => (editModifiedDate = v))}
								{@render scalarRow('Gen Type', (meta?.gen_type as string) ?? '', 'Gen Type', () => editGenType, (v) => (editGenType = v))}

								{#if editingDetails}
									<!-- Edit mode: the full grid of tagged values
										 including a `+ Add Tagged Value` button so
										 users can grow / shrink the list. -->
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Tagged Values</dt>
									<dd>
										<table class="w-full text-sm" style="color: var(--color-fg)">
											<thead>
												<tr style="border-bottom: 1px solid var(--color-border)">
													<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Property</th>
													<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Value</th>
													<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Notes</th>
													<th class="py-1 w-6"></th>
												</tr>
											</thead>
											<tbody>
												{#each editTaggedValues as _row, i (i)}
													<tr style="border-bottom: 1px solid var(--color-border)">
														<td class="py-1 pr-2">
															<input
																type="text"
																bind:value={editTaggedValues[i].property}
																aria-label={`Tagged value ${i + 1} property`}
																class="w-full rounded border px-1 py-0.5 text-sm"
																style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
															/>
														</td>
														<td class="py-1 pr-2">
															<input
																type="text"
																bind:value={editTaggedValues[i].value}
																aria-label={`Tagged value ${i + 1} value`}
																class="w-full rounded border px-1 py-0.5 text-sm"
																style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
															/>
														</td>
														<td class="py-1 pr-2">
															<textarea
																bind:value={editTaggedValues[i].notes}
																rows="1"
																aria-label={`Tagged value ${i + 1} notes`}
																class="w-full rounded border px-1 py-0.5 text-sm"
																style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
															></textarea>
														</td>
														<td class="py-1">
															<button
																type="button"
																aria-label={`Remove tagged value ${i + 1}`}
																onclick={() => { editTaggedValues = editTaggedValues.filter((_, j) => j !== i); }}
																class="rounded px-2 py-0.5 text-sm"
																style="color: var(--color-muted)"
															>✕</button>
														</td>
													</tr>
												{/each}
												<tr>
													<td colspan="4" class="py-2">
														<button
															type="button"
															onclick={() => { editTaggedValues = [...editTaggedValues, { property: '', value: '', notes: '' }]; }}
															class="rounded px-2 py-1 text-sm"
															style="border: 1px solid var(--color-border); color: var(--color-fg)"
														>+ Add Tagged Value</button>
													</td>
												</tr>
											</tbody>
										</table>
									</dd>
								{:else if Array.isArray(meta?.tagged_values) && (meta.tagged_values as unknown[]).length > 0}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Tagged Values</dt>
									<dd>
										<table class="w-full text-sm" style="color: var(--color-fg)">
											<thead>
												<tr style="border-bottom: 1px solid var(--color-border)">
													<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Property</th>
													<th class="py-1 text-left font-medium" style="color: var(--color-muted)">Value</th>
												</tr>
											</thead>
											<tbody>
												{#each meta.tagged_values as tv}
													{@const tvObj = tv as {property?: string; value?: string}}
													<tr style="border-bottom: 1px solid var(--color-border)">
														<td class="py-1 pr-4">{tvObj.property ?? ''}</td>
														<td class="py-1">{tvObj.value ?? ''}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									</dd>
								{/if}
							</dl>
						{:else}
							<p class="text-sm" style="color: var(--color-muted)">No extended metadata available.</p>
						{/if}
					</Accordion.Content>
				</Accordion.Item>
			</Accordion.Root>
			<!-- ADR-209 (v6.17.0 / v6.17.3): attached images for this
				 element. Always-editable (matches collections/sets) — image
				 attachments are committed atomically by the backend, so they
				 shouldn't gate the form's save/discard flow. -->
			<div class="mt-4">
				<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Images</h3>
				<EntityImagesEditor
					entityType="element"
					entityId={entity.id}
					editing={true}
				/>
			</div>
		{:else if activeTab === 'relationships'}
			<!-- ADR-208 (v6.16.0): the Relationships tab now hosts three
				 sections — Package membership, Used in Views, and the
				 explicit Relationships table. Empty sections are hidden. -->

			{#if entity?.parent_element_id}
				<section class="mb-6">
					<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Parent element</h3>
					<a
						href="/elements/{entity.parent_element_id}"
						class="flex items-center gap-3 rounded border block p-3"
						style="border-color: var(--color-border); color: var(--color-primary)"
					>
						<span class="font-medium">{entity.parent_element_name ?? entity.parent_element_id}</span>
					</a>
				</section>
			{/if}

			{#if childElements.length > 0}
				<section class="mb-6">
					<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Child elements ({childElements.length})</h3>
					<ul class="flex flex-col gap-2">
						{#each childElements as child (child.id)}
							<li>
								<a
									href="/elements/{child.id}"
									class="flex items-center gap-3 rounded border block p-3"
									style="border-color: var(--color-border); color: var(--color-primary)"
								>
									<span class="font-medium">{child.name}</span>
									<span class="text-xs" style="color: var(--color-muted)">{child.element_type}</span>
								</a>
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			{#if packageMemberships.length > 0}
				<section class="mb-6">
					<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Package membership</h3>
					<ul class="flex flex-col gap-2">
						{#each packageMemberships as pkg (pkg.id)}
							<li>
								<a
									href="/packages/{pkg.id}"
									class="flex items-center gap-3 rounded border block p-3"
									style="border-color: var(--color-border); color: var(--color-primary)"
								>
									<span class="font-medium">{pkg.name}</span>
								</a>
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			{#if diagramsLoading}
				<p style="color: var(--color-muted)">Loading views…</p>
			{:else if usedInModels.length > 0}
				<section class="mb-6">
					<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Used in Views</h3>
					<ul class="flex flex-col gap-2">
						{#each usedInModels as model}
							<li>
								<a
									href="/views/{model.diagram_id}"
									class="flex items-center gap-3 rounded border block p-3"
									style="border-color: var(--color-border); color: var(--color-primary)"
								>
									<span class="font-medium">{model.name}</span>
									<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
										{model.diagram_type}
									</span>
								</a>
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<section>
				<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Relationships</h3>
				{#if relationshipsLoading}
					<p style="color: var(--color-muted)">Loading relationships…</p>
				{:else if relationships.length === 0}
					<p style="color: var(--color-muted)">No relationships yet. Relationships are created automatically when elements are connected by edges in a view canvas.</p>
				{:else}
					<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="py-2 text-left" style="color: var(--color-muted)">Type</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Source</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Target</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Label</th>
							</tr>
						</thead>
						<tbody>
							{#each relationships as rel}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="py-2" style="color: var(--color-fg)">{rel.relationship_type}</td>
									<td class="py-2">
										<a href="/elements/{rel.source_element_id}" style="color: var(--color-primary)">
											{rel.source_element_id === entity.id ? entity.name : (rel.source_element_name || rel.source_element_id)}
										</a>
									</td>
									<td class="py-2">
										<a href="/elements/{rel.target_element_id}" style="color: var(--color-primary)">
											{rel.target_element_id === entity.id ? entity.name : (rel.target_element_name || rel.target_element_id)}
										</a>
									</td>
									<td class="py-2" style="color: var(--color-fg)">{rel.label ?? '—'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
					</div>
				{/if}
			</section>
		{:else if activeTab === 'versions'}
			<VersionHistory {versions} loading={versionsLoading} currentVersion={entity?.current_version} onrollback={handleElementRollback} />
		{/if}
	</div>

	<!-- Comments section -->
	<section class="mt-8">
		<CommentsPanel targetType="element" targetId={entity.id} collectionId={entity.collection_id} />
	</section>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Element"
		message="Are you sure you want to delete '{entity.name}'? This action cannot be undone."
		confirmLabel="Delete"
		onconfirm={handleDelete}
		oncancel={() => (showDeleteDialog = false)}
	/>

	<CreateTemplateDialog
		open={showSaveTemplateDialog}
		sourceElementId={entity.id}
		sourceElementName={entity.name}
		setId={entity.set_id ?? null}
		oncancel={() => (showSaveTemplateDialog = false)}
		oncreated={(templateId) => {
			showSaveTemplateDialog = false;
			goto(`/element-templates/${templateId}`);
		}}
	/>

	<!-- ADR-221: pick the element's detail diagram (cross-set allowed). -->
	<DiagramPicker
		open={showDetailDiagramPicker}
		title="Set detail view"
		onselect={(d: Diagram) => {
			editDetailDiagramId = d.id;
			editDetailDiagramName = d.name;
			showDetailDiagramPicker = false;
		}}
		oncancel={() => (showDetailDiagramPicker = false)}
	/>
	</div>
	</div>
{/if}
