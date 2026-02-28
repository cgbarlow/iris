<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Model, ModelVersion, Bookmark } from '$lib/types/api';
	import BrowseCanvas from '$lib/canvas/BrowseCanvas.svelte';
	import ModelCanvas from '$lib/canvas/ModelCanvas.svelte';
	import FullViewCanvas from '$lib/canvas/FullViewCanvas.svelte';
	import SequenceDiagram from '$lib/canvas/sequence/SequenceDiagram.svelte';
	import SequenceToolbar from '$lib/canvas/sequence/SequenceToolbar.svelte';
	import ParticipantDialog from '$lib/canvas/sequence/ParticipantDialog.svelte';
	import MessageDialog from '$lib/canvas/sequence/MessageDialog.svelte';
	import { createSequenceViewport } from '$lib/canvas/sequence/useSequenceViewport.svelte';
	import type { SequenceDiagramData, Participant, SequenceMessage } from '$lib/canvas/sequence/types';
	import { SEQUENCE_LAYOUT as L } from '$lib/canvas/sequence/types';
	import FocusView from '$lib/components/FocusView.svelte';
	import ModelDialog from '$lib/components/ModelDialog.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import EntityDialog from '$lib/canvas/controls/EntityDialog.svelte';
	import RelationshipDialog from '$lib/canvas/controls/RelationshipDialog.svelte';
	import EntityDetailPanel from '$lib/canvas/controls/EntityDetailPanel.svelte';
	import CommentsPanel from '$lib/components/CommentsPanel.svelte';
	import EntityPicker from '$lib/components/EntityPicker.svelte';
	import { createCanvasHistory } from '$lib/canvas/useCanvasHistory.svelte';
	import type { Entity } from '$lib/types/api';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';
	import type { SimpleEntityType, SimpleRelationshipType } from '$lib/types/canvas';
	import {
		SIMPLE_ENTITY_TYPES,
		UML_ENTITY_TYPES,
		ARCHIMATE_ENTITY_TYPES,
		SIMPLE_RELATIONSHIP_TYPES,
		UML_RELATIONSHIP_TYPES,
		ARCHIMATE_RELATIONSHIP_TYPES,
	} from '$lib/types/canvas';
	import type { UmlEntityType, ArchimateEntityType } from '$lib/types/canvas';

	let model = $state<Model | null>(null);
	let versions = $state<ModelVersion[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'overview' | 'canvas' | 'versions'>('overview');
	let versionsLoading = $state(false);

	let showEditDialog = $state(false);
	let showDeleteDialog = $state(false);

	// Bookmark state
	let isBookmarked = $state(false);
	let bookmarkLoading = $state(false);

	// Canvas state
	let canvasNodes = $state<CanvasNode[]>([]);
	let canvasEdges = $state<CanvasEdge[]>([]);
	let editing = $state(false);
	let showAddEntity = $state(false);
	let canvasDirty = $state(false);
	let saving = $state(false);
	let selectedEdgeId = $state<string | null>(null);

	// Canvas undo/redo history
	const history = createCanvasHistory();

	// RelationshipDialog state
	let showRelationshipDialog = $state(false);
	let pendingConnection = $state<{ sourceId: string; targetId: string } | null>(null);

	// Browse mode entity detail panel state
	let selectedBrowseNode = $state<CanvasNode | null>(null);

	// Sequence diagram state
	let sequenceData = $state<SequenceDiagramData>({
		participants: [],
		messages: [],
		activations: [],
	});
	let selectedMessageId = $state<string | null>(null);
	let showAddParticipant = $state(false);
	let showAddMessage = $state(false);

	// Focus view state
	let focusMode = $state(false);

	// Entity picker state (link existing entity)
	let showEntityPicker = $state(false);

	// Version rollback — not available for models (only entities have rollback API).

	$effect(() => {
		const id = page.params.id;
		if (id) loadModel(id);
	});

	/** Determine which canvas component to render based on model type. */
	const canvasType = $derived.by(() => {
		if (!model) return 'simple';
		const mt = model.model_type;
		if (mt === 'sequence') return 'sequence';
		if (mt === 'uml') return 'uml';
		if (mt === 'archimate') return 'archimate';
		return 'simple'; // 'simple' and 'component' both use simple view
	});

	/** Get the Full View type for FullViewCanvas. */
	const fullViewType = $derived(canvasType === 'uml' ? 'uml' : 'archimate') as 'uml' | 'archimate';

	/** Source node name for RelationshipDialog display. */
	const pendingSourceName = $derived.by(() => {
		const pc = pendingConnection;
		if (!pc) return '';
		return canvasNodes.find((n) => n.id === pc.sourceId)?.data.label ?? 'Source';
	});

	/** Target node name for RelationshipDialog display. */
	const pendingTargetName = $derived.by(() => {
		const pc = pendingConnection;
		if (!pc) return '';
		return canvasNodes.find((n) => n.id === pc.targetId)?.data.label ?? 'Target';
	});

	async function loadModel(id: string) {
		loading = true;
		error = null;
		try {
			model = await apiFetch<Model>(`/api/models/${id}`);
			parseCanvasData();
			loadVersions(id);
			loadBookmarkStatus(id);
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Model not found'
				: 'Failed to load model';
		}
		loading = false;
	}

	function parseCanvasData() {
		if (!model?.data) {
			canvasNodes = [];
			canvasEdges = [];
			sequenceData = { participants: [], messages: [], activations: [] };
			return;
		}
		const data = model.data as Record<string, unknown>;

		if (model.model_type === 'sequence') {
			sequenceData = {
				participants: Array.isArray(data.participants) ? data.participants : [],
				messages: Array.isArray(data.messages) ? data.messages : [],
				activations: Array.isArray(data.activations) ? data.activations : [],
			} as SequenceDiagramData;
		} else {
			canvasNodes = (Array.isArray(data.nodes) ? data.nodes : []) as CanvasNode[];
			canvasEdges = (Array.isArray(data.edges) ? data.edges : []) as CanvasEdge[];
		}
		canvasDirty = false;
	}

	async function loadVersions(id: string) {
		versionsLoading = true;
		try {
			versions = await apiFetch<ModelVersion[]>(`/api/models/${id}/versions`);
		} catch {
			versions = [];
		}
		versionsLoading = false;
	}

	async function loadBookmarkStatus(id: string) {
		try {
			const bookmarks = await apiFetch<Bookmark[]>('/api/bookmarks');
			isBookmarked = bookmarks.some((b) => b.model_id === id);
		} catch {
			isBookmarked = false;
		}
	}

	async function toggleBookmark() {
		if (!model || bookmarkLoading) return;
		bookmarkLoading = true;
		try {
			if (isBookmarked) {
				await apiFetch(`/api/models/${model.id}/bookmark`, { method: 'DELETE' });
				isBookmarked = false;
			} else {
				await apiFetch(`/api/models/${model.id}/bookmark`, { method: 'POST' });
				isBookmarked = true;
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update bookmark';
		}
		bookmarkLoading = false;
	}

	async function handleEdit(name: string, _modelType: string, description: string) {
		if (!model) return;
		try {
			await apiFetch(`/api/models/${model.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(model.current_version) },
				body: JSON.stringify({
					name,
					description,
					data: model.data,
					change_summary: 'Updated model details',
				}),
			});
			showEditDialog = false;
			await loadModel(model.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update model';
		}
	}

	async function handleDelete() {
		if (!model) return;
		try {
			await apiFetch(`/api/models/${model.id}`, {
				method: 'DELETE',
				headers: { 'If-Match': String(model.current_version) },
			});
			showDeleteDialog = false;
			await goto('/models');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete model';
		}
	}

	// Canvas editing

	async function handleAddEntity(name: string, entityType: SimpleEntityType, description: string) {
		try {
			const created = await apiFetch<Entity>('/api/entities', {
				method: 'POST',
				body: JSON.stringify({
					entity_type: entityType,
					name,
					description,
					data: {},
				}),
			});
			const id = crypto.randomUUID();
			const offset = canvasNodes.length * 40;
			const newNode: CanvasNode = {
				id,
				type: entityType,
				position: { x: 100 + offset, y: 100 + offset },
				data: {
					label: name,
					entityType,
					description,
					entityId: created.id,
				},
			};
			history.pushState(canvasNodes, canvasEdges);
			canvasNodes = [...canvasNodes, newNode];
			canvasDirty = true;
			showAddEntity = false;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create entity';
		}
	}

	function handleDeleteNode(nodeId: string) {
		history.pushState(canvasNodes, canvasEdges);
		canvasNodes = canvasNodes.filter((n) => n.id !== nodeId);
		canvasEdges = canvasEdges.filter((e) => e.source !== nodeId && e.target !== nodeId);
		canvasDirty = true;
	}

	function handleDeleteEdge(edgeId: string) {
		canvasEdges = canvasEdges.filter((e) => e.id !== edgeId);
		selectedEdgeId = null;
		canvasDirty = true;
	}

	function handleConnectNodes(sourceId: string, targetId: string) {
		pendingConnection = { sourceId, targetId };
		showRelationshipDialog = true;
	}

	function handleRelationshipSave(type: SimpleRelationshipType, label: string) {
		if (!pendingConnection) return;
		const { sourceId, targetId } = pendingConnection;
		const newEdge: CanvasEdge = {
			id: `e-${sourceId}-${targetId}`,
			source: sourceId,
			target: targetId,
			type,
			data: { relationshipType: type, label: label || undefined },
		};
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = [...canvasEdges, newEdge];
		canvasDirty = true;
		showRelationshipDialog = false;
		pendingConnection = null;
	}

	function handleRelationshipCancel() {
		showRelationshipDialog = false;
		pendingConnection = null;
	}

	function handleBrowseNodeSelect(nodeId: string) {
		selectedBrowseNode = canvasNodes.find((n) => n.id === nodeId) ?? null;
	}

	async function saveCanvas() {
		if (!model) return;
		saving = true;
		error = null;
		try {
			await apiFetch(`/api/models/${model.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(model.current_version) },
				body: JSON.stringify({
					name: model.name,
					description: model.description ?? '',
					data: { nodes: canvasNodes, edges: canvasEdges },
					change_summary: 'Updated model diagram',
				}),
			});
			canvasDirty = false;
			history.clear();
			await loadModel(model.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to save canvas';
		}
		saving = false;
	}

	function handleLinkEntity(entity: Entity) {
		const id = crypto.randomUUID();
		const offset = canvasNodes.length * 40;
		const entityType = entity.entity_type as SimpleEntityType;
		const newNode: CanvasNode = {
			id,
			type: entityType,
			position: { x: 100 + offset, y: 100 + offset },
			data: {
				label: entity.name,
				entityType,
				description: entity.description ?? '',
				entityId: entity.id,
			},
		};
		history.pushState(canvasNodes, canvasEdges);
		canvasNodes = [...canvasNodes, newNode];
		canvasDirty = true;
		showEntityPicker = false;
	}

	function handleUndo() {
		const state = history.undo(canvasNodes, canvasEdges);
		if (state) {
			canvasNodes = state.nodes;
			canvasEdges = state.edges;
			canvasDirty = true;
		}
	}

	function handleRedo() {
		const state = history.redo(canvasNodes, canvasEdges);
		if (state) {
			canvasNodes = state.nodes;
			canvasEdges = state.edges;
			canvasDirty = true;
		}
	}

	function discardChanges() {
		parseCanvasData();
		history.clear();
		editing = false;
	}

	// Sequence diagram viewport
	const seqContentWidth = $derived(
		sequenceData.participants.length > 0
			? sequenceData.participants.length * (L.participantWidth + L.participantGap) - L.participantGap + L.padding * 2
			: 400,
	);
	const seqContentHeight = $derived(
		sequenceData.participants.length > 0
			? L.messageStartY + (sequenceData.messages.length + 1) * L.messageGap + L.participantHeight + L.padding
			: 300,
	);
	const seqViewport = $derived(createSequenceViewport(seqContentWidth, seqContentHeight));

	// Sequence editing

	function handleAddParticipant(name: string, type: Participant['type']) {
		const id = crypto.randomUUID();
		sequenceData = {
			...sequenceData,
			participants: [...sequenceData.participants, { id, name, type }],
		};
		canvasDirty = true;
		showAddParticipant = false;
	}

	function handleAddMessage(from: string, to: string, label: string, type: SequenceMessage['type']) {
		const id = crypto.randomUUID();
		const order = sequenceData.messages.length;
		sequenceData = {
			...sequenceData,
			messages: [...sequenceData.messages, { id, from, to, label, type, order }],
		};
		canvasDirty = true;
		showAddMessage = false;
	}

	function handleDeleteSelected() {
		if (selectedMessageId) {
			sequenceData = {
				...sequenceData,
				messages: sequenceData.messages
					.filter((m) => m.id !== selectedMessageId)
					.map((m, i) => ({ ...m, order: i })),
				activations: sequenceData.activations.filter(
					(a) => !sequenceData.messages.some(
						(m) => m.id === selectedMessageId &&
							(a.startOrder === m.order || a.endOrder === m.order),
					),
				),
			};
			selectedMessageId = null;
			canvasDirty = true;
		}
	}

	async function saveSequence() {
		if (!model) return;
		saving = true;
		error = null;
		try {
			await apiFetch(`/api/models/${model.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(model.current_version) },
				body: JSON.stringify({
					name: model.name,
					description: model.description ?? '',
					data: {
						participants: sequenceData.participants,
						messages: sequenceData.messages,
						activations: sequenceData.activations,
					},
					change_summary: 'Updated sequence diagram',
				}),
			});
			canvasDirty = false;
			await loadModel(model.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to save sequence';
		}
		saving = false;
	}
</script>

<svelte:head>
	<title>{model?.name ?? 'Model Detail'} — Iris</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/models" style="color: var(--color-primary)">Models</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">{model?.name ?? page.params.id}</li>
	</ol>
</nav>

{#if loading}
	<p style="color: var(--color-muted)">Loading model...</p>
{:else if error}
	<div role="alert" class="rounded border p-4" style="border-color: var(--color-danger); color: var(--color-danger)">
		{error}
	</div>
{:else if model}
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{model.name}</h1>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">{model.model_type}</p>
		</div>
		<div class="flex gap-2">
			<button
				onclick={toggleBookmark}
				disabled={bookmarkLoading}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid {isBookmarked ? 'var(--color-primary)' : 'var(--color-border)'}; color: {isBookmarked ? 'var(--color-primary)' : 'var(--color-fg)'}; background: {isBookmarked ? 'var(--color-surface, transparent)' : 'transparent'}"
			>
				{isBookmarked ? 'Bookmarked' : 'Bookmark'}
			</button>
			<button
				onclick={() => (showEditDialog = true)}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Edit
			</button>
			<button
				onclick={() => (showDeleteDialog = true)}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-danger)"
			>
				Delete
			</button>
		</div>
	</div>

	<!-- Tab navigation -->
	<div class="mt-6 flex gap-1 border-b" style="border-color: var(--color-border)" role="tablist" aria-label="Model sections">
		<button
			role="tab"
			aria-selected={activeTab === 'overview'}
			onclick={() => (activeTab = 'overview')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'overview' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'overview' ? 'var(--color-primary)' : 'transparent'}"
		>
			Overview
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'canvas'}
			onclick={() => (activeTab = 'canvas')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'canvas' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'canvas' ? 'var(--color-primary)' : 'transparent'}"
		>
			Canvas
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'versions'}
			onclick={() => (activeTab = 'versions')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'versions' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'versions' ? 'var(--color-primary)' : 'transparent'}"
		>
			Version History
		</button>
	</div>

	<div class="mt-4" role="tabpanel">
		{#if activeTab === 'overview'}
			<dl class="grid gap-4" style="grid-template-columns: auto 1fr">
				<dt class="text-sm font-medium" style="color: var(--color-muted)">ID</dt>
				<dd class="font-mono text-xs" style="color: var(--color-fg)">{model.id}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Type</dt>
				<dd style="color: var(--color-fg)">{model.model_type}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Version</dt>
				<dd style="color: var(--color-fg)">{model.current_version ?? 'N/A'}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
				<dd style="color: var(--color-fg)">{model.created_at ?? 'N/A'}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Created By</dt>
				<dd style="color: var(--color-fg)">{model.created_by_username ?? model.created_by}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified</dt>
				<dd style="color: var(--color-fg)">{model.updated_at ?? 'N/A'}</dd>

				{#if model.description}
					<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
					<dd style="color: var(--color-fg)">{model.description}</dd>
				{/if}
			</dl>
		{:else if activeTab === 'canvas'}
			{#if canvasType === 'sequence'}
				<!-- Sequence diagram toolbar -->
				<div class="mb-3 flex items-center gap-4">
					{#if editing}
						<!-- Create group -->
						<div class="flex items-center gap-2">
							<button
								onclick={() => (showAddParticipant = true)}
								class="rounded px-3 py-1.5 text-sm text-white"
								style="background-color: var(--color-primary)"
							>
								Add Participant
							</button>
							<button
								onclick={() => (showAddMessage = true)}
								disabled={sequenceData.participants.length < 2}
								class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
								style="background-color: var(--color-primary)"
							>
								Add Message
							</button>
						</div>
						<!-- Edit group -->
						<div class="flex items-center gap-2">
							<button
								onclick={handleDeleteSelected}
								disabled={!selectedMessageId}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-danger); color: var(--color-danger)"
							>
								Delete Selected
							</button>
						</div>
						<!-- Persist group -->
						<div class="flex items-center gap-2">
							<button
								onclick={saveSequence}
								disabled={saving || !canvasDirty}
								class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
								style="background-color: var(--color-success, #16a34a)"
							>
								{saving ? 'Saving...' : 'Save'}
							</button>
							<button
								onclick={discardChanges}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								Discard
							</button>
							{#if canvasDirty}
								<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
							{/if}
						</div>
					{:else}
						<button
							onclick={() => (editing = true)}
							class="rounded px-3 py-1.5 text-sm"
							style="background-color: var(--color-primary); color: white"
						>
							Edit Canvas
						</button>
					{/if}
					<!-- View group (always visible) -->
					<div class="ml-auto">
						<button
							onclick={() => (focusMode = true)}
							class="rounded px-3 py-1.5 text-sm"
							style="border: 1px solid var(--color-border); color: var(--color-fg)"
						>
							Focus
						</button>
					</div>
				</div>

				<!-- Sequence diagram rendering -->
				{#if sequenceData.participants.length === 0 && !editing}
					<div class="flex flex-col items-center justify-center gap-3 rounded border p-8" style="border-color: var(--color-border); min-height: 300px">
						<p style="color: var(--color-muted)">This sequence diagram has no participants yet.</p>
						<button
							onclick={() => (editing = true)}
							class="rounded px-4 py-2 text-sm text-white"
							style="background-color: var(--color-primary)"
						>
							Start Building
						</button>
					</div>
				{:else}
					{#if focusMode}
						<FocusView onexit={() => (focusMode = false)}>
							<div style="width: 100%; height: 100%; border: 1px solid var(--color-border); overflow: hidden; position: relative">
								<SequenceDiagram
									data={sequenceData}
									{selectedMessageId}
									onmessageselect={(id) => (selectedMessageId = id)}
									viewBox={seqViewport.viewBox}
									onwheel={seqViewport.handleWheel}
									onpointerdown={seqViewport.handlePointerDown}
									onpointermove={seqViewport.handlePointerMove}
									onpointerup={seqViewport.handlePointerUp}
								/>
								<SequenceToolbar
									onzoomin={seqViewport.zoomIn}
									onzoomout={seqViewport.zoomOut}
									onfitview={seqViewport.fitView}
								/>
							</div>
						</FocusView>
					{/if}
					<div style="height: 500px; border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden; position: relative">
						<SequenceDiagram
							data={sequenceData}
							{selectedMessageId}
							onmessageselect={(id) => (selectedMessageId = id)}
							viewBox={seqViewport.viewBox}
							onwheel={seqViewport.handleWheel}
							onpointerdown={seqViewport.handlePointerDown}
							onpointermove={seqViewport.handlePointerMove}
							onpointerup={seqViewport.handlePointerUp}
						/>
						<SequenceToolbar
							onzoomin={seqViewport.zoomIn}
							onzoomout={seqViewport.zoomOut}
							onfitview={seqViewport.fitView}
						/>
					</div>
				{/if}
			{:else}
				<!-- Canvas toolbar -->
				<div class="mb-3 flex items-center gap-4">
					{#if editing}
						<!-- Create group -->
						<div class="flex items-center gap-2">
							<button
								onclick={() => (showAddEntity = true)}
								class="rounded px-3 py-1.5 text-sm text-white"
								style="background-color: var(--color-primary)"
							>
								Add Entity
							</button>
							<button
								onclick={() => (showEntityPicker = true)}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								Link Entity
							</button>
						</div>
						<!-- Edit group -->
						<div class="flex items-center gap-2">
							<button
								onclick={() => selectedEdgeId && handleDeleteEdge(selectedEdgeId)}
								disabled={!selectedEdgeId}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-danger); color: var(--color-danger)"
							>
								Delete Edge
							</button>
							<button
								onclick={handleUndo}
								disabled={!history.canUndo}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-label="Undo"
								title="Undo (Ctrl+Z)"
							>
								Undo
							</button>
							<button
								onclick={handleRedo}
								disabled={!history.canRedo}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-label="Redo"
								title="Redo (Ctrl+Y)"
							>
								Redo
							</button>
						</div>
						<!-- Persist group -->
						<div class="flex items-center gap-2">
							<button
								onclick={saveCanvas}
								disabled={saving || !canvasDirty}
								class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
								style="background-color: var(--color-success, #16a34a)"
							>
								{saving ? 'Saving...' : 'Save'}
							</button>
							<button
								onclick={discardChanges}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								Discard
							</button>
							{#if canvasDirty}
								<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
							{/if}
						</div>
					{:else}
						<button
							onclick={() => (editing = true)}
							class="rounded px-3 py-1.5 text-sm"
							style="background-color: var(--color-primary); color: white"
						>
							Edit Canvas
						</button>
					{/if}
					<!-- View group (always visible) -->
					<div class="ml-auto">
						<button
							onclick={() => (focusMode = true)}
							class="rounded px-3 py-1.5 text-sm"
							style="border: 1px solid var(--color-border); color: var(--color-fg)"
						>
							Focus
						</button>
					</div>
				</div>

				<!-- Canvas area -->
				{#if editing}
					{#if focusMode}
						<FocusView onexit={() => (focusMode = false)}>
							<div style="width: 100%; height: 100%; border: 1px solid var(--color-border); overflow: hidden">
								{#if canvasType === 'uml' || canvasType === 'archimate'}
									<FullViewCanvas
										viewType={fullViewType}
										bind:nodes={canvasNodes}
										bind:edges={canvasEdges}
										oncreatenode={() => (showAddEntity = true)}
										ondeletenode={handleDeleteNode}
										onconnectnodes={handleConnectNodes}
										ondeleteedge={handleDeleteEdge}
										onundo={handleUndo}
										onredo={handleRedo}
									/>
								{:else}
									<ModelCanvas
										bind:nodes={canvasNodes}
										bind:edges={canvasEdges}
										oncreatenode={() => (showAddEntity = true)}
										ondeletenode={handleDeleteNode}
										onconnectnodes={handleConnectNodes}
										ondeleteedge={handleDeleteEdge}
										onundo={handleUndo}
										onredo={handleRedo}
									/>
								{/if}
							</div>
						</FocusView>
					{/if}
					<div style="height: 500px; border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden">
						{#if canvasType === 'uml' || canvasType === 'archimate'}
							<FullViewCanvas
								viewType={fullViewType}
								bind:nodes={canvasNodes}
								bind:edges={canvasEdges}
								oncreatenode={() => (showAddEntity = true)}
								ondeletenode={handleDeleteNode}
								onconnectnodes={handleConnectNodes}
								ondeleteedge={handleDeleteEdge}
							/>
						{:else}
							<ModelCanvas
								bind:nodes={canvasNodes}
								bind:edges={canvasEdges}
								oncreatenode={() => (showAddEntity = true)}
								ondeletenode={handleDeleteNode}
								onconnectnodes={handleConnectNodes}
								ondeleteedge={handleDeleteEdge}
							/>
						{/if}
					</div>
				{:else if canvasNodes.length === 0}
					<div class="flex flex-col items-center justify-center gap-3 rounded border p-8" style="border-color: var(--color-border); min-height: 300px">
						<p style="color: var(--color-muted)">This model has no diagram yet.</p>
						<button
							onclick={() => (editing = true)}
							class="rounded px-4 py-2 text-sm text-white"
							style="background-color: var(--color-primary)"
						>
							Start Building
						</button>
					</div>
				{:else}
					{#if focusMode}
						<FocusView onexit={() => (focusMode = false)}>
							<div style="width: 100%; height: 100%; border: 1px solid var(--color-border); overflow: hidden">
								<BrowseCanvas
									nodes={canvasNodes}
									edges={canvasEdges}
									onnodeselect={handleBrowseNodeSelect}
								/>
							</div>
						</FocusView>
					{/if}
					<div class="flex gap-4">
						<div class="flex-1" style="height: 500px; border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden">
							<BrowseCanvas
								nodes={canvasNodes}
								edges={canvasEdges}
								onnodeselect={handleBrowseNodeSelect}
							/>
						</div>
						{#if selectedBrowseNode}
							<div style="width: 300px">
								<EntityDetailPanel
									entity={selectedBrowseNode.data}
									onclose={() => (selectedBrowseNode = null)}
									currentModelId={model?.id}
								/>
							</div>
						{/if}
					</div>
				{/if}
			{/if}
		{:else if activeTab === 'versions'}
			{#if versionsLoading}
				<p style="color: var(--color-muted)">Loading versions...</p>
			{:else if versions.length === 0}
				<p style="color: var(--color-muted)">No version history available.</p>
			{:else}
				<table class="w-full text-sm">
					<thead>
						<tr style="border-bottom: 1px solid var(--color-border)">
							<th class="py-2 text-left" style="color: var(--color-muted)">Version</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Type</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">User</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Date</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Change Summary</th>
						</tr>
					</thead>
					<tbody>
						{#each versions as v}
							<tr style="border-bottom: 1px solid var(--color-border)">
								<td class="py-2" style="color: var(--color-fg)">v{v.version}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.change_type}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.created_by_username ?? v.created_by}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.created_at}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.change_summary ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		{/if}
	</div>

	<!-- Comments section -->
	<section class="mt-8">
		<CommentsPanel targetType="model" targetId={model.id} />
	</section>

	<ModelDialog
		open={showEditDialog}
		mode="edit"
		initialName={model.name}
		initialType={model.model_type}
		initialDescription={model.description ?? ''}
		onsave={handleEdit}
		oncancel={() => (showEditDialog = false)}
	/>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Model"
		message="Are you sure you want to delete '{model.name}'? This action cannot be undone."
		confirmLabel="Delete"
		onconfirm={handleDelete}
		oncancel={() => (showDeleteDialog = false)}
	/>

	<EntityDialog
		open={showAddEntity}
		mode="create"
		onsave={handleAddEntity}
		oncancel={() => (showAddEntity = false)}
	/>

	<RelationshipDialog
		open={showRelationshipDialog}
		sourceName={pendingSourceName}
		targetName={pendingTargetName}
		onsave={handleRelationshipSave}
		oncancel={handleRelationshipCancel}
	/>

	<EntityPicker
		open={showEntityPicker}
		onselect={handleLinkEntity}
		oncancel={() => (showEntityPicker = false)}
	/>

	<ParticipantDialog
		open={showAddParticipant}
		onsave={handleAddParticipant}
		oncancel={() => (showAddParticipant = false)}
	/>

	<MessageDialog
		open={showAddMessage}
		participants={sequenceData.participants}
		onsave={handleAddMessage}
		oncancel={() => (showAddMessage = false)}
	/>

{/if}
