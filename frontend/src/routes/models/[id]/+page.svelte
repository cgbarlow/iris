<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { exportToSvg, exportToPng, exportToPdf } from '$lib/utils/export';
	import type { Model, ModelVersion, Bookmark } from '$lib/types/api';
	import UnifiedCanvas from '$lib/canvas/UnifiedCanvas.svelte';
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
	import NodeDeleteDialog from '$lib/components/NodeDeleteDialog.svelte';
	import TreeNode from '$lib/components/TreeNode.svelte';
	import TagInput from '$lib/components/TagInput.svelte';
	import { Accordion } from 'bits-ui';
	import { createCanvasHistory } from '$lib/canvas/useCanvasHistory.svelte';
	import DOMPurify from 'dompurify';
	import type { Entity, ModelHierarchyNode } from '$lib/types/api';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';
	import type { SimpleEntityType, SimpleRelationshipType, EdgeRoutingType, NotationType } from '$lib/types/canvas';
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
	let activeTab = $state<'details' | 'canvas' | 'relationships' | 'versions'>('canvas');
	let userSelectedTab = $state(false);
	let versionsLoading = $state(false);

	// Model relationships state
	interface ModelRelationship {
		id: string;
		source_model_id: string;
		target_model_id: string;
		relationship_type: string;
		label: string | null;
		description: string | null;
		created_by: string;
		created_at: string;
		source_name: string;
		target_name: string;
	}
	interface EntityRelationship {
		id: string;
		source_entity_id: string;
		target_entity_id: string;
		relationship_type: string;
		label: string | null;
		description: string | null;
		created_by: string;
		created_at: string;
		source_name: string;
		target_name: string;
	}
	let modelRelationships = $state<ModelRelationship[]>([]);
	let entityRelationships = $state<EntityRelationship[]>([]);
	let relationshipsLoading = $state(false);

	let showDeleteDialog = $state(false);
	let showCloneDialog = $state(false);
	let inheritedTags = $state<string[]>([]);
	let allTags = $state<string[]>([]);

	// Inline metadata editing state
	let editingOverview = $state(false);
	let overviewDirty = $state(false);
	let savingOverview = $state(false);
	let editName = $state('');
	let editDescription = $state('');
	let editTags = $state<string[]>([]);
	let editIsTemplate = $state(false);

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

	// Hierarchy breadcrumb state
	let ancestors = $state<{ id: string; name: string; model_type: string }[]>([]);

	// Focus view state
	let focusMode = $state(false);

	// Hierarchy tree sidebar state
	let sidebarOpen = $state(false);
	let hierarchyTree = $state<ModelHierarchyNode[]>([]);
	let hierarchyLoading = $state(false);
	let treeSearchQuery = $state('');
	let showCreateChildDialog = $state(false);
	let showParentPicker = $state(false);
	let treeModelsOnly = $state(false);
	let treeExpandedIds = $state(new Set<string>());

	// Export menu state
	let showExportMenu = $state(false);

	// Entity picker state (link existing entity)
	let showEntityPicker = $state(false);

	// Model picker state (insert model as component)
	let showModelPicker = $state(false);

	// Node delete dialog state
	let showNodeDeleteDialog = $state(false);
	let deleteNodeId = $state<string | null>(null);
	let deleteNodeName = $state('');
	let deleteNodeIsModelRef = $state(false);

	// Add entity relationship from tab state
	let addEntityRelStep = $state<'source' | 'target' | 'details' | null>(null);
	let addEntityRelSource = $state<Entity | null>(null);
	let addEntityRelTarget = $state<Entity | null>(null);

	// Add model relationship from tab state
	let showAddModelRelPicker = $state(false);
	let showAddModelRelDialog = $state(false);
	let addModelRelTarget = $state<{ id: string; name: string } | null>(null);

	// "Add to canvas?" prompt state
	let showAddToCanvasPrompt = $state(false);
	let addToCanvasRelType = $state<'entity' | 'model'>('entity');
	let addToCanvasRelData = $state<{
		sourceEntityId?: string; targetEntityId?: string;
		sourceName?: string; targetName?: string;
		targetModelId?: string; targetModelName?: string;
		relationshipType?: string;
	} | null>(null);

	// Version rollback — not available for models (only entities have rollback API).

	let prevSetId = $state<string | undefined>(undefined);

	$effect(() => {
		const id = page.params.id;
		if (id) {
			userSelectedTab = false;
			loadModel(id);
		}
	});

	// Reload hierarchy tree when navigating to a model with a different set_id
	$effect(() => {
		if (model && sidebarOpen && model.set_id !== prevSetId) {
			prevSetId = model.set_id;
			treeExpandedIds = new Set<string>();
			loadHierarchyTree();
		}
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
		if (mt === 'c4' || mt === 'c4_landscape' || mt === 'c4_dynamic' || mt === 'c4_deployment') return 'c4';
		if (mt === 'roadmap') return 'simple';
		return 'simple'; // 'simple' and 'component' both use simple view
	});

	/** Notation for UnifiedCanvas context. */
	const notation = $derived<NotationType>(canvasType === 'sequence' ? 'simple' : canvasType as NotationType);

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
			// Smart default tab: show details if no canvas content
			if (!userSelectedTab) {
				const hasContent = model.model_type === 'sequence'
					? sequenceData.participants.length > 0
					: canvasNodes.length > 0;
				activeTab = hasContent ? 'canvas' : 'details';
			}
			refreshNodeDescriptions();
			loadVersions(id);
			loadBookmarkStatus(id);
			loadInheritedTags();
			loadAllTags();
			loadAncestors(id);
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

	async function loadAllTags() {
		try {
			allTags = await apiFetch<string[]>('/api/entities/tags/all');
		} catch {
			allTags = [];
		}
	}

	async function loadAncestors(id: string) {
		try {
			ancestors = await apiFetch<{ id: string; name: string; model_type: string }[]>(
				`/api/models/${id}/ancestors`
			);
		} catch {
			ancestors = [];
		}
	}

	async function loadHierarchyTree() {
		if (!model?.set_id) return;
		hierarchyLoading = true;
		try {
			hierarchyTree = await apiFetch<ModelHierarchyNode[]>(
				`/api/models/hierarchy?set_id=${model.set_id}`
			);
		} catch {
			hierarchyTree = [];
		}
		hierarchyLoading = false;
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
		if (sidebarOpen && hierarchyTree.length === 0) {
			loadHierarchyTree();
		}
	}

	async function handleCreateChild(name: string, modelType: string, description: string) {
		if (!model) return;
		try {
			const created = await apiFetch<Model>('/api/models', {
				method: 'POST',
				body: JSON.stringify({
					model_type: modelType,
					name,
					description,
					data: {},
					parent_model_id: model.id,
					set_id: model.set_id,
				}),
			});
			showCreateChildDialog = false;
			await loadHierarchyTree();
			await goto(`/models/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create child model';
		}
	}

	async function handleSetParent(parentModel: Model) {
		if (!model) return;
		showParentPicker = false;
		try {
			await apiFetch(`/api/models/${model.id}/parent`, {
				method: 'PUT',
				body: JSON.stringify({ parent_model_id: parentModel.id }),
			});
			await loadModel(model.id);
			if (sidebarOpen) await loadHierarchyTree();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to set parent';
		}
	}

	async function handleRemoveParent() {
		if (!model) return;
		try {
			await apiFetch(`/api/models/${model.id}/parent`, {
				method: 'PUT',
				body: JSON.stringify({ parent_model_id: null }),
			});
			await loadModel(model.id);
			if (sidebarOpen) await loadHierarchyTree();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to remove parent';
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

	async function loadModelRelationships(id: string) {
		relationshipsLoading = true;
		try {
			const result = await apiFetch<{
				model_relationships: ModelRelationship[];
				entity_relationships: EntityRelationship[];
			}>(`/api/models/${id}/relationships`);
			modelRelationships = result.model_relationships;
			entityRelationships = result.entity_relationships;
		} catch {
			modelRelationships = [];
			entityRelationships = [];
		}
		relationshipsLoading = false;
	}

	async function deleteModelRelationship(relId: string) {
		if (!model) return;
		try {
			await apiFetch(`/api/model-relationships/${relId}`, { method: 'DELETE' });
			modelRelationships = modelRelationships.filter((r) => r.id !== relId);
		} catch {
			// ignore
		}
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

	function enterOverviewEdit() {
		if (!model) return;
		editName = model.name;
		editDescription = model.description ?? '';
		editTags = (model.tags ?? []).filter(t => t !== 'template');
		editIsTemplate = isTemplate;
		editingOverview = true;
		overviewDirty = false;
	}

	// Track dirty state for inline editing
	$effect(() => {
		if (!editingOverview || !model) return;
		const nameChanged = editName !== model.name;
		const descChanged = editDescription !== (model.description ?? '');
		const origTags = (model.tags ?? []).filter(t => t !== 'template');
		const tagsChanged = JSON.stringify(editTags.slice().sort()) !== JSON.stringify(origTags.slice().sort());
		const templateChanged = editIsTemplate !== isTemplate;
		overviewDirty = nameChanged || descChanged || tagsChanged || templateChanged;
	});

	async function saveMetadata() {
		if (!model) return;
		savingOverview = true;
		error = null;
		try {
			const sanitizedName = DOMPurify.sanitize(editName).trim();
			const sanitizedDesc = DOMPurify.sanitize(editDescription).trim();
			if (!sanitizedName) {
				error = 'Name is required';
				savingOverview = false;
				return;
			}
			await apiFetch(`/api/models/${model.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(model.current_version) },
				body: JSON.stringify({
					name: sanitizedName,
					description: sanitizedDesc,
					data: model.data,
					change_summary: 'Updated model details',
				}),
			});

			// Sync tags
			const oldTags = model.tags ?? [];
			const newTags = [...editTags];

			// Handle template toggle via tags
			if (editIsTemplate && !newTags.includes('template')) {
				newTags.push('template');
			}
			const fullOldTags = oldTags;
			const toAdd = newTags.filter((t) => !fullOldTags.includes(t));
			const toRemove = fullOldTags.filter((t) => !newTags.includes(t));
			if (!editIsTemplate && oldTags.includes('template') && !toRemove.includes('template')) {
				toRemove.push('template');
			}

			for (const tag of toAdd) {
				await apiFetch(`/api/models/${model.id}/tags`, {
					method: 'POST',
					body: JSON.stringify({ tag }),
				});
			}
			for (const tag of toRemove) {
				await apiFetch(`/api/models/${model.id}/tags/${encodeURIComponent(tag)}`, {
					method: 'DELETE',
				});
			}

			editingOverview = false;
			overviewDirty = false;
			await loadModel(model.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update model';
		}
		savingOverview = false;
	}

	function discardOverviewChanges() {
		editingOverview = false;
		overviewDirty = false;
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
		const node = canvasNodes.find((n) => n.id === nodeId);
		if (!node) return;
		deleteNodeId = nodeId;
		deleteNodeName = node.data?.label ?? 'Unknown';
		deleteNodeIsModelRef = !!node.data?.linkedModelId;
		showNodeDeleteDialog = true;
	}

	function handleRemoveNodeFromCanvas() {
		if (!deleteNodeId) return;
		history.pushState(canvasNodes, canvasEdges);
		canvasNodes = canvasNodes.filter((n) => n.id !== deleteNodeId);
		canvasEdges = canvasEdges.filter((e) => e.source !== deleteNodeId && e.target !== deleteNodeId);
		canvasDirty = true;
		showNodeDeleteDialog = false;
		deleteNodeId = null;
	}

	async function handleCascadeDeleteEntity() {
		if (!deleteNodeId) return;
		const node = canvasNodes.find((n) => n.id === deleteNodeId);
		const entityId = node?.data?.entityId;
		if (!entityId) return;

		try {
			// Fetch entity to get current version for OCC
			const entity = await apiFetch<Entity>(`/api/entities/${entityId}`);
			await apiFetch(`/api/entities/${entityId}?cascade=true`, {
				method: 'DELETE',
				headers: { 'If-Match': String(entity.current_version) },
			});
			// Remove node from local canvas state
			history.pushState(canvasNodes, canvasEdges);
			canvasNodes = canvasNodes.filter((n) => n.id !== deleteNodeId);
			canvasEdges = canvasEdges.filter((e) => e.source !== deleteNodeId && e.target !== deleteNodeId);
			canvasDirty = true;
			showNodeDeleteDialog = false;
			deleteNodeId = null;
			// Reload model (canvas data may have changed server-side)
			if (model) await loadModel(model.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete entity';
			showNodeDeleteDialog = false;
		}
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

	/** Navigate to the entity page in edit mode. */
	function handleEditEntityClick() {
		if (!selectedEditNodeId) return;
		const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
		if (!node?.data?.entityId) return;
		goto(`/entities/${node.data.entityId}?edit=true`);
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
		let modelRelationshipId: string | undefined;
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
		} else if (sourceNode?.data?.linkedModelId && targetNode?.data?.linkedModelId && model) {
			// Both nodes are modelrefs — create a model relationship
			try {
				const rel = await apiFetch<{ id: string }>(`/api/models/${sourceNode.data.linkedModelId}/relationships`, {
					method: 'POST',
					body: JSON.stringify({
						target_model_id: targetNode.data.linkedModelId,
						relationship_type: type,
						label: label || undefined,
					}),
				});
				modelRelationshipId = rel.id;
			} catch {
				// Non-fatal: edge still works visually
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
				modelRelationshipId,
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

	// --- Add entity relationship from tab ---
	function handleStartAddEntityRel() {
		addEntityRelStep = 'source';
		addEntityRelSource = null;
		addEntityRelTarget = null;
	}

	function handleEntityRelSourceSelected(entity: Entity) {
		addEntityRelSource = entity;
		addEntityRelStep = 'target';
	}

	function handleEntityRelTargetSelected(entity: Entity) {
		addEntityRelTarget = entity;
		addEntityRelStep = 'details';
	}

	async function handleEntityRelSave(type: SimpleRelationshipType, label: string) {
		if (!addEntityRelSource || !addEntityRelTarget || !model) return;
		try {
			await apiFetch('/api/relationships', {
				method: 'POST',
				body: JSON.stringify({
					source_entity_id: addEntityRelSource.id,
					target_entity_id: addEntityRelTarget.id,
					relationship_type: type,
					label: label || type,
					description: '',
				}),
			});
			addEntityRelStep = null;
			loadModelRelationships(model.id);
			// Prompt to add to canvas
			addToCanvasRelType = 'entity';
			addToCanvasRelData = {
				sourceEntityId: addEntityRelSource.id,
				targetEntityId: addEntityRelTarget.id,
				sourceName: addEntityRelSource.name,
				targetName: addEntityRelTarget.name,
				relationshipType: type,
			};
			showAddToCanvasPrompt = true;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create relationship';
			addEntityRelStep = null;
		}
	}

	// --- Add model relationship from tab ---
	function handleStartAddModelRel() {
		showAddModelRelPicker = true;
		addModelRelTarget = null;
	}

	function handleModelRelTargetSelected(selectedModel: Model) {
		addModelRelTarget = { id: selectedModel.id, name: selectedModel.name };
		showAddModelRelPicker = false;
		showAddModelRelDialog = true;
	}

	async function handleModelRelSave(type: SimpleRelationshipType, label: string) {
		if (!addModelRelTarget || !model) return;
		try {
			await apiFetch(`/api/models/${model.id}/relationships`, {
				method: 'POST',
				body: JSON.stringify({
					target_model_id: addModelRelTarget.id,
					relationship_type: type,
					label: label || undefined,
				}),
			});
			showAddModelRelDialog = false;
			loadModelRelationships(model.id);
			// Prompt to add to canvas
			addToCanvasRelType = 'model';
			addToCanvasRelData = {
				targetModelId: addModelRelTarget.id,
				targetModelName: addModelRelTarget.name,
			};
			showAddToCanvasPrompt = true;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create model relationship';
			showAddModelRelDialog = false;
		}
	}

	// --- "Add to canvas?" prompt ---
	function handleAddToCanvas() {
		if (!addToCanvasRelData) return;
		if (addToCanvasRelType === 'entity') {
			const { sourceEntityId, targetEntityId, sourceName, targetName, relationshipType } = addToCanvasRelData;
			if (!sourceEntityId || !targetEntityId) return;

			history.pushState(canvasNodes, canvasEdges);

			// Find or create source node
			let sourceNodeId = canvasNodes.find((n) => n.data?.entityId === sourceEntityId)?.id;
			if (!sourceNodeId) {
				sourceNodeId = crypto.randomUUID();
				canvasNodes = [...canvasNodes, {
					id: sourceNodeId,
					type: 'component',
					position: findOpenPosition(),
					data: { label: sourceName ?? 'Source', entityType: 'component' as SimpleEntityType, entityId: sourceEntityId },
				}];
			}

			// Find or create target node
			let targetNodeId = canvasNodes.find((n) => n.data?.entityId === targetEntityId)?.id;
			if (!targetNodeId) {
				targetNodeId = crypto.randomUUID();
				canvasNodes = [...canvasNodes, {
					id: targetNodeId,
					type: 'component',
					position: findOpenPosition(),
					data: { label: targetName ?? 'Target', entityType: 'component' as SimpleEntityType, entityId: targetEntityId },
				}];
			}

			// Add edge
			const edgeType = (relationshipType ?? 'uses') as SimpleRelationshipType;
			canvasEdges = [...canvasEdges, {
				id: `e-${sourceNodeId}-${targetNodeId}`,
				source: sourceNodeId,
				target: targetNodeId,
				type: edgeType,
				data: { relationshipType: edgeType },
			}];

			canvasDirty = true;
			activeTab = 'canvas';
		} else if (addToCanvasRelType === 'model') {
			const { targetModelId, targetModelName } = addToCanvasRelData;
			if (!targetModelId) return;

			// Only add target model as modelref node if not already present
			const existing = canvasNodes.find((n) => n.data?.linkedModelId === targetModelId);
			if (!existing) {
				history.pushState(canvasNodes, canvasEdges);
				canvasNodes = [...canvasNodes, {
					id: crypto.randomUUID(),
					type: 'modelref',
					position: findOpenPosition(),
					data: { label: targetModelName ?? 'Model', entityType: 'component' as SimpleEntityType, linkedModelId: targetModelId },
				}];
				canvasDirty = true;
			}
			activeTab = 'canvas';
		}
		showAddToCanvasPrompt = false;
		addToCanvasRelData = null;
	}

	function handleDismissAddToCanvas() {
		showAddToCanvasPrompt = false;
		addToCanvasRelData = null;
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

{#if loading}
	<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
		<ol class="flex gap-1">
			<li><a href="/models" style="color: var(--color-primary)">Models</a></li>
			<li aria-hidden="true">/</li>
			<li aria-current="page">{page.params.id}</li>
		</ol>
	</nav>
	<p style="color: var(--color-muted)">Loading model...</p>
{:else if error}
	<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
		<ol class="flex gap-1">
			<li><a href="/models" style="color: var(--color-primary)">Models</a></li>
			<li aria-hidden="true">/</li>
			<li aria-current="page">{page.params.id}</li>
		</ol>
	</nav>
	<div role="alert" class="rounded border p-4" style="border-color: var(--color-danger); color: var(--color-danger)">
		{error}
	</div>
{:else if model}
	<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
		<ol class="flex items-center gap-1">
			<li><a href="/models" style="color: var(--color-primary)">Models</a></li>
			{#each ancestors as ancestor}
				<li class="flex items-center gap-1">
					<span aria-hidden="true">/</span>
					<a href="/models/{ancestor.id}" style="color: var(--color-primary)">{ancestor.name}</a>
				</li>
			{/each}
			<li class="flex items-center gap-1">
				<span aria-hidden="true">/</span>
				<span aria-current="page">{model.name}</span>
			</li>
		</ol>
	</nav>
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

	<div class="mt-6 flex gap-4">
	<!-- Collapsible hierarchy sidebar -->
	{#if sidebarOpen}
		<aside
			style="width: 280px; max-height: calc(100vh - 80px); flex-shrink: 0"
			class="overflow-y-auto rounded border"
			style:border-color="var(--color-border)"
			style:background-color="var(--color-surface)"
			aria-label="Model hierarchy"
		>
			<div class="flex items-center justify-between p-3" style="border-bottom: 1px solid var(--color-border)">
				<span class="text-sm font-semibold" style="color: var(--color-fg)">Hierarchy</span>
				<div class="flex items-center gap-1">
					<button
						onclick={() => (treeModelsOnly = !treeModelsOnly)}
						class="rounded px-2 py-1 text-xs"
						style="border: 1px solid {treeModelsOnly ? 'var(--color-primary)' : 'var(--color-border)'}; color: {treeModelsOnly ? 'var(--color-primary)' : 'var(--color-fg)'}; background: {treeModelsOnly ? 'var(--color-surface, transparent)' : 'transparent'}"
						title="Show only items with child models"
						aria-pressed={treeModelsOnly}
					>
						Models
					</button>
					<button
						onclick={() => (showCreateChildDialog = true)}
						class="rounded px-2 py-1 text-xs"
						style="background: var(--color-primary); color: white"
						title="Create child model"
					>
						+ Child
					</button>
					<button
						onclick={() => (sidebarOpen = false)}
						class="rounded p-1 text-xs"
						style="color: var(--color-muted)"
						aria-label="Close sidebar"
					>
						✕
					</button>
				</div>
			</div>
			<div class="p-2">
				<input
					type="search"
					placeholder="Search tree..."
					bind:value={treeSearchQuery}
					class="w-full rounded border px-2 py-1 text-xs"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					aria-label="Search hierarchy"
				/>
			</div>
			<div class="px-2 pb-2">
				{#if hierarchyLoading}
					<p class="p-2 text-xs" style="color: var(--color-muted)">Loading...</p>
				{:else if hierarchyTree.length === 0}
					<p class="p-2 text-xs" style="color: var(--color-muted)">No models in this set.</p>
				{:else}
					<ul role="tree">
						{#each hierarchyTree as node (node.id)}
							<TreeNode {node} currentModelId={model.id} searchQuery={treeSearchQuery} showModelsOnly={treeModelsOnly} expandedIds={treeExpandedIds} />
						{/each}
					</ul>
				{/if}
			</div>
		</aside>
	{/if}

	<!-- Main content -->
	<div class="min-w-0 flex-1">
	<!-- Tab navigation with hierarchy toggle -->
	<div class="flex items-center gap-1 border-b" style="border-color: var(--color-border)">
		<button onclick={toggleSidebar} aria-label="Toggle hierarchy sidebar" aria-pressed={sidebarOpen} class="rounded p-1">
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="20" height="20"
				style="color: {sidebarOpen ? 'var(--color-primary)' : 'var(--color-muted)'}">
				<path d="M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z"/>
			</svg>
		</button>
		<div class="flex gap-1" role="tablist" aria-label="Model sections">
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
				aria-selected={activeTab === 'canvas'}
				onclick={() => { activeTab = 'canvas'; userSelectedTab = true; }}
				class="px-4 py-2 text-sm"
				style="color: {activeTab === 'canvas' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'canvas' ? 'var(--color-primary)' : 'transparent'}"
			>
				Canvas
			</button>
			<button
				role="tab"
				aria-selected={activeTab === 'relationships'}
				onclick={() => { activeTab = 'relationships'; userSelectedTab = true; if (model) loadModelRelationships(model.id); }}
				class="px-4 py-2 text-sm"
				style="color: {activeTab === 'relationships' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'relationships' ? 'var(--color-primary)' : 'transparent'}"
			>
				Relationships
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

	<div class="mt-4" role="tabpanel">
		{#if activeTab === 'details'}
			{@const modifiedByUsername = versions.length > 0 ? (versions[0].created_by_username ?? versions[0].created_by) : (model.created_by_username ?? model.created_by)}
			<!-- Inline edit toolbar -->
			<div class="mb-3 flex items-center gap-2">
				{#if editingOverview}
					<button
						onclick={saveMetadata}
						disabled={!overviewDirty || savingOverview}
						class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
						style="background-color: var(--color-success, #16a34a)"
					>
						{savingOverview ? 'Saving...' : 'Save'}
					</button>
					<button
						onclick={discardOverviewChanges}
						class="rounded px-3 py-1.5 text-sm"
						style="border: 1px solid var(--color-border); color: var(--color-fg)"
					>
						Discard
					</button>
					{#if overviewDirty}
						<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
					{/if}
				{:else}
					<button
						onclick={enterOverviewEdit}
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
					<Accordion.Content class="pb-4">
						<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">Name</dt>
							<dd>
								{#if editingOverview}
									<input
										type="text"
										bind:value={editName}
										class="w-full rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									/>
								{:else}
									<span style="color: var(--color-fg)">{model.name}</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
							<dd>
								{#if editingOverview}
									<textarea
										bind:value={editDescription}
										rows="3"
										class="w-full rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									></textarea>
								{:else}
									<span style="color: var(--color-fg)">{model.description ?? 'No description'}</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Type</dt>
							<dd style="color: var(--color-fg)">{model.model_type}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Set</dt>
							<dd>
								<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-fg)">
									{model.set_name ?? 'Default'}
								</span>
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Tags</dt>
							<dd>
								{#if editingOverview}
									<TagInput
										tags={editTags}
										onaddtag={(tag) => { editTags = [...editTags, tag]; }}
										onremovetag={(tag) => { editTags = editTags.filter(t => t !== tag); }}
										{inheritedTags}
										suggestions={allTags}
									/>
								{:else if (model.tags ?? []).length > 0 || inheritedTags.length > 0}
									<div class="flex flex-wrap gap-1">
										{#each (model.tags ?? []) as tag}
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

				<!-- Details group (collapsed) -->
				<Accordion.Item value="model-details" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Details
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4">
						<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">ID</dt>
							<dd class="text-sm" style="color: var(--color-fg)">{model.id}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Version</dt>
							<dd style="color: var(--color-fg)">{model.current_version ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Status</dt>
							<dd style="color: var(--color-fg)">{(model.metadata?.status as string) ?? '—'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Parent</dt>
							<dd class="flex items-center gap-2">
								{#if model.parent_model_id}
									{@const parentAncestor = ancestors.length > 0 ? ancestors[ancestors.length - 1] : null}
									{#if parentAncestor}
										<a href="/models/{parentAncestor.id}" style="color: var(--color-primary)" class="text-sm">{parentAncestor.name}</a>
									{:else}
										<span class="text-sm" style="color: var(--color-fg)">{model.parent_model_id.slice(0, 8)}...</span>
									{/if}
								{:else}
									<span class="text-sm" style="color: var(--color-muted)">None — root model</span>
								{/if}
								<button
									onclick={() => (showParentPicker = true)}
									class="rounded px-2 py-0.5 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-primary)"
								>
									Change
								</button>
								{#if model.parent_model_id}
									<button
										onclick={handleRemoveParent}
										class="rounded px-2 py-0.5 text-xs"
										style="border: 1px solid var(--color-border); color: var(--color-danger)"
									>
										Remove
									</button>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
							<dd style="color: var(--color-fg)">{model.created_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created By</dt>
							<dd style="color: var(--color-fg)">{model.created_by_username ?? model.created_by}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified</dt>
							<dd style="color: var(--color-fg)">{model.updated_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified By</dt>
							<dd style="color: var(--color-fg)">{modifiedByUsername}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Template</dt>
							<dd>
								{#if editingOverview}
									<label class="flex items-center gap-2 text-sm" style="color: var(--color-fg)">
										<input type="checkbox" bind:checked={editIsTemplate} />
										{editIsTemplate ? 'Yes' : 'No'}
									</label>
								{:else}
									<span style="color: var(--color-fg)">{isTemplate ? 'Yes' : 'No'}</span>
								{/if}
							</dd>
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
					<Accordion.Content class="pb-4">
						{#if model.metadata?.stereotype || (Array.isArray(model.metadata?.tagged_values) && (model.metadata.tagged_values as unknown[]).length > 0)}
							<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
								{#if model.metadata?.stereotype}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Stereotype</dt>
									<dd style="color: var(--color-fg)">{model.metadata.stereotype}</dd>
								{/if}

								{#if Array.isArray(model.metadata?.tagged_values) && (model.metadata.tagged_values as unknown[]).length > 0}
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
												{#each model.metadata.tagged_values as tv}
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
		{:else if activeTab === 'canvas'}
			{#if canvasType === 'sequence'}
				<!-- Sequence diagram toolbar -->
				<div class="mb-3 flex flex-wrap items-center gap-2 gap-y-2">
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
							aria-label="Full screen"
							title="Full screen"
						>
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle">
								<polyline points="15 3 21 3 21 9"></polyline>
								<polyline points="9 21 3 21 3 15"></polyline>
								<polyline points="21 15 21 21 15 21"></polyline>
								<polyline points="3 9 3 3 9 3"></polyline>
							</svg>
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
				<div class="mb-3 flex flex-wrap items-center gap-2 gap-y-2">
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
							{#if selectedEditNodeId}
								<button
									onclick={() => selectedEditNodeId && handleDeleteNode(selectedEditNodeId)}
									class="rounded px-3 py-1.5 text-sm"
									style="border: 1px solid var(--color-danger); color: var(--color-danger)"
								>
									Remove
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
							aria-label="Full screen"
							title="Full screen"
						>
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block; vertical-align: middle">
								<polyline points="15 3 21 3 21 9"></polyline>
								<polyline points="9 21 3 21 3 15"></polyline>
								<polyline points="21 15 21 21 15 21"></polyline>
								<polyline points="3 9 3 3 9 3"></polyline>
							</svg>
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
									<UnifiedCanvas
										{notation}
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
								</div>
							</div>
						</FocusView>
					{:else}
					<div style="height: 500px; border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden">
						<UnifiedCanvas
							{notation}
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
								<UnifiedCanvas
									{notation}
									nodes={canvasNodes}
									edges={canvasEdges}
									browseMode={true}
									onnodeselect={handleBrowseNodeSelect}
								/>
							</div>
						</FocusView>
					{:else}
					<div class="flex gap-4">
						<div class="flex-1" style="height: 500px; border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden">
							<UnifiedCanvas
								{notation}
								nodes={canvasNodes}
								edges={canvasEdges}
								browseMode={true}
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
		{:else if activeTab === 'relationships'}
			<!-- Add relationship buttons -->
			<div class="mb-4 flex gap-2">
				<button
					onclick={handleStartAddEntityRel}
					class="rounded px-3 py-1.5 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					Add Entity Relationship
				</button>
				<button
					onclick={handleStartAddModelRel}
					class="rounded px-3 py-1.5 text-sm"
					style="border: 1px solid var(--color-primary); color: var(--color-primary)"
				>
					Add Model Relationship
				</button>
			</div>

			{#if relationshipsLoading}
				<p style="color: var(--color-muted)">Loading relationships...</p>
			{:else if modelRelationships.length === 0 && entityRelationships.length === 0}
				<p style="color: var(--color-muted)">No relationships found.</p>
			{:else}
				<!-- Entity relationships (within this model's canvas) -->
				{#if entityRelationships.length > 0}
					<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Entity Relationships ({entityRelationships.length})</h3>
					<table class="mb-6 w-full text-sm">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="py-2 text-left" style="color: var(--color-muted)">Source</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Target</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Type</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Label</th>
							</tr>
						</thead>
						<tbody>
							{#each entityRelationships as rel}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="py-2">
										<a href="/entities/{rel.source_entity_id}" style="color: var(--color-primary)">{rel.source_name || rel.source_entity_id}</a>
									</td>
									<td class="py-2">
										<a href="/entities/{rel.target_entity_id}" style="color: var(--color-primary)">{rel.target_name || rel.target_entity_id}</a>
									</td>
									<td class="py-2">
										<span class="inline-block rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg)">
											{rel.relationship_type}
										</span>
									</td>
									<td class="py-2" style="color: var(--color-fg)">{rel.label ?? '—'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}

				<!-- Model-to-model relationships -->
				{#if modelRelationships.length > 0}
					<h3 class="mb-2 text-sm font-semibold" style="color: var(--color-fg)">Model Relationships ({modelRelationships.length})</h3>
					<table class="w-full text-sm">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="py-2 text-left" style="color: var(--color-muted)">Direction</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Related Model</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Type</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Label</th>
								<th class="py-2 text-left" style="color: var(--color-muted)">Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each modelRelationships as rel}
								{@const isSource = rel.source_model_id === model.id}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="py-2" style="color: var(--color-fg)">{isSource ? 'Outgoing' : 'Incoming'}</td>
									<td class="py-2">
										<a
											href="/models/{isSource ? rel.target_model_id : rel.source_model_id}"
											style="color: var(--color-primary)"
										>
											{isSource ? rel.target_name : rel.source_name}
										</a>
									</td>
									<td class="py-2">
										<span class="inline-block rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg)">
											{rel.relationship_type}
										</span>
									</td>
									<td class="py-2" style="color: var(--color-fg)">{rel.label ?? '—'}</td>
									<td class="py-2">
										{#if editing}
											<button
												onclick={() => deleteModelRelationship(rel.id)}
												class="text-xs"
												style="color: var(--color-danger, #dc2626)"
											>
												Delete
											</button>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
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
	</div><!-- end main content flex-1 -->
	</div><!-- end sidebar + content flex wrapper -->

	<ModelDialog
		open={showCreateChildDialog}
		mode="create"
		initialName=""
		initialType={model.model_type}
		initialDescription=""
		onsave={handleCreateChild}
		oncancel={() => (showCreateChildDialog = false)}
	/>

	<ModelPicker
		open={showParentPicker}
		onselect={handleSetParent}
		oncancel={() => (showParentPicker = false)}
		excludeModelId={model?.id}
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

	<NodeDeleteDialog
		open={showNodeDeleteDialog}
		nodeName={deleteNodeName}
		isModelRef={deleteNodeIsModelRef}
		onremove={handleRemoveNodeFromCanvas}
		ondelete={handleCascadeDeleteEntity}
		oncancel={() => { showNodeDeleteDialog = false; deleteNodeId = null; }}
	/>

	<!-- Add entity relationship from tab: source picker -->
	<EntityPicker
		open={addEntityRelStep === 'source'}
		title="Select Source Entity"
		subtitle="Choose the source entity for the relationship."
		onselect={handleEntityRelSourceSelected}
		oncancel={() => (addEntityRelStep = null)}
	/>

	<!-- Add entity relationship from tab: target picker -->
	<EntityPicker
		open={addEntityRelStep === 'target'}
		title="Select Target Entity"
		subtitle="Choose the target entity for the relationship."
		onselect={handleEntityRelTargetSelected}
		oncancel={() => (addEntityRelStep = null)}
	/>

	<!-- Add entity relationship from tab: details dialog -->
	<RelationshipDialog
		open={addEntityRelStep === 'details'}
		sourceName={addEntityRelSource?.name ?? ''}
		targetName={addEntityRelTarget?.name ?? ''}
		onsave={handleEntityRelSave}
		oncancel={() => (addEntityRelStep = null)}
	/>

	<!-- Add model relationship from tab: model picker -->
	<ModelPicker
		open={showAddModelRelPicker}
		title="Select Target Model"
		onselect={handleModelRelTargetSelected}
		oncancel={() => (showAddModelRelPicker = false)}
		excludeModelId={model?.id}
	/>

	<!-- Add model relationship from tab: details dialog -->
	<RelationshipDialog
		open={showAddModelRelDialog}
		sourceName={model?.name ?? ''}
		targetName={addModelRelTarget?.name ?? ''}
		onsave={handleModelRelSave}
		oncancel={() => (showAddModelRelDialog = false)}
	/>

	<!-- "Add to canvas?" prompt -->
	{#if showAddToCanvasPrompt}
		<dialog
			open
			class="fixed inset-0 z-50 flex items-center justify-center rounded-lg p-6 shadow-lg backdrop:bg-black/50"
			style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 320px"
			aria-labelledby="add-to-canvas-title"
		>
			<h2 id="add-to-canvas-title" class="text-lg font-bold">Add to Canvas?</h2>
			<p class="mt-2 text-sm" style="color: var(--color-muted)">
				{#if addToCanvasRelType === 'entity'}
					Would you like to add the entities and relationship to the canvas?
				{:else}
					Would you like to add the target model as a reference on the canvas?
				{/if}
			</p>
			<div class="mt-4 flex justify-end gap-3">
				<button
					onclick={handleDismissAddToCanvas}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					No
				</button>
				<button
					onclick={handleAddToCanvas}
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					Yes
				</button>
			</div>
		</dialog>
	{/if}

{/if}
