<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { exportToSvg, exportToPng, exportToPdf } from '$lib/utils/export';
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
	import ModelPicker from '$lib/components/ModelPicker.svelte';
	import TagInput from '$lib/components/TagInput.svelte';
	import { createCanvasHistory } from '$lib/canvas/useCanvasHistory.svelte';
	import type { Entity } from '$lib/types/api';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';
	import type { SimpleEntityType, SimpleRelationshipType, EdgeRoutingType } from '$lib/types/canvas';
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
	let showCloneDialog = $state(false);
	let inheritedTags = $state<string[]>([]);
	let allTags = $state<string[]>([]);

	// Template designation (derived from tags)
	const isTemplate = $derived((model?.tags ?? []).includes('template'));

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

	// Edit entity state (WP-15)
	let selectedEditNodeId = $state<string | null>(null);
	let showEditEntity = $state(false);
	let editEntityData = $state<Entity | null>(null);

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

	// Export menu state
	let showExportMenu = $state(false);

	// Entity picker state (link existing entity)
	let showEntityPicker = $state(false);

	// Model picker state (insert model as component)
	let showModelPicker = $state(false);

	// Version rollback — not available for models (only entities have rollback API).

	$effect(() => {
		const id = page.params.id;
		if (id) loadModel(id);
	});

	// Listen for edge label edit events from EdgeLabel component (WP-3)
	$effect(() => {
		function onEdgeLabelEdit(e: Event) {
			const { edgeId, label } = (e as CustomEvent).detail;
			if (editing) handleEdgeLabelEdit(edgeId, label);
		}
		document.addEventListener('edgelabeledit', onEdgeLabelEdit);
		return () => document.removeEventListener('edgelabeledit', onEdgeLabelEdit);
	});

	// Listen for edge label move events from EdgeLabel component (WP-4)
	$effect(() => {
		function onEdgeLabelMove(e: Event) {
			const { edgeId, offsetX, offsetY } = (e as CustomEvent).detail;
			if (editing) handleEdgeLabelMove(edgeId, offsetX, offsetY);
		}
		document.addEventListener('edgelabelmove', onEdgeLabelMove);
		return () => document.removeEventListener('edgelabelmove', onEdgeLabelMove);
	});

	/** Determine which canvas component to render based on model type. */
	const canvasType = $derived.by(() => {
		if (!model) return 'simple';
		const mt = model.model_type;
		if (mt === 'sequence') return 'sequence';
		if (mt === 'uml') return 'uml';
		if (mt === 'archimate') return 'archimate';
		if (mt === 'roadmap') return 'simple';
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
			refreshNodeDescriptions();
			loadVersions(id);
			loadBookmarkStatus(id);
			loadInheritedTags();
			loadAllTags();
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Model not found'
				: 'Failed to load model';
		}
		loading = false;
	}

	/** Sync node descriptions from linked entities (WP-5). */
	async function refreshNodeDescriptions() {
		let updated = false;
		const refreshed = await Promise.all(
			canvasNodes.map(async (node) => {
				const entityId = node.data?.entityId;
				if (!entityId) return node;
				try {
					const entity = await apiFetch<Entity>(`/api/entities/${entityId}`);
					if (entity.description !== node.data.description || entity.name !== node.data.label) {
						updated = true;
						return {
							...node,
							data: {
								...node.data,
								label: entity.name,
								description: entity.description ?? '',
							},
						};
					}
				} catch { /* entity may be deleted */ }
				return node;
			}),
		);
		if (updated) {
			canvasNodes = refreshed;
		}
	}

	async function loadInheritedTags() {
		// Compute inherited tags from entities placed on this model's canvas
		const entityTags = new Set<string>();
		for (const node of canvasNodes) {
			const entityId = node.data?.entityId;
			if (!entityId) continue;
			try {
				const e = await apiFetch<{ tags?: string[] }>(`/api/entities/${entityId}`);
				if (e.tags) e.tags.forEach((t) => entityTags.add(t));
			} catch { /* skip inaccessible entities */ }
		}
		const ownTags = new Set(model?.tags ?? []);
		inheritedTags = [...entityTags].filter((t) => !ownTags.has(t)).sort();
	}

	async function toggleTemplate() {
		if (!model) return;
		try {
			if (isTemplate) {
				await apiFetch(`/api/models/${model.id}/tags/${encodeURIComponent('template')}`, {
					method: 'DELETE',
				});
			} else {
				await apiFetch(`/api/models/${model.id}/tags`, {
					method: 'POST',
					body: JSON.stringify({ tag: 'template' }),
				});
			}
			await loadModel(model.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update template status';
		}
	}

	async function loadAllTags() {
		try {
			allTags = await apiFetch<string[]>('/api/entities/tags/all');
		} catch {
			allTags = [];
		}
	}

	async function handleAddTag(tag: string) {
		if (!model) return;
		try {
			await apiFetch(`/api/models/${model.id}/tags`, {
				method: 'POST',
				body: JSON.stringify({ tag }),
			});
			await loadModel(model.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to add tag';
		}
	}

	async function handleRemoveTag(tag: string) {
		if (!model) return;
		try {
			await apiFetch(`/api/models/${model.id}/tags/${encodeURIComponent(tag)}`, {
				method: 'DELETE',
			});
			await loadModel(model.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to remove tag';
		}
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

	async function handleClone(name: string, modelType: string, description: string) {
		if (!model) return;
		try {
			const created = await apiFetch<Model>('/api/models', {
				method: 'POST',
				body: JSON.stringify({
					model_type: modelType,
					name,
					description,
					data: model.data ?? {},
				}),
			});
			showCloneDialog = false;
			await goto(`/models/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to clone model';
		}
	}

	// Canvas editing

	/** Standard node dimensions for overlap detection. */
	const NODE_WIDTH = 220;
	const NODE_HEIGHT = 100;
	const NODE_GAP = 30;

	/** Find a position that doesn't overlap existing nodes. */
	function findOpenPosition(): { x: number; y: number } {
		const cols = 4;
		const cellW = NODE_WIDTH + NODE_GAP;
		const cellH = NODE_HEIGHT + NODE_GAP;
		for (let i = 0; i < 200; i++) {
			const col = i % cols;
			const row = Math.floor(i / cols);
			const x = 60 + col * cellW;
			const y = 60 + row * cellH;
			const overlaps = canvasNodes.some((n) => {
				const nx = n.position.x;
				const ny = n.position.y;
				return (
					Math.abs(nx - x) < NODE_WIDTH + NODE_GAP / 2 &&
					Math.abs(ny - y) < NODE_HEIGHT + NODE_GAP / 2
				);
			});
			if (!overlaps) return { x, y };
		}
		return { x: 60, y: 60 };
	}

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
			const newNode: CanvasNode = {
				id,
				type: entityType,
				position: findOpenPosition(),
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
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = canvasEdges.filter((e) => e.id !== edgeId);
		selectedEdgeId = null;
		canvasDirty = true;
	}

	function handleReconnectEdge() {
		history.pushState(canvasNodes, canvasEdges);
		canvasDirty = true;
	}

	function handleEdgeSelect(edgeId: string | null) {
		selectedEdgeId = edgeId;
	}

	function handleEdgeLabelEdit(edgeId: string, newLabel: string) {
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = canvasEdges.map((e) =>
			e.id === edgeId
				? { ...e, data: { ...e.data!, label: newLabel || undefined } }
				: e,
		);
		canvasDirty = true;
	}

	function handleEdgeLabelMove(edgeId: string, offsetX: number, offsetY: number) {
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = canvasEdges.map((e) =>
			e.id === edgeId
				? { ...e, data: { ...e.data!, labelOffsetX: offsetX, labelOffsetY: offsetY } }
				: e,
		);
		canvasDirty = true;
	}

	function handleNodeSelect(nodeId: string | null) {
		selectedEditNodeId = nodeId;
	}

	/** Whether the currently selected node in edit mode is a linked entity (has entityId). */
	const selectedNodeIsLinkedEntity = $derived.by(() => {
		if (!selectedEditNodeId) return false;
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		return !!node?.data?.entityId;
	});

	/** Open the edit entity dialog by fetching the entity from the API. */
	async function handleEditEntityClick() {
		if (!selectedEditNodeId) return;
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		if (!node?.data?.entityId) return;
		try {
			editEntityData = await apiFetch<Entity>(`/api/entities/${node.data.entityId}`);
			showEditEntity = true;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to load entity for editing';
		}
	}

	/** Save the edited entity via PUT, then update the canvas node. */
	async function handleEditEntitySave(name: string, entityType: SimpleEntityType, description: string) {
		if (!editEntityData || !selectedEditNodeId) return;
		try {
			await apiFetch(`/api/entities/${editEntityData.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(editEntityData.current_version) },
				body: JSON.stringify({
					name,
					entity_type: entityType,
					description,
					change_summary: 'Updated entity from model editor',
				}),
			});
			// Update the canvas node's label and description to reflect the edit
			canvasNodes = canvasNodes.map((n) =>
				n.id === selectedEditNodeId
					? { ...n, type: entityType, data: { ...n.data, label: name, entityType, description } }
					: n,
			);
			canvasDirty = true;
			showEditEntity = false;
			editEntityData = null;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update entity';
		}
	}

	/** Derived routing type for the currently selected edge. */
	const selectedEdgeRoutingType = $derived.by(() => {
		if (!selectedEdgeId) return 'default';
		const edge = canvasEdges.find((e) => e.id === selectedEdgeId);
		return edge?.data?.routingType ?? 'default';
	});

	function handleRoutingTypeChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		const newType = target.value as EdgeRoutingType;
		if (!selectedEdgeId) return;
		history.pushState(canvasNodes, canvasEdges);
		canvasEdges = canvasEdges.map((e) =>
			e.id === selectedEdgeId
				? { ...e, data: { ...e.data!, routingType: newType === 'default' ? undefined : newType } }
				: e,
		);
		canvasDirty = true;
	}

	function handleConnectNodes(sourceId: string, targetId: string) {
		pendingConnection = { sourceId, targetId };
		showRelationshipDialog = true;
	}

	async function handleRelationshipSave(type: SimpleRelationshipType, label: string) {
		if (!pendingConnection) return;
		const { sourceId, targetId } = pendingConnection;

		// Resolve entity IDs from the connected nodes
		const sourceNode = canvasNodes.find((n) => n.id === sourceId);
		const targetNode = canvasNodes.find((n) => n.id === targetId);
		const sourceEntityId = sourceNode?.data?.entityId;
		const targetEntityId = targetNode?.data?.entityId;

		let relationshipId: string | undefined;

		// Create a real relationship record if both nodes are linked to entities
		if (sourceEntityId && targetEntityId) {
			try {
				const rel = await apiFetch<{ id: string }>('/api/relationships', {
					method: 'POST',
					body: JSON.stringify({
						source_entity_id: sourceEntityId,
						target_entity_id: targetEntityId,
						relationship_type: type,
						label: label || type,
						description: '',
					}),
				});
				relationshipId = rel.id;
			} catch {
				// Non-fatal: edge still works visually without a DB relationship
			}
		}

		const newEdge: CanvasEdge = {
			id: `e-${sourceId}-${targetId}`,
			source: sourceId,
			target: targetId,
			type,
			data: {
				relationshipType: type,
				label: label || undefined,
				relationshipId,
			},
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
		const node = canvasNodes.find((n) => n.id === nodeId) ?? null;
		// If the node is a model reference, navigate to it
		if (node?.data?.linkedModelId) {
			goto(`/models/${node.data.linkedModelId}`);
			return;
		}
		selectedBrowseNode = node;
	}

	function handleSequenceParticipantSelect(participant: Participant) {
		if (!participant.entityId) return;
		selectedBrowseNode = {
			id: `seq-participant-${participant.id}`,
			type: 'default',
			position: { x: 0, y: 0 },
			data: {
				label: participant.name,
				entityType: participant.type,
				entityId: participant.entityId,
			},
		};
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
		const entityType = entity.entity_type as SimpleEntityType;
		const newNode: CanvasNode = {
			id,
			type: entityType,
			position: findOpenPosition(),
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

	function handleInsertModel(linkedModel: Model) {
		const id = crypto.randomUUID();
		const newNode: CanvasNode = {
			id,
			type: 'modelref',
			position: findOpenPosition(),
			data: {
				label: linkedModel.name,
				entityType: 'component' as SimpleEntityType,
				description: linkedModel.description ?? '',
				linkedModelId: linkedModel.id,
			},
		};
		history.pushState(canvasNodes, canvasEdges);
		canvasNodes = [...canvasNodes, newNode];
		canvasDirty = true;
		showModelPicker = false;
	}

	function handleNodeDragStart() {
		history.pushState(canvasNodes, canvasEdges);
		canvasDirty = true;
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

	// Export handlers
	function getFlowElement(): HTMLElement | null {
		return document.querySelector('.svelte-flow') as HTMLElement | null;
	}

	async function handleExportSvg() {
		const el = getFlowElement();
		if (el && model) {
			await exportToSvg(el, model.name);
			showExportMenu = false;
		}
	}

	async function handleExportPng() {
		const el = getFlowElement();
		if (el && model) {
			await exportToPng(el, model.name);
			showExportMenu = false;
		}
	}

	async function handleExportPdf() {
		const el = getFlowElement();
		if (el && model) {
			await exportToPdf(el, model.name, model.name);
			showExportMenu = false;
		}
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
				onclick={() => (showCloneDialog = true)}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Clone
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

			<div class="mt-4 flex items-center gap-2">
				<label class="flex items-center gap-2 text-sm cursor-pointer" style="color: var(--color-fg)">
					<input
						type="checkbox"
						checked={isTemplate}
						onchange={toggleTemplate}
						aria-label="Mark as template"
					/>
					Template
				</label>
				<span class="text-xs" style="color: var(--color-muted)">
					Mark this model as a reusable template
				</span>
			</div>

			<div class="mt-4">
				<h3 class="text-sm font-medium mb-2" style="color: var(--color-muted)">Tags</h3>
				<TagInput
					tags={model.tags ?? []}
					onaddtag={handleAddTag}
					onremovetag={handleRemoveTag}
					{inheritedTags}
					suggestions={allTags}
				/>
			</div>
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
					<div class="ml-auto flex items-center gap-2">
						<div class="relative">
							<button
								onclick={() => (showExportMenu = !showExportMenu)}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-haspopup="true"
								aria-expanded={showExportMenu}
							>
								Export
							</button>
							{#if showExportMenu}
								<div
									class="absolute right-0 z-50 mt-1 min-w-[140px] rounded border py-1 shadow-lg"
									style="background-color: var(--color-bg, #fff); border-color: var(--color-border)"
									role="menu"
								>
									<button onclick={handleExportSvg} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">SVG</button>
									<button onclick={handleExportPng} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">PNG</button>
									<button onclick={handleExportPdf} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">PDF</button>
									<button disabled title="Coming soon" class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50" style="color: var(--color-fg)" role="menuitem">Visio</button>
									<button disabled title="Coming soon" class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50" style="color: var(--color-fg)" role="menuitem">Draw.io</button>
								</div>
							{/if}
						</div>
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
									onparticipantselect={!editing ? handleSequenceParticipantSelect : undefined}
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
					{:else}
					<div class="flex gap-4">
						<div class="flex-1" style="height: 500px; border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden; position: relative">
							<SequenceDiagram
								data={sequenceData}
								{selectedMessageId}
								onmessageselect={(id) => (selectedMessageId = id)}
								onparticipantselect={!editing ? handleSequenceParticipantSelect : undefined}
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
						{#if !editing && selectedBrowseNode}
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
							<button
								onclick={() => (showModelPicker = true)}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
							>
								Add Model
							</button>
						</div>
						<!-- Edit group -->
						<div class="flex items-center gap-2">
							{#if selectedNodeIsLinkedEntity}
								<button
									onclick={handleEditEntityClick}
									class="rounded px-3 py-1.5 text-sm"
									style="border: 1px solid var(--color-primary); color: var(--color-primary)"
								>
									Edit Entity
								</button>
							{/if}
							<button
								onclick={() => selectedEdgeId && handleDeleteEdge(selectedEdgeId)}
								disabled={!selectedEdgeId}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-danger); color: var(--color-danger)"
							>
								Delete Edge
							</button>
							{#if selectedEdgeId}
								<label class="flex items-center gap-1 text-sm" style="color: var(--color-fg)">
									Routing:
									<select
										value={selectedEdgeRoutingType}
										onchange={handleRoutingTypeChange}
										class="rounded px-2 py-1 text-sm"
										style="border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-fg)"
										aria-label="Edge routing type"
									>
										<option value="default">Default</option>
										<option value="straight">Straight</option>
										<option value="step">Step</option>
										<option value="smoothstep">Smooth Step</option>
										<option value="bezier">Bezier</option>
									</select>
								</label>
							{/if}
							<button
								onclick={handleUndo}
								disabled={!history.canUndo}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-label="Undo"
								title="Undo (Ctrl/Cmd+Z)"
							>
								Undo
							</button>
							<button
								onclick={handleRedo}
								disabled={!history.canRedo}
								class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-label="Redo"
								title="Redo (Ctrl/Cmd+Y)"
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
					<div class="ml-auto flex items-center gap-2">
						<div class="relative">
							<button
								onclick={() => (showExportMenu = !showExportMenu)}
								class="rounded px-3 py-1.5 text-sm"
								style="border: 1px solid var(--color-border); color: var(--color-fg)"
								aria-haspopup="true"
								aria-expanded={showExportMenu}
							>
								Export
							</button>
							{#if showExportMenu}
								<div
									class="absolute right-0 z-50 mt-1 min-w-[140px] rounded border py-1 shadow-lg"
									style="background-color: var(--color-bg, #fff); border-color: var(--color-border)"
									role="menu"
								>
									<button onclick={handleExportSvg} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">SVG</button>
									<button onclick={handleExportPng} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">PNG</button>
									<button onclick={handleExportPdf} class="block w-full px-4 py-1.5 text-left text-sm hover:opacity-80" style="color: var(--color-fg)" role="menuitem">PDF</button>
									<button disabled title="Coming soon" class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50" style="color: var(--color-fg)" role="menuitem">Visio</button>
									<button disabled title="Coming soon" class="block w-full px-4 py-1.5 text-left text-sm disabled:opacity-50" style="color: var(--color-fg)" role="menuitem">Draw.io</button>
								</div>
							{/if}
						</div>
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
							<div style="display: flex; flex-direction: column; width: 100%; height: 100%;">
								<!-- Toolbar inside FocusView so edit controls are visible -->
								<div class="flex items-center gap-4 p-2" style="border-bottom: 1px solid var(--color-border); background: var(--color-surface); flex-shrink: 0;">
									<div class="flex items-center gap-2">
										<button onclick={() => (showAddEntity = true)} class="rounded px-3 py-1.5 text-sm text-white" style="background-color: var(--color-primary)">Add Entity</button>
										<button onclick={() => (showEntityPicker = true)} class="rounded px-3 py-1.5 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">Link Entity</button>
										<button onclick={() => (showModelPicker = true)} class="rounded px-3 py-1.5 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">Add Model</button>
									</div>
									<div class="flex items-center gap-2">
										<button onclick={handleUndo} disabled={!history.canUndo} class="rounded px-3 py-1.5 text-sm disabled:opacity-50" style="border: 1px solid var(--color-border); color: var(--color-fg)" aria-label="Undo">Undo</button>
										<button onclick={handleRedo} disabled={!history.canRedo} class="rounded px-3 py-1.5 text-sm disabled:opacity-50" style="border: 1px solid var(--color-border); color: var(--color-fg)" aria-label="Redo">Redo</button>
									</div>
									<div class="flex items-center gap-2">
										<button onclick={saveCanvas} disabled={saving || !canvasDirty} class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50" style="background-color: var(--color-success, #16a34a)">{saving ? 'Saving...' : 'Save'}</button>
										<button onclick={discardChanges} class="rounded px-3 py-1.5 text-sm" style="border: 1px solid var(--color-border); color: var(--color-fg)">Discard</button>
										{#if canvasDirty}
											<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
										{/if}
									</div>
								</div>
								<div style="flex: 1; border: 1px solid var(--color-border); overflow: hidden">
									{#if canvasType === 'uml' || canvasType === 'archimate'}
										<FullViewCanvas
											viewType={fullViewType}
											bind:nodes={canvasNodes}
											bind:edges={canvasEdges}
											oncreatenode={() => (showAddEntity = true)}
											ondeletenode={handleDeleteNode}
											onconnectnodes={handleConnectNodes}
											ondeleteedge={handleDeleteEdge}
											onreconnectedge={handleReconnectEdge}
											onedgeselect={handleEdgeSelect}
											onnodeselect={handleNodeSelect}
											onundo={handleUndo}
											onredo={handleRedo}
											onnodedragstart={handleNodeDragStart}
										/>
									{:else}
										<ModelCanvas
											bind:nodes={canvasNodes}
											bind:edges={canvasEdges}
											oncreatenode={() => (showAddEntity = true)}
											ondeletenode={handleDeleteNode}
											onconnectnodes={handleConnectNodes}
											ondeleteedge={handleDeleteEdge}
											onreconnectedge={handleReconnectEdge}
											onedgeselect={handleEdgeSelect}
											onnodeselect={handleNodeSelect}
											onundo={handleUndo}
											onredo={handleRedo}
											onnodedragstart={handleNodeDragStart}
										/>
									{/if}
								</div>
							</div>
						</FocusView>
					{:else}
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
								onreconnectedge={handleReconnectEdge}
								onedgeselect={handleEdgeSelect}
								onnodeselect={handleNodeSelect}
								onundo={handleUndo}
								onredo={handleRedo}
								onnodedragstart={handleNodeDragStart}
							/>
						{:else}
							<ModelCanvas
								bind:nodes={canvasNodes}
								bind:edges={canvasEdges}
								oncreatenode={() => (showAddEntity = true)}
								ondeletenode={handleDeleteNode}
								onconnectnodes={handleConnectNodes}
								ondeleteedge={handleDeleteEdge}
								onreconnectedge={handleReconnectEdge}
								onedgeselect={handleEdgeSelect}
								onnodeselect={handleNodeSelect}
								onundo={handleUndo}
								onredo={handleRedo}
								onnodedragstart={handleNodeDragStart}
							/>
						{/if}
					</div>
					{/if}
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
					{:else}
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

	<ModelDialog
		open={showCloneDialog}
		mode="create"
		initialName="{model.name} (Copy)"
		initialType={model.model_type}
		initialDescription={model.description ?? ''}
		onsave={handleClone}
		oncancel={() => (showCloneDialog = false)}
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

	<EntityDialog
		open={showEditEntity}
		mode="edit"
		initialName={editEntityData?.name ?? ''}
		initialType={(editEntityData?.entity_type ?? 'component') as SimpleEntityType}
		initialDescription={editEntityData?.description ?? ''}
		onsave={handleEditEntitySave}
		oncancel={() => { showEditEntity = false; editEntityData = null; }}
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

	<ModelPicker
		open={showModelPicker}
		onselect={handleInsertModel}
		oncancel={() => (showModelPicker = false)}
		excludeModelId={model?.id}
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
